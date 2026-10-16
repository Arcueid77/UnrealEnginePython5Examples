"""Real EnhancedInput ADS, original native camera/movement/mappings/UI source."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_hud.message_payload_validation_fields import ON, CONTROLLER
from . import ads_mixin as policy
from .ads_contract import PLAN, require, validate


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.scope, self.helper, self.sides, self.paused = False, None, None, [], False
        self.plan = PLAN
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(status="running", error=None, cases=[], original_player_restored=False,
            original_widget_grant_preserved=False, source_observer_closed=False, source_scopes_created=0, source_scopes_closed=0)
        for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
            "task_callbacks_replayed", "camera_or_speed_written_by_probe", "mapping_context_written_by_probe", "ui_messages_injected_by_probe"):
            self.report[field] = False

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))
    def tasks(self): return sum(valid(task) and task.is_a(ue.find_class("AbilityTask_WaitInputRelease")) for task in self.ability.get_property("ActiveTasks"))

    def mapping(self):
        value = self.input.call_function("HasMappingContext", self.context)
        require(isinstance(value, tuple) and len(value) == 2, "native HasMappingContext output shape differs")
        return dict(active=next(part for part in value if type(part) is bool), priority=next(part for part in value if type(part) is int))

    def widget_handles(self):
        return list(self.ability.WidgetExtensionHandles)

    def widgets_preserved(self):
        handles = self.widget_handles()
        native = ue.find_class("UIExtensionHandleFunctions").get_cdo()
        def is_valid(handle):
            value = native.call_function("IsValid", handle)
            return value if type(value) is bool else next(part for part in value if type(part) is bool)
        return len(handles) == len(self.original_handles) and all(is_valid(handle) for handle in handles)

    def inject(self, pressed):
        self.controller.inject_enhanced_input_for_action(self.action, pressed)
        if pressed: self.row["input_injections"] += 1

    def close_observer(self):
        if self.scope is not None:
            self.scope.close(); self.scope = None; self.report["source_scopes_closed"] += 1

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bHealthReady and not snap.bDamageImmune and snap.Health > 0): continue
            controller = self.statics.call_function("GetPlayerController", world, 0)
            model = capture(controller)
            if model is None or "ID_Pistol" not in model["definition"]: continue
            self.world, self.controller, self.pawn = world, controller, controller.get_controlled_pawn()
            self.asc, self.cls = ability_system(self.pawn), ue.load_class(policy.CLASS)
            values = [value for spec in self.asc.get_property("ActivatableAbilities").Items
                if valid(spec.Ability) and spec.Ability.get_class() == self.cls
                for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
            if len(values) != 1 or values[0].get_property("bIsActive"): continue
            self.ability, self.movement = values[0], self.pawn.CharacterMovement
            self.hero = self.pawn.get_component_by_type(ue.find_class("LyraHeroComponent"))
            self.input, self.context = policy.input_system(self.ability), ue.load_object(ue.find_class("InputMappingContext"), policy.MAPPING)
            self.original_model, self.original_speed, self.original_camera, self.original_mapping = model, float(self.movement.MaxWalkSpeed), self.hero.get_property("AbilityCameraMode"), self.mapping()
            require(not self.original_mapping["active"], "ADS mapping already exists; do not remove a foreign context")
            self.original_handles = self.widget_handles()
            require(bool(self.original_handles) and self.widgets_preserved(), "native inherited ADS UI grant handles missing")
            reticles = [value for value in world.all_objects() if valid(value) and "W_Reticle_Pistol_C" == value.get_class().get_name()
                and value.call_function("GetOwningPlayer") == self.controller]
            if len(reticles) != 1: continue
            self.reticle = reticles[0]
            self.action = ue.load_object(ue.find_class("InputAction"), "/ShooterCore/Input/Actions/IA_ADS.IA_ADS")
            self.helper = ue.new_object(ue.load_class("/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C")); self.helper.add_to_root()
            self.begin(); return

    def begin(self):
        self.name, self.profile = self.plan[self.index//2], ("ADSBlueprintFallback", "ADSPython")[self.index % 2]
        require(not self.ability.get_property("bIsActive"), "previous native ADS still active")
        ue.set_mixin_profile(self.ability, self.profile)
        require(str(ue.get_mixin_profile(self.ability)) == self.profile, "ADS parent-router profile not selected")
        self.before = policy.snapshot()
        self.row = dict(native_type_preserved=self.ability.get_class() == self.cls, input_injections=0,
            native_camera_while_held=False, native_speed_while_held=False, native_mapping_priority_11=False,
            actual_reticle_ads_on=False, actual_reticle_ads_off=False, native_pause_observed=False,
            profile_teardown_ended_ability=False, source_ui_events=[])
        self.scope = SubscriptionScope(); self.report["source_scopes_created"] += 1
        def read(proxy):
            payload, success = self.helper.call_function("ReadUI", proxy)
            require(success is True, "native typed ADS source extraction failed"); return payload
        def message(channel, payload):
            require(getattr(payload, CONTROLLER) == self.controller, "foreign ADS UI message owner")
            self.row["source_ui_events"].append(bool(getattr(payload, ON)))
        ui = ue.load_object(ue.find_class("UserDefinedStruct"), policy.UI)
        self.scope.listen_gameplay_message(self.world, "Gameplay.Message.ADS", ui, read, message)
        self.enter("hold")

    def hold(self):
        require(time.monotonic()-self.phase_started < 5., "real native input did not establish ADS")
        if not self.ability.get_property("bIsActive"):
            self.inject(True); return
        self.row["native_camera_while_held"] |= self.hero.get_property("AbilityCameraMode") == ue.load_class(policy.CAMERA)
        self.row["native_speed_while_held"] |= abs(float(self.movement.MaxWalkSpeed)-self.original_speed*float(self.ability.ADSMultiplier)) < .01
        self.row["native_mapping_priority_11"] |= self.mapping() == dict(active=True, priority=11)
        self.row["actual_reticle_ads_on"] |= bool(self.reticle._uep_reticle_ads)
        if self.row["input_injections"] < 4:
            self.inject(True); return
        if not self.may_finish_hold():
            self.inject(True); return
        if self.profile == "ADSPython":
            require(policy.snapshot()["activations"] == self.before["activations"]+1, "native input did not enter ADS Python activation gate")
        require(all(self.row[key] for key in ("native_camera_while_held", "native_speed_while_held", "native_mapping_priority_11", "actual_reticle_ads_on")),
            "native ADS camera/speed/mapping/reticle state missing")
        self.row["wait_tasks_while_held"] = self.tasks()
        if self.name == "paused-world-time":
            self.frozen_time = self.game_time()
            require(self.statics.call_function("SetGamePaused", self.world, True), "native ADS pause refused")
            self.paused = True; self.enter("paused"); return
        if self.name == "native-cancel": self.ability.call_function("K2_CancelAbility")
        elif self.name == "external-native-end": self.ability.call_function("K2_EndAbility")
        elif self.name == "active-profile-switch":
            ue.set_mixin_profile(self.ability, "ADSPython" if self.profile == "ADSBlueprintFallback" else "ADSBlueprintFallback")
            self.row["profile_teardown_ended_ability"] = not self.ability.get_property("bIsActive")
        self.inject(False); self.enter("ended")

    def may_finish_hold(self): return True

    def ended(self):
        self.inject(False)
        if self.ability.get_property("bIsActive"):
            require(time.monotonic()-self.phase_started < 5., "native ADS input release/end did not finish"); return
        if time.monotonic()-self.phase_started < .4: return
        self.row.update(tasks_after_end=self.tasks(), actual_reticle_ads_off=not bool(self.reticle._uep_reticle_ads),
            camera_speed_mapping_restored=(self.hero.get_property("AbilityCameraMode") == self.original_camera and
                float(self.movement.MaxWalkSpeed) == self.original_speed and self.mapping() == self.original_mapping),
            widget_grant_preserved=self.widgets_preserved())
        self.at_end = policy.snapshot(); self.enter("settled")

    def settled(self):
        if time.monotonic()-self.phase_started < .25: return
        after = policy.snapshot(); self.row["no_late_callbacks"] = after == self.at_end
        self.row["counters"] = {key: value-self.before[key] for key, value in after.items() if type(value) is int and key != "active_count"}
        self.close_observer(); self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_ADS_CASE_OBSERVED "+self.name)
        self.index += 1
        if self.index == len(self.plan)*2: self.finish()
        else: self.begin()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "native ADS total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "hold": self.hold()
            elif self.phase == "ended": self.ended()
            elif self.phase == "settled": self.settled()
            elif time.monotonic()-self.phase_started > .3:
                self.row["native_pause_observed"] = self.game_time() == self.frozen_time
                self.row["ability_active_during_pause"] = bool(self.ability.get_property("bIsActive"))
                require(self.statics.call_function("SetGamePaused", self.world, False), "native ADS unpause refused")
                self.paused = False; self.inject(False); self.enter("ended")
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            if hasattr(self, "ability"):
                if hasattr(self, "action"): self.inject(False)
                if self.ability.get_property("bIsActive"): self.ability.call_function("K2_EndAbility")
                self.report["original_player_restored"] = (capture(self.controller) == self.original_model and
                    self.hero.get_property("AbilityCameraMode") == self.original_camera and float(self.movement.MaxWalkSpeed) == self.original_speed and
                    self.mapping() == self.original_mapping)
                self.report["original_widget_grant_preserved"] = self.widgets_preserved()
                ue.set_mixin_profile(self.ability, "ADSPython")
            self.close_observer(); self.report["source_observer_closed"] = self.scope is None
            if valid(self.helper): self.helper.remove_from_root(); self.helper = None
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_ADS_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report, self.plan)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_ADS_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPADSResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPADSResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
