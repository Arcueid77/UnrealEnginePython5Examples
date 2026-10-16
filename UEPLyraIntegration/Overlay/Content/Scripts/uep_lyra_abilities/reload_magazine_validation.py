"""Real equipped ability/input, original animation notify and native ammo APIs."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture, services
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_hud.weapon_validation_helpers import set_stat
from . import reload_magazine_mixin as policy
from .reload_magazine_contract import PLAN, REFUSED, EARLY, require, validate
from . import reload_weapon_fixture as weapon_fixture

PISTOL = "/Game/Weapons/Pistol/GA_Weapon_Reload_Pistol.GA_Weapon_Reload_Pistol_C"
AUTO = "/Game/Weapons/GA_Weapon_AutoReload.GA_Weapon_AutoReload_C"
RESPAWN = "/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn_C"
QUICKSLOT = "/ShooterCore/Game/GA_QuickbarSlots.GA_QuickbarSlots_C"


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.sides, self.scope, self.source_task, self.paused = False, [], None, None, False
        self.plan = PLAN
        self.last_readiness = {}
        self.weapon = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPReloadWeapon=")), "pistol")
        require(self.weapon in weapon_fixture.WEAPONS, "unknown native reload weapon fixture")
        self.weapon_fixture = None
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(status="running", error=None, cases=[], original_player_restored=False,
            original_autoreload_active_restored=False, fixture_native_inventory_api_used=True,
            observer_scopes_created=0, observer_scopes_closed=0, weapon=self.weapon)
        for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
            "task_callbacks_replayed", "reload_done_event_injected", "ammo_properties_written", "ability_activation_called_by_probe"): self.report[field] = False

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))
    def ammo(self): return policy.ammo(self.item)
    def tasks(self): return sum(valid(task) for task in self.ability.get_property("ActiveTasks"))

    def no_firing(self):
        return bool(ue.find_class("BlueprintGameplayTagLibrary").get_cdo().call_function("DoesTagAssetInterfaceHaveTag",
            self.pawn, GameplayTag(TagName=policy.NO_FIRING)))

    def instances(self, cls):
        return [value for spec in self.asc.get_property("ActivatableAbilities").Items if valid(spec.Ability) and spec.Ability.get_class() == cls
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]

    def set_ammo(self, values):
        for tag, value in zip((policy.MAGAZINE, policy.SPARE), (values[0], values[2])): set_stat(self.item, tag, value)

    def initial_ammo(self):
        return (self.capacity, self.capacity, self.capacity*2) if self.name == "full-magazine-refused" else (
            (min(1, self.capacity-1), self.capacity, 0) if self.name == "no-spare-refused" else ((min(5, self.capacity-1), self.capacity, 3) if self.name == "partial-limited-spare" else (
                (self.capacity//2, self.capacity, self.capacity*2) if self.name == "repeat-partial" else (0, self.capacity, self.capacity*2))))

    def prepare_weapon(self, controller, model):
        if self.weapon == "pistol": return True
        if self.weapon_fixture is None:
            self.weapon_fixture = weapon_fixture.install(controller, self.weapon)
            self.report["native_weapon_fixture"] = copy.deepcopy(self.weapon_fixture)
            return False
        return True

    def readiness(self, **values):
        stage = values["stage"]
        if values == self.last_readiness.get(stage): return
        self.last_readiness[stage] = values
        self.report["readiness"] = values
        atomic_write(self.path, self.report)
        ue.log("UEP_RELOAD_MAGAZINE_WAIT "+json.dumps(values))

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            self.readiness(stage="native Hero input/health", input_ready=bool(snap.bHeroInputReady), health_ready=bool(snap.bHealthReady), immune=bool(snap.bDamageImmune))
            if not (snap.bHeroInputReady and snap.bHealthReady and not snap.bDamageImmune and snap.Health > 0): continue
            controller = self.statics.call_function("GetPlayerController", world, 0); model = capture(controller)
            if model is None or not self.prepare_weapon(controller, model): continue
            if weapon_fixture.WEAPONS[self.weapon][2] not in model["definition"]: continue
            self.world, self.bridge, self.controller, self.pawn = world, bridge, controller, controller.get_controlled_pawn()
            self.asc, self.cls = ability_system(self.pawn), ue.load_class(weapon_fixture.WEAPONS[self.weapon][0])
            reloads, autos, respawns, quickslots = (self.instances(ue.load_class(cls)) for cls in (weapon_fixture.WEAPONS[self.weapon][0], AUTO, RESPAWN, QUICKSLOT))
            _, quickbar = services(controller); active_item = quickbar.call_function("GetActiveSlotItem")
            autos = [value for value in autos if value.call_function("GetAssociatedItem") == active_item]
            candidates = [value for value in respawns+quickslots if value.get_property("bIsActive")]
            owners = candidates[:1]
            self.readiness(stage="native equipped ability/source observer", reloads=len(reloads), autos=len(autos),
                respawns=[bool(value.get_property("bIsActive")) for value in respawns],
                quickslots=[bool(value.get_property("bIsActive")) for value in quickslots])
            expected_autos = int(self.weapon != "netshooter")
            if len(reloads) != 1 or len(owners) != 1 or len(autos) != expected_autos: continue
            self.ability, self.auto, self.source_owner = reloads[0], autos[0] if autos else None, owners[0]
            if self.ability.get_property("bIsActive") or not self.source_owner.get_property("bIsActive"): continue
            self.item = self.ability.call_function("GetAssociatedItem")
            if not valid(self.item): continue
            _, self.quickbar = services(controller)
            equipment = self.ability.call_function("GetAssociatedEquipment")
            require(valid(equipment) and equipment.call_function("GetInstigator") == self.item == self.quickbar.call_function("GetActiveSlotItem"),
                "native reload equipment SourceObject differs")
            widgets = [value for value in world.all_objects() if valid(value) and value.get_class().get_name() == "W_AbilityFailureFeedback_C" and
                value.call_function("GetOwningPlayer") == controller]
            self.readiness(stage="native source/UI ready", source_owner=self.source_owner.get_class().get_path_name(), failure_widgets=len(widgets))
            if len(widgets) != 1: continue
            self.failure_widget, self.anim = widgets[0], self.pawn.Mesh.call_function("GetAnimInstance")
            require(not self.no_firing(), "do not clear a foreign NoFiring tag")
            self.original_ammo, self.original_model = self.ammo(), model
            self.report["native_source_observer_owner"] = self.source_owner.get_class().get_path_name()
            self.report["native_reload_class"] = self.cls.get_path_name()
            self.report["native_equipped_autoreload_grant_count"] = len(autos)
            self.report["native_inherited_signatures"] = {name: ue.describe_function(self.cls, name) for name in
                ("K2_ActivateAbility", "K2_CanActivateAbility", "ReloadAmmoIntoMagazine", "K2_OnEndAbility")}
            self.capacity, self.original_auto_active = self.original_ammo[1], bool(self.auto.get_property("bIsActive")) if self.auto is not None else False
            if self.original_auto_active: self.auto.call_function("K2_EndAbility")
            self.action = ue.load_object(ue.find_class("InputAction"), "/Game/Input/Actions/IA_Weapon_Reload.IA_Weapon_Reload")
            self.begin(); return

    def close_observer(self):
        if self.scope is not None:
            self.scope.close(); self.scope = None; self.report["observer_scopes_closed"] += 1
        if valid(self.source_task): self.source_task.call_function("EndTask")
        self.source_task = None

    def begin(self):
        self.name, self.profile = self.plan[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        require(not self.ability.get_property("bIsActive") and not self.no_firing(), "previous native reload/tag still active")
        ue.set_mixin_profile(self.ability, self.profile); self.set_ammo(self.initial_ammo())
        initial = self.ammo(); moved = min(initial[1], initial[0]+initial[2])-initial[0]
        self.before, self.trial_started, self.intervened = policy.snapshot(), self.game_time(), False
        self.row = dict(native_type_preserved=self.ability.get_class() == self.cls, native_class=self.cls.get_path_name(),
            native_equipment_item_source_matches=self.ability.call_function("GetAssociatedEquipment").call_function("GetInstigator") == self.item,
            initial_ammo=initial, expected_ammo=(initial[0]+moved, initial[1], initial[2]-moved), input_injections=1,
            native_active_observed=False, native_tasks_observed=0, original_montage_playing_observed=False,
            expected_no_firing_observed=False, native_reload_done_events=0, native_failure_tags=[], failure_messages=0,
            profile_teardown_ended_native_ability=False, native_pause_observed=False)
        self.failure_before = self.failure_widget._uep_failure_messages
        self.scope = SubscriptionScope(); self.report["observer_scopes_created"] += 1
        self.source_task = ue.find_class("AbilityTask_WaitGameplayEvent").get_cdo().call_function("WaitGameplayEvent", self.source_owner,
            GameplayTag(TagName=policy.RELOAD_DONE), None, False, True)
        self.source_events = 0
        def received(payload): self.source_events += 1
        self.scope.bind_event(self.source_task, "EventReceived", received); self.source_task.call_function("ReadyForActivation")
        self.controller.inject_enhanced_input_for_action(self.action, True)
        self.enter("running")

    def may_perform_action(self): return True

    def may_capture_end(self): return True

    def running(self):
        self.controller.inject_enhanced_input_for_action(self.action, False)
        elapsed = self.game_time()-self.trial_started
        require(elapsed < 10., "native reload did not finish/refuse: "+self.name)
        active = bool(self.ability.get_property("bIsActive"))
        self.row["native_active_observed"] |= active
        self.row["native_tasks_observed"] = max(self.row["native_tasks_observed"], self.tasks())
        self.row["original_montage_playing_observed"] |= bool(self.anim.call_function("Montage_IsPlaying", self.ability.ReloadMontage))
        if active: self.row["expected_no_firing_observed"] |= self.no_firing() == (self.row["initial_ammo"][0] == 0)
        if self.name in REFUSED:
            self.row["failure_messages"] = self.failure_widget._uep_failure_messages-self.failure_before
            if self.row["failure_messages"] == 0: return
            payload = self.failure_widget._uep_failure_payload
            self.row["native_failure_tags"] = sorted(str(tag.TagName) for tag in payload.FailureTags.GameplayTags)
        elif active:
            if elapsed > .06 and not self.intervened and self.may_perform_action():
                if self.name in EARLY or self.name == "paused-world-time":
                    self.intervened = True
                    if self.name == "native-cancel": self.ability.call_function("K2_CancelAbility")
                    elif self.name == "montage-interrupt": self.pawn.call_function("StopAnimMontage", self.ability.ReloadMontage)
                    elif self.name == "external-native-end": self.ability.call_function("K2_EndAbility")
                    elif self.name == "active-profile-switch":
                        ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
                        self.row["profile_teardown_ended_native_ability"] = not self.ability.get_property("bIsActive")
                    else:
                        self.frozen_time = self.game_time()
                        require(self.statics.call_function("SetGamePaused", self.world, True), "native reload pause refused")
                        self.paused = True; self.enter("paused")
            return
        elif not self.row["native_active_observed"]: return
        if not self.may_capture_end(): return
        self.row.update(final_ammo=self.ammo(), tasks_after_end=self.tasks(), native_ability_inactive=not self.ability.get_property("bIsActive"),
            no_firing_after_end=self.no_firing(), native_reload_done_events=self.source_events, native_inventory_model=capture(self.controller))
        self.at_end = policy.snapshot(); self.enter("ended")

    def ended(self):
        # Original bStopWhenAbilityEnds=False permits a remaining montage and
        # its native notify after early End. Observe it; never start another
        # reload while that old notify could be mistaken for the next trial.
        require(time.monotonic()-self.phase_started < 10., "native reload remaining montage did not settle")
        if self.anim.call_function("Montage_IsPlaying", self.ability.ReloadMontage) or time.monotonic()-self.phase_started < .35: return
        after = policy.snapshot()
        self.row["no_late_callback"] = all(after[key] == self.at_end[key] for key in
            ("activations", "reload_events", "authority_reloads", "transferred_rounds", "tasks_created", "fallback_activations", "fallback_reloads")) and self.ammo() == self.row["final_ammo"]
        self.row["late_native_source_events"] = self.source_events-self.row["native_reload_done_events"]
        self.row["counters"] = {key: value-self.before[key] for key, value in after.items() if type(value) is int and key != "active_count"}
        self.close_observer(); self.complete_trial()

    def complete_trial(self):
        self.set_ammo(self.original_ammo)
        self.row["fixture_ammo_restored"] = self.ammo() == self.original_ammo
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_RELOAD_MAGAZINE_CASE_OBSERVED "+self.name)
        self.index += 1
        if self.index == len(self.plan)*2: self.finish()
        else: self.begin()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300., "native reload total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "running": self.running()
            elif self.phase == "ended": self.ended()
            elif self.phase == "paused" and time.monotonic()-self.phase_started > .35:
                self.row["native_pause_observed"] = (abs(self.game_time()-self.frozen_time) < .01 and
                    bool(self.ability.get_property("bIsActive")) and self.ammo() == self.row["initial_ammo"] and self.tasks() == 2)
                require(self.statics.call_function("SetGamePaused", self.world, False), "native reload unpause refused")
                self.paused = False; self.enter("running")
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            if hasattr(self, "action"): self.controller.inject_enhanced_input_for_action(self.action, False)
            self.close_observer()
            if hasattr(self, "ability"):
                if self.ability.get_property("bIsActive"): self.ability.call_function("K2_EndAbility")
                self.set_ammo(self.original_ammo); ue.set_mixin_profile(self.ability, "Python")
                if self.original_auto_active and not self.auto.get_property("bIsActive"):
                    require(self.asc.call_function("TryActivateAbilityByClass", ue.load_class(AUTO), False), "native AutoReload restore refused")
                self.report["original_autoreload_active_restored"] = (bool(self.auto.get_property("bIsActive")) == self.original_auto_active if self.auto is not None
                    else len(weapon_fixture.auto_instances(self.controller)) == 0)
                self.report["original_player_restored"] = self.ammo() == self.original_ammo and capture(self.controller) == self.original_model and not self.no_firing()
            if self.weapon_fixture is not None:
                self.report["equipped_fixture_state_restored"] = self.report["original_player_restored"]
                weapon_fixture.restore(self.controller, self.weapon_fixture)
                self.report["temporary_weapon_removed"] = weapon_fixture.restored(self.controller, self.weapon_fixture)
                self.report["original_player_restored"] = self.report["temporary_weapon_removed"] and not self.no_firing()
                self.report["original_autoreload_active_restored"] = weapon_fixture.auto_active(self.controller) == self.weapon_fixture["original_auto_active"]
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_RELOAD_MAGAZINE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"
                validate(self.report, authority=not getattr(self, "network_fixture", False), plan=self.plan)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_RELOAD_MAGAZINE_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPReloadMagazineResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPReloadMagazineResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
