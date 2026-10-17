"""Typed second-BP calls and native lethal GAS on independently owned bots."""
import copy
import time
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from uep_lyra_abilities import death_damage
from .inventory_wait_transitions import Transition as OwnedTransition, end_owned_respawn, CUE
from .inventory_clear_mixin import CLASS, inventory_state
from .health_changed_observation import health
from .outline_validation import path, gc
from .initial_inventory_contract import require
from .team_observer_observation import proxies
from . import equipment_hide_mixin as policy, inventory_wait_mixin as wait, initial_inventory_mixin as loadout

PROBE = "/Game/UEPValidation/BP_CharacterEquipmentHideProbe.BP_CharacterEquipmentHideProbe_C"
SCENARIOS = [(name, 0, calls, profile) for name, calls in (("equipped", 1), ("already-hidden", 1), ("repeat", 2), ("empty", 1), ("missing-manager", 1), ("native-death", 1)) for profile in ("BlueprintFallback", "Python")]


def equipment(actor):
    manager = actor.get_component_by_type(ue.find_class("LyraEquipmentManagerComponent"))
    instances = list(manager.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance"))) if valid(manager) else []
    actors = [value for instance in instances for value in instance.call_function("GetSpawnedActors") if valid(value)]
    return manager, instances, actors


class Caller:
    def __init__(self):
        self.cls = ue.load_class(PROBE); self.object = self.cls.get_cdo(); self.added = not self.cls.is_rooted(); self.released = False
        if self.added: self.cls.add_to_root()
    def call(self, actor): self.object.call_function("Hide", actor)
    def close(self):
        if self.added and not self.released: self.cls.remove_from_root(); self.released = True
        return dict(created=int(self.added), released=int(self.released))


def delta(after, before): return {key: after[key]-before[key] for key in after}


def network_trial(actor, controller, caller, profile, target):
    _, instances, actors = equipment(actor); require(instances and actors, "network equipment-hide has no actual native spawned weapon Actor")
    original = [(value, bool(value.get_property("bHidden"))) for value in actors]
    before_inventory, before_profile, pawn_hidden = inventory_state(controller), str(ue.get_mixin_profile(actor)), bool(actor.get_property("bHidden"))
    before = copy.deepcopy(policy.evidence(actor))
    try:
        ue.set_mixin_profile(actor, profile); caller.call(actor)
        row = dict(target=target, profile=profile, bp_reference_call=True, actual_character_class=path(actor.get_class()),
            instances=len(instances), spawned_actor_paths=[path(value) for value in actors], native_all_hidden=all(value.get_property("bHidden") for value in actors),
            native_pawn_hidden_unchanged=bool(actor.get_property("bHidden")) == pawn_hidden, counters=delta(policy.evidence(actor), before),
            native_role=int(actor.call_function("GetLocalRole")))
    finally:
        for value, hidden in original:
            if valid(value): value.call_function("SetActorHiddenInGame", hidden)
        ue.set_mixin_profile(actor, before_profile)
    row.update(original_visibility_restored=all(valid(value) and bool(value.get_property("bHidden")) == hidden for value, hidden in original),
        inventory_identity_restored=inventory_state(controller) == before_inventory, profile_restored=str(ue.get_mixin_profile(actor)) == before_profile)
    return row


class Trial(OwnedTransition):
    def __init__(self, world, caller, scenario):
        # Snapshot pre-existing exact native Cue handles BEFORE producing a bot.
        # Those native timeline observers may retire or be replaced on recycle;
        # persistent Character observers may not. Never cancel either baseline.
        self.preexisting_cue_handles = [(cue, value, path(cue), path(value))
            for cue in ue.tobject_iterator(ue.load_class(CUE)) if valid(cue) and cue.get_world() == world
            for value in [cue.get_property("TeamColorWatcherHandle")] if valid(value) and value.call_function("IsActive")]
        super().__init__(world, None, scenario); self.caller = caller; self.observe_owned_cue_handles()

    def start(self):
        name, _, calls, profile = self.scenario
        self.actor = self.world.actor_spawn(ue.load_class(CLASS), ue.FVector(200000., 200000., 2000.)) if name in ("empty", "missing-manager") else self.owner.pawn
        end_owned_respawn(self.actor)
        manager, instances, actors = equipment(self.actor)
        if name == "empty": require(valid(manager) and not instances and not actors, "empty native equipment control is not a valid empty manager")
        if name == "missing-manager":
            require(valid(manager), "owned missing-manager fixture has no original component"); manager.destroy_component()
            require(not valid(equipment(self.actor)[0]), "owned equipment component removal did not actually occur")
        if name not in ("empty", "missing-manager"): require(instances and actors, "owned equipment-hide has no native spawned weapon Actor")
        for value in actors: value.call_function("SetActorHiddenInGame", name == "already-hidden")
        self.actors = actors; self.before_inventory = inventory_state(self.owner.controller); self.pawn_hidden = bool(self.actor.get_property("bHidden"))
        ue.set_mixin_profile(self.actor, profile); self.before = copy.deepcopy(policy.evidence(self.actor)); self.actor_path = path(self.actor)
        self.death_started = float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", self.world))
        if name == "native-death": death_damage.apply(ability_system(self.actor), health(self.actor))
        else:
            for _ in range(calls): self.caller.call(self.actor)
        self.row = dict(name=name, profile=profile, calls=calls, actual_character_class=path(self.actor.get_class()),
            bp_reference_call=name != "native-death", native_lethal_gas_death=name == "native-death", callback_manually_replayed=False,
            manager_present_before=name != "missing-manager", instances_before=len(instances), spawned_actor_paths=[path(value) for value in actors],
            counters={}, native_all_spawned_actors_hidden=False,
            native_pawn_hidden_unchanged=bool(self.actor.get_property("bHidden")) == self.pawn_hidden,
            native_health_after=health(self.actor) if name == "native-death" else None, actor_was_not_rooted=not self.actor.is_rooted())
        if name == "native-death": self.enter("await-native-death-hide")
        else: self.capture_hide()

    def capture_hide(self):
        self.row.update(counters=delta(policy.evidence(self.actor), self.before),
            native_all_spawned_actors_hidden=all(valid(value) and value.get_property("bHidden") for value in self.actors),
            native_death_delay_observed=self.scenario[0] == "native-death",
            native_death_elapsed_game_seconds=float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", self.world))-self.death_started if self.scenario[0] == "native-death" else None)
        self.hide_ref = policy.evidence(self.actor); self.hide_snapshot = copy.deepcopy(self.hide_ref); self.enter("observe-hide")

    def step(self):
        if not self.closed: self.observe_owned_cue_handles()
        if self.phase == "owner-ready":
            require(time.monotonic()-self.started < 20, "equipment-hide owned bot readiness timeout")
            if self.owner.ready(): self.start()
            return False
        if self.phase == "await-native-death-hide":
            require(time.monotonic()-self.phase_started < 2., "real native death did not reach delayed weapon hiding")
            if self.actors and all(valid(value) and value.get_property("bHidden") for value in self.actors): self.capture_hide()
            return False
        if self.phase == "observe-hide":
            if time.monotonic()-self.phase_started >= .1:
                self.row["inventory_unchanged_by_hide"] = inventory_state(self.owner.controller) == self.before_inventory
                self.wait_ref, self.loadout_ref = wait.evidence(self.actor), loadout.evidence(self.actor)
                self.quiet_snapshot = (copy.deepcopy(self.wait_ref), copy.deepcopy(self.loadout_ref))
                self.close(); gc(); self.enter("cleanup-gc")
            return False
        done = super().step()
        if done:
            current = set(proxies()); exempt = {value[3] for value in self.preexisting_cue_handles}
            self.row.update(hide_quiet_after_destroy=self.hide_ref == self.hide_snapshot,
                original_active_observer_paths=sorted(self.original_proxies), final_active_observer_paths=sorted(current),
                original_character_observers_preserved=current-exempt == self.original_proxies-exempt,
                preexisting_observers_explicitly_cancelled=False,
                preexisting_native_cue_observers=[dict(cue=cue_path, cue_class=CUE, observer=observer_path,
                    original_was_active=True, fixture_never_cancels_or_writes=True,
                    final_active=valid(value) and bool(value.call_function("IsActive")), collected=not valid(value),
                    native_cue_handle_still_matches=valid(cue) and cue.get_property("TeamColorWatcherHandle") == value)
                    for cue, value, cue_path, observer_path in self.preexisting_cue_handles])
        return done
