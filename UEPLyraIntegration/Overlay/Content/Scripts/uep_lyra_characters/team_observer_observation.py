"""Read-only native proxy discovery; cancel only proxies created by this fixture."""
import copy
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .team_cosmetics_validation import DeviceObserver, ActorState, visual
from .inventory_clear_mixin import inventory_state
from .outline_validation import path, gc
from . import team_observer_mixin as policy, team_cosmetics_mixin as team_policy
from .team_observer_contract import require

PROBE = "/Game/UEPValidation/BP_CharacterTeamListenProbe.BP_CharacterTeamListenProbe_C"


def proxies(): return {path(value): value for value in ue.tobject_iterator(ue.find_class("AsyncAction_ObserveTeamColors")) if valid(value) and value.call_function("IsActive")}


def query(actor):
    found, number, _ = ue.find_class("LyraTeamStatics").get_cdo().call_function("FindTeamFromObject", actor, False)
    display = ue.find_class("LyraTeamStatics").get_cdo().call_function("GetTeamDisplayAsset", actor, number)
    return dict(team_set=bool(found), team_id=int(number), display_asset=path(display))


def delta(after, before, skip): return {key: value-before[key] for key, value in after.items() if key != skip}


class Context:
    probe_path = PROBE
    def __init__(self, actors, controllers, original_proxy_paths=None, startup_owned=()):
        self.actors, self.controllers, self.closed = actors, controllers, False
        self.states = {key: ActorState(actor) for key, actor in actors.items()}
        self.inventory = {key: inventory_state(controller) for key, controller in controllers.items()}
        self.original_proxies = set(proxies()) if original_proxy_paths is None else set(original_proxy_paths)
        self.startup_owned, self.owned, self.cancelled, self.latest = list(startup_owned), [], [], {}
        self.cdo = next(iter(actors.values())).get_class().get_cdo(); self.cdo_profile = str(ue.get_mixin_profile(self.cdo))
        self.devices = DeviceObserver(); self.caller_class = ue.load_class(self.probe_path); self.caller = self.caller_class.get_cdo()
        self.caller_root = not self.caller_class.is_rooted(); self.caller_released = False
        if self.caller_root: self.caller_class.add_to_root()
        self.startup = {key: copy.deepcopy(policy.evidence(actor)) for key, actor in actors.items()}
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", next(iter(actors.values())).get_world())
        self.net_mode = str(bridge.call_function("CaptureSnapshot").NetMode)

    def produce(self, key, profile, calls):
        actor = self.actors[key]; ue.set_mixin_profile(actor, profile)
        self.key, self.profile, self.calls, self.properties, self.current = key, profile, calls, [], []
        self.previous_latest = self.latest.get(key)
        self.before, self.team_before = copy.deepcopy(policy.evidence(actor)), copy.deepcopy(team_policy.evidence(actor))
        self.native_query = query(actor)
        for _ in range(calls):
            before = set(proxies()); marker = self.devices.marker()
            self.caller.call_function("Listen", actor)
            added = [value for name, value in proxies().items() if name not in before]
            require(len(added) == 1, "original BP ListenForTeam did not create exactly one real active native observer")
            self.current.extend(added); self.owned.extend(added); self.properties.extend(self.devices.collect(marker))
        self.active_before_cancel = all(value.call_function("IsActive") for value in self.current)

    def devices_done(self): return self.devices.observed(self.properties) and self.devices.markers_removed()

    def complete(self):
        actor = self.actors[self.key]
        row = dict(profile=str(ue.get_mixin_profile(actor)), typed_bp_listen_calls=self.calls, native_proxies_created=len(self.current),
            native_proxies_active_before_cancel=self.active_before_cancel, counters=delta(policy.evidence(actor), self.before, "last_payload"),
            team_counters=delta(team_policy.evidence(actor), self.team_before, "last_call"), payload=copy.deepcopy(policy.evidence(actor)["last_payload"]),
            native_team_query=self.native_query, visual=visual(actor), native_role=int(actor.call_function("GetLocalRole")),
            native_device_properties_created=len(self.properties), native_device_properties=self.devices.rows(self.properties), native_scheduler_removed_owned_properties=True)
        for value in self.current: value.call_function("Cancel")
        row["native_proxies_inactive_after_cancel"] = all(not value.call_function("IsActive") for value in self.current)
        self.cancelled.extend(self.current); self.latest[self.key] = self.current[-1]; gc()
        require(query(actor) == self.native_query, "observer fixture changed actual team state")
        return row

    def settle_collection(self, row):
        # Kismet CollectGarbage requests end-of-frame GC, not same-call GC.
        # Observe after engine ticks, without clearing any native BP frame.
        row.update(native_collection_checked_after_engine_ticks=True,
            native_older_current_proxies_collected=all(not valid(value) for value in self.current[:-1]),
            native_previous_proxy_released_after_next_factory=self.previous_latest is None or not valid(self.previous_latest),
            native_latest_cancelled_proxy_retained=int(valid(self.current[-1])),
            native_retained_proxy_inactive=not valid(self.current[-1]) or not self.current[-1].call_function("IsActive"))
        return row

    def cleanup(self, bare=None):
        if self.closed: return self.cleanup_report
        errors = []
        for value in self.owned+self.startup_owned:
            try:
                if valid(value) and value.call_function("IsActive"): value.call_function("Cancel")
            except Exception: errors.append(traceback.format_exc())
        restored = []
        for state in self.states.values():
            try: restored.append(state.restore())
            except Exception: errors.append(traceback.format_exc())
        markers_removed = self.devices.markers_removed()
        try: self.devices.close()
        except Exception: errors.append(traceback.format_exc())
        try:
            if self.caller_root and self.caller_class.is_rooted(): self.caller_class.remove_from_root(); self.caller_released = True
        except Exception: errors.append(traceback.format_exc())
        try:
            if valid(bare): bare.call_function("K2_DestroyActor")
        except Exception: errors.append(traceback.format_exc())
        gc()
        self.cleanup_report = dict(original_actor_visual_camera_profiles_restored=len(restored) == len(self.states) and all(restored),
            original_inventory_restored=all(inventory_state(controller) == self.inventory[key] for key, controller in self.controllers.items()),
            cdo_profile_restored=str(ue.get_mixin_profile(self.cdo)) == self.cdo_profile,
            original_active_proxies_preserved=set(proxies()) == self.original_proxies,
            owned_observers_cancelled_and_deregistered=all(not valid(value) or not value.call_function("IsActive") for value in self.owned+self.startup_owned),
            native_observation_markers_removed=markers_removed, native_observation_markers=len(self.devices.markers),
            device_roots_created=self.devices.roots_created, device_roots_released=self.devices.roots_released,
            caller_roots_created=int(self.caller_root), caller_roots_released=int(self.caller_released),
            owned_bare_actor_and_startup_proxy_destroyed=bare is None or not valid(bare))
        self.closed = True
        if errors: raise RuntimeError("native team observer cleanup failed: "+"\n".join(errors))
        return self.cleanup_report

    def finalize_collection(self):
        # Cleanup is already cached; no reads of destroyed Actors/controllers.
        retained = [value for value in self.owned+self.startup_owned if valid(value)]
        self.cleanup_report.update(native_collection_checked_after_engine_ticks=True,
            older_owned_proxies_collected=not retained,
            native_latest_cancelled_proxies_retained=len(retained),
            owned_bare_actor_startup_proxy_collected=all(not valid(value) for value in self.startup_owned),
            original_active_proxies_preserved=set(proxies()) == self.original_proxies)
        return self.cleanup_report
