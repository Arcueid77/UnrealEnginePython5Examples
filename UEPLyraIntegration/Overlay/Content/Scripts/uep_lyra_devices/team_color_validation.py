"""Real engine device scheduler and separate invalid-user public BP entry."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import ActivateDevicePropertyParams
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_world.effect_pad_mixin import valid
from . import team_color_mixin as policy
from .team_color_contract import PLAN, require, validate


def state(instance):
    data = instance.ColorData; color = data.LightColor
    return dict(enabled=bool(data.bEnable), reset=bool(data.bResetAfterCompletion),
        rgba=[int(getattr(color, key if hasattr(color, key) else key.upper())) for key in ("r", "g", "b", "a")])


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.paused, self.instance, self.handles, self.sides = False, False, None, [], []
        self.report = dict(status="running", error=None, cases=[], native_default_profile_observed=False,
            original_player_restored=False, owned_handles_removed=False, roots_created=0, roots_removed=0,
            invalid_user_public_bp_entry_used=True, invalid_user_submitted_to_scheduler=False,
            same_instance_native_reactivation_tested=False,
            direct_python_handler_replayed=False, native_apply_called_by_probe=False,
            hardware_output_tested=False, full_acceptance=False, network_acceptance=False, packaged_runtime=False,
            animation_assets_modified=False, device_mapping_written=False, cdo_profile_written=False)
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.library = ue.find_class("InputDeviceLibrary").get_cdo()

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def counts(self): return policy.instance_snapshot(self.instance)
    def evaluated(self):
        counts = self.counts(); return counts["evaluations"]+counts["fallback_evaluations"]

    def root(self, instance):
        self.instance = instance; instance.add_to_root(); self.report["roots_created"] += 1

    def unroot(self):
        if self.instance is not None:
            self.instance.remove_from_root(); self.instance = None; self.report["roots_removed"] += 1

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bHealthReady and snap.Health > 0 and not snap.bDamageImmune): continue
            controller = self.statics.call_function("GetPlayerController", world, 0); model = capture(controller)
            if model is None or "ID_Pistol" not in model["definition"]: continue
            self.world, self.controller, self.original_model, self.original_health = controller.get_controlled_pawn().get_world(), controller, model, float(snap.Health)
            self.bridge, self.cls = bridge, ue.load_class(policy.CLASS)
            self.devices = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetEngineSubsystem", ue.find_class("InputDeviceSubsystem"))
            require(valid(self.devices), "native input device subsystem unavailable")
            self.user = self.library.call_function("GetPrimaryPlatformUser")
            require(self.library.call_function("GetPlayerControllerFromPlatformUser", self.user) == controller, "primary platform user does not map to actual Lyra controller")
            self.device = self.library.call_function("GetPrimaryInputDeviceForUser", self.user)
            self.params = ActivateDevicePropertyParams(UserId=self.user, DeviceId=self.device, bLooping=False, bIgnoreTimeDilation=False, bPlayWhilePaused=False)
            handle = self.devices.call_function("ActivateDevicePropertyOfClass", self.cls, self.params)
            self.handles.append(handle); self.handle = handle
            instance = self.devices.call_function("GetActiveDeviceProperty", handle)
            require(valid(instance), "native class activation did not create its actual device property")
            self.root(instance); self.enter("default"); return

    def default(self):
        if self.evaluated() < 1 or self.devices.call_function("IsPropertyActive", self.handle): return
        require(not valid(self.devices.call_function("GetActiveDeviceProperty", self.handle)), "native one-shot handle still retains property")
        counts = self.counts()
        self.report["native_default_profile_observed"] = (self.instance.get_class() == self.cls and str(ue.get_mixin_profile(self.instance)) == "Python" and
            counts["evaluations"] == counts["valid_controllers"] == counts["colors_written"] == 1)
        require(self.report["native_default_profile_observed"], "native default class scheduler did not execute Python")
        self.report["native_default_color"] = state(self.instance)
        self.unroot(); self.prepare()

    def prepare(self):
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        self.cycle, self.accumulated = 0, {}
        self.row = dict(native_class=self.cls.get_path_name(), native_type_preserved=True, native_profile_selected=True,
            native_scheduler_used=self.name != "public-invalid-user", native_activation_count=0,
            same_instance_profile_switch_preserved=False, native_pause_observed=False, native_instance_paths=[])
        if self.name == "public-invalid-user":
            self.root(ue.new_object(self.cls)); ue.set_mixin_profile(self.instance, self.profile)
            self.before = self.counts(); self.row["before"] = state(self.instance)
            invalid = self.library.call_function("PlatformUserId_None")
            require(not self.library.call_function("IsValidPlatformId", invalid), "native invalid-user fixture is not invalid")
            self.instance.call_function("EvaluateDeviceProperty", invalid, self.device, .125, .75)
            self.complete(); return
        self.looping = self.name in ("native-looping", "same-instance-profile-switch", "native-paused-loop")
        self.activate()

    def activate(self):
        params = ActivateDevicePropertyParams(UserId=self.user, DeviceId=self.device, bLooping=self.looping, bIgnoreTimeDilation=False, bPlayWhilePaused=False)
        # Only the class factory is reflected by the Engine. Do not invent a
        # callable instance-activation API or add a C++ bridge just for a probe.
        self.handle = self.devices.call_function("ActivateDevicePropertyOfClass", self.cls, params); self.handles.append(self.handle)
        self.root(self.devices.call_function("GetActiveDeviceProperty", self.handle))
        require(valid(self.instance), "native class factory returned no active property")
        ue.set_mixin_profile(self.instance, self.profile)
        self.before = self.counts()
        self.row.setdefault("before", state(self.instance))
        self.row["native_type_preserved"] &= self.instance.get_class() == self.cls
        self.row["native_profile_selected"] &= str(ue.get_mixin_profile(self.instance)) == self.profile
        self.row["native_instance_paths"].append(self.instance.get_path_name())
        self.row["native_activation_count"] += 1; self.enter("evaluate")

    def evaluate(self):
        minimum = 3 if self.looping else 1
        if self.evaluated() < minimum: return
        if self.name == "same-instance-profile-switch":
            before = state(self.instance)
            ue.set_mixin_profile(self.instance, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
            self.row["same_instance_profile_switch_preserved"] = state(self.instance) == before and self.devices.call_function("GetActiveDeviceProperty", self.handle) == self.instance
            self.switch_count = self.evaluated(); self.enter("switched"); return
        if self.name == "native-paused-loop":
            require(self.statics.call_function("SetGamePaused", self.world, True), "native device pause refused")
            self.paused = True; self.frozen_counts = self.counts(); self.enter("paused"); return
        self.remove()

    def switched(self):
        if self.evaluated()-self.switch_count < 3: return
        ue.set_mixin_profile(self.instance, self.profile); self.remove()

    def paused_tick(self):
        require(self.counts() == self.frozen_counts, "native device scheduler evaluated a paused property")
        if time.monotonic()-self.phase_started < .25: return
        require(self.statics.call_function("SetGamePaused", self.world, False), "native device unpause refused")
        self.paused = False; self.row["native_pause_observed"] = True
        self.switch_count = self.evaluated(); self.enter("resumed")

    def resumed(self):
        if self.evaluated()-self.switch_count < 3: return
        self.remove()

    def remove(self):
        if self.looping: self.devices.call_function("RemoveDevicePropertyByHandle", self.handle)
        self.enter("removed")

    def removed(self):
        if self.devices.call_function("IsPropertyActive", self.handle) or valid(self.devices.call_function("GetActiveDeviceProperty", self.handle)): return
        if self.name == "native-repeat" and self.cycle == 0:
            self.accumulate(); self.unroot(); self.cycle = 1; self.activate(); return
        self.complete()

    def accumulate(self):
        for key, value in self.counts().items(): self.accumulated[key] = self.accumulated.get(key, 0)+value-self.before[key]

    def complete(self):
        self.row["after"] = state(self.instance)
        self.accumulate(); self.row["counters"] = dict(self.accumulated)
        self.row["original_player_restored"] = capture(self.controller) == self.original_model
        self.sides.append(copy.deepcopy(self.row)); self.unroot()
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
            ue.log("UEP_DEVICE_COLOR_CASE_OBSERVED "+self.name)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.prepare()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 180., "native device validation total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase != "ready": require(time.monotonic()-self.phase_started < 8., "native device phase timeout: "+self.phase)
            {"ready": self.ready, "default": self.default, "evaluate": self.evaluate, "switched": self.switched,
                "paused": self.paused_tick, "resumed": self.resumed, "removed": self.removed}[self.phase]()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            if hasattr(self, "devices"):
                for handle in self.handles:
                    if self.devices.call_function("IsPropertyActive", handle): self.devices.call_function("RemoveDevicePropertyByHandle", handle)
                self.report["owned_handles_removed"] = all(not self.devices.call_function("IsPropertyActive", handle) and
                    not valid(self.devices.call_function("GetActiveDeviceProperty", handle)) for handle in self.handles)
            self.unroot()
            if hasattr(self, "controller"):
                snap = self.bridge.call_function("CaptureSnapshot")
                self.report["original_player_restored"] = capture(self.controller) == self.original_model and float(snap.Health) == self.original_health
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_DEVICE_COLOR_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DEVICE_COLOR_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPDeviceColorResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPDeviceColorResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
