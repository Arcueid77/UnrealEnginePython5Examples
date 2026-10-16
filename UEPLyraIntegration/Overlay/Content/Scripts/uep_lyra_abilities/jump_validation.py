"""Native EnhancedInput -> production granted GAS Jump, original/Python pairs."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_world.effect_pad_mixin import ability_system
from . import jump_mixin as policy
from .jump_contract import PLAN, FALSE_CLAIMS, require, validate


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.finished, self.index, self.events, self.sides = False, 0, [], []
        self.report = dict(schema_version=1, status="running", error=None, cases=[],
            enhanced_input_injection=True, native_gas_instance=False, player_restored=False,
            jump_observer_closed=False, **{field: False for field in FALSE_CLAIMS})

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def game_time(self):
        return float(self.statics.call_function("GetTimeSeconds", self.world))

    def ready(self):
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bExperienceLoaded and snap.bHealthReady and snap.bHeroInputReady): continue
            if getattr(self, "require_combat_ready", False) and (snap.bDamageImmune or snap.Health <= 0): continue
            self.world = world
            self.controller = self.statics.call_function("GetPlayerController", world, 0)
            self.pawn = self.controller.get_controlled_pawn()
            if not valid(self.pawn): continue
            self.movement = self.pawn.CharacterMovement
            if int(self.movement.MovementMode) != 1: continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            self.cls, self.asc = ue.load_class(policy.CLASS), ability_system(self.pawn)
            instances = []
            for spec in self.asc.get_property("ActivatableAbilities").Items:
                if valid(spec.Ability) and spec.Ability.get_class() == self.cls:
                    instances.extend(list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances))
            if len(instances) != 1: continue
            self.ability = instances[0]
            self.input = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetLocalPlayerSubsystem", self.controller, ue.find_class("EnhancedInputLocalPlayerSubsystem"))
            require(valid(self.input), "actual local-player EnhancedInput subsystem missing")
            self.action = ue.load_object(ue.find_class("InputAction"), "/Game/Input/Actions/IA_Jump.IA_Jump")
            self.original = dict(location=self.pawn.get_actor_location(), rotation=self.pawn.get_actor_rotation(),
                aim=self.controller.call_function("GetControlRotation"), mode=int(self.movement.MovementMode),
                custom=int(self.movement.CustomMovementMode))
            self.player_class, self.original_jump = self.pawn.get_class(), self.pawn.find_function("OnJumped")
            require(not any(row["target_class"] == self.player_class for row in ue.get_registered_mixins()),
                    "test observer must not replace a production Character mixin")
            owner = self
            class ObserveJump:
                def OnJumped(self):
                    if self == owner.pawn: owner.events.append(self.get_path_name())
                    self.call_mixin_original("OnJumped")
            ue.register_mixin_profile(self.player_class, "UEPJumpObserve", ObserveJump, make_default=True)
            self.report.update(native_gas_instance=True, pawn=self.pawn.get_path_name(),
                ability=self.ability.get_path_name(), ability_class=self.cls.get_path_name())
            self.begin(); return

    def begin(self):
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        require(not self.ability.get_property("bIsActive") and int(self.movement.MovementMode) == 1,
                "jump trial starts active/airborne")
        ue.set_mixin_profile(self.ability, self.profile)
        self.stats_before, self.event_start = policy.snapshot(), len(self.events)
        self.start_z, self.peak, self.held, self.injections = float(self.pawn.get_actor_location().z), 0., False, 0
        self.intervention, self.state_stopped = None, False
        self.native_started = self.game_time()
        self.enter("hold")

    def inject(self, pressed):
        self.input.call_function("InjectInputVectorForAction", self.action, ue.FVector(1. if pressed else 0., 0., 0.))
        if pressed: self.injections += 1

    def hold(self):
        self.peak = max(self.peak, float(self.pawn.get_actor_location().z)-self.start_z)
        elapsed = self.game_time()-self.native_started
        active = bool(self.ability.get_property("bIsActive"))
        if active and elapsed > .08 and self.peak > 20.: self.held = True
        delay = max(.35 if self.name == "release-held" else .15, getattr(self, "minimum_hold_seconds", 0.))
        # The first native frame can include startup work. Require actual
        # repeated input injections instead of inferring a hold from elapsed
        # wall/game time across that first frame.
        if not (self.held and elapsed >= delay and self.injections >= 2):
            require(elapsed < 3., "native input did not hold/raise Jump: "+repr((active, self.peak, elapsed)))
            self.inject(True); return
        self.intervention = self.name
        if self.name == "native-cancel": self.ability.call_function("K2_CancelAbility")
        elif self.name == "external-native-end": self.ability.call_function("K2_EndAbility")
        elif self.name == "active-profile-switch":
            ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
        elif self.name == "native-state-end":
            self.ability.call_function("EndAbilityState", "Jumping")
            self.state_stopped = bool(self.ability.get_property("bIsActive")) and not self.pawn.get_property("bPressedJump")
            require(self.state_stopped, "native state delegate did not stop Jump while ability remains active")
        self.inject(False); self.enter("land")

    def land(self):
        self.peak = max(self.peak, float(self.pawn.get_actor_location().z)-self.start_z)
        if self.ability.get_property("bIsActive") or int(self.movement.MovementMode) != 1:
            require(time.monotonic()-self.phase_started < 10., "jump ability/character did not end/land")
            return
        if time.monotonic()-self.phase_started < .2: return
        row = dict(active_while_held=self.held, native_type_preserved=self.ability.get_class() == self.cls,
            peak_rise=self.peak, jump_events=len(self.events)-self.event_start, landed=True,
            active_after=bool(self.ability.get_property("bIsActive")), pressed_jump_after=bool(self.pawn.get_property("bPressedJump")),
            intervention=self.intervention, profile_after=str(ue.get_mixin_profile(self.ability)),
            input_injections=self.injections, native_state_stopped_jump=self.state_stopped)
        self.sides.append(row)
        after = policy.snapshot()
        counts = {key: after[key]-self.stats_before[key] for key in after if isinstance(after[key], int) and key != "active_count"}
        self.restore_player()
        self.record_trial(row, counts)
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1], python_counters=counts))
            self.sides = []
            ue.log("UEP_JUMP_ABILITY_CASE_PASSED "+self.name)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.begin()

    def record_trial(self, row, counts):
        """Optional network orchestration hook; no production callback replay."""

    def restore_player(self):
        if not hasattr(self, "original"): return
        self.movement.call_function("StopMovementImmediately")
        self.pawn.set_actor_location(self.original["location"]); self.pawn.set_actor_rotation(self.original["rotation"])
        self.controller.call_function("SetControlRotation", self.original["aim"])
        self.movement.call_function("SetMovementMode", self.original["mode"], self.original["custom"])
        point = self.pawn.get_actor_location()
        require(max(abs(getattr(point, key)-getattr(self.original["location"], key)) for key in ("x", "y", "z")) < .01,
                "native Jump fixture did not restore player position")
        self.report["player_restored"] = True

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 210., "native Jump timeout: "+self.phase)
            if hasattr(self, "world"):
                # Bots can be granted after the local hero becomes ready.
                # Stop newly arrived native AI; never change Health/immunity.
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "hold": self.hold()
            elif self.phase == "land": self.land()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finish(self, failure=None):
        if self.finished: return
        self.finished = True
        try:
            if hasattr(self, "ability"):
                self.inject(False)
                if self.ability.get_property("bIsActive"): self.ability.call_function("K2_CancelAbility")
                ue.set_mixin_profile(self.ability, "Python")
            self.restore_player()
            if hasattr(self, "original_jump"):
                require(ue.unregister_mixin(self.player_class) and self.pawn.find_function("OnJumped") == self.original_jump,
                        "native Jump observer not restored")
                self.report["jump_observer_closed"] = True
        except Exception: failure = (failure or "")+traceback.format_exc()
        self.report.update(status="failed" if failure else "awaiting_shutdown", error=failure)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if failure else ue.log)("UEP_JUMP_ABILITY_DIFFERENTIAL_"+("FAILED "+failure if failure else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_JUMP_ABILITY_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPJumpAbilityResult=")), None)
if result is not None:
    validation = Validation(result)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
