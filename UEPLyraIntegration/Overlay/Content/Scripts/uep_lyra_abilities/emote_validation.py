"""Real EnhancedInput and native movement -> retained BP/Python Emote pairs."""
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
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from uep_lyra_world.inventory_pad_network_state import capture
from . import emote_mixin as policy
from .emote_contract import PLAN, FALSE_CLAIMS, require, validate


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.paused, self.scope, self.sides = False, False, None, []
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.plan = PLAN
        self.timeout = 250.
        self.report = dict(status="running", error=None, cases=[], native_existing_spec_input_activation=True,
            original_player_restored=False, original_profile_restored=False, original_widget_grant_preserved=False,
            fixture_observers_closed=False, original_cdo_untouched=False, fixture_scopes_created=0, fixture_scopes_closed=0,
            native_movement_producer="Character.LaunchCharacter", native_crouch_producer="Character.Crouch",
            native_external_movement_fixture=True, player_movement_input_tested=False)
        self.report.update({field: False for field in FALSE_CLAIMS})

    def enter(self, name): self.phase, self.phase_started = name, time.monotonic()
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))
    def active(self): return bool(self.ability.get_property("bIsActive"))
    def tasks(self):
        return [task for task in self.ability.get_property("ActiveTasks") if valid(task) and task.is_a(ue.find_class("AbilityTask_PlayMontageAndWait"))]
    def playing(self): return bool(self.anim.call_function("Montage_IsPlaying", self.montage))
    def position(self): return float(self.anim.call_function("Montage_GetPosition", self.montage))

    def widget_state(self):
        native = ue.find_class("UIExtensionHandleFunctions").get_cdo()
        values = list(self.ability.WidgetExtensionHandles)
        def live(handle):
            result = native.call_function("IsValid", handle)
            return result if type(result) is bool else next(value for value in result if type(value) is bool)
        return len(values), all(live(handle) for handle in values)

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            state = bridge.call_function("CaptureSnapshot")
            if not (state.bHeroInputReady and state.bHealthReady and not state.bDamageImmune and state.Health > 0): continue
            controller = self.statics.call_function("GetPlayerController", world, 0)
            model = capture(controller)
            if model is None or "ID_Pistol" not in model["definition"]: continue
            pawn = controller.get_controlled_pawn()
            if int(pawn.CharacterMovement.MovementMode) != 1: continue
            asc, cls = ability_system(pawn), ue.load_class(policy.CLASS)
            values = [value for spec in asc.get_property("ActivatableAbilities").Items
                if valid(spec.Ability) and spec.Ability.get_class() == cls
                for value in list(spec.NonReplicatedInstances) + list(spec.ReplicatedInstances) if valid(value)]
            if len(values) != 1 or values[0].get_property("bIsActive"): continue
            self.world, self.controller, self.pawn, self.asc, self.cls, self.ability = world, controller, pawn, asc, cls, values[0]
            self.movement, self.anim = pawn.CharacterMovement, pawn.Mesh.call_function("GetAnimInstance")
            self.montage = self.ability.get_property("Montage to Play")
            self.action = ue.load_object(ue.find_class("InputAction"), "/ShooterCore/Input/Actions/IA_Emote.IA_Emote")
            self.original_model, self.original_profile = model, str(ue.get_mixin_profile(self.ability))
            self.original = dict(location=pawn.get_actor_location(), rotation=pawn.get_actor_rotation(),
                mode=int(self.movement.MovementMode), custom=int(self.movement.CustomMovementMode),
                crouched=bool(pawn.get_property("bIsCrouched")), montage=self.montage)
            self.original_widgets = self.widget_state()
            require(self.original_widgets == (1, True), "native inherited Emote widget grant missing")
            self.cdo_profile = str(self.cls.get_cdo().GetPythonMixinProfile())
            self.report.update(native_montage_length=float(self.montage.call_function("GetPlayLength")),
                native_class=cls.get_path_name(), native_montage=self.montage.get_path_name(),
                native_policy=[int(self.ability.NetExecutionPolicy), int(self.ability.InstancingPolicy), int(self.ability.ActivationPolicy)])
            self.begin(); return

    def begin(self):
        self.name, self.profile = self.plan[self.index // 2], ("EmoteBlueprintFallback", "EmotePython")[self.index % 2]
        require(not self.active() and not self.playing(), "previous Emote is not settled")
        ue.set_mixin_profile(self.ability, self.profile)
        self.before = policy.instance_snapshot(self.ability)
        self.row = dict(native_type_preserved=self.ability.get_class() == self.cls,
            native_source_preserved=self.ability.call_function("GetAvatarActorFromActorInfo") == self.pawn,
            profile_selected=str(ue.get_mixin_profile(self.ability)) == self.profile, input_injections=0,
            native_montage_observed=False, native_tasks_during=0, native_montage_events=[], native_velocity_observed=0.,
            native_crouch_observed=False, crouched_before_activation=False, native_uncrouch_observed=False,
            profile_teardown_ended_ability=False, native_pause_observed=False, active_during_pause=False)
        self.foreign_calls = 0
        self.scope = SubscriptionScope(); self.report["fixture_scopes_created"] += 1
        self.scope.bind_event(self.pawn, "OnCharacterMovementUpdated", self.foreign_movement)
        if self.name == "crouched-entry": self.pawn.call_function("Crouch", False)
        self.enter("preactivate")

    def foreign_movement(self, delta, old_location, old_velocity):
        self.foreign_calls += 1

    def inject(self, pressed):
        self.controller.inject_enhanced_input_for_action(self.action, pressed)
        if pressed: self.row["input_injections"] += 1

    def preactivate(self):
        if time.monotonic() - self.phase_started < .15: return
        if self.name == "crouched-entry":
            require(bool(self.pawn.get_property("bIsCrouched")), "native pre-entry crouch failed")
            self.row["crouched_before_activation"] = True
        self.inject(True); self.activation_requested = self.game_time(); self.enter("starting")

    def starting(self):
        self.inject(False)
        if not self.active() or not self.playing():
            require(time.monotonic() - self.phase_started < 4., "native EnhancedInput did not start Emote")
            return
        self.active_started = self.game_time()
        self.row["native_montage_observed"] = True
        tasks = self.tasks(); self.row["native_tasks_during"] = len(tasks)
        require(len(tasks) == 1, "native Emote montage task missing/duplicated")
        for event in ("OnCompleted", "OnInterrupted", "OnCancelled"):
            self.scope.bind_event(tasks[0], event, lambda event=event: self.row["native_montage_events"].append(event))
        self.action_done, self.foreign_at_intervention = False, None
        self.enter("running")

    def running(self):
        elapsed = self.game_time() - self.active_started
        if self.active():
            self.row["native_uncrouch_observed"] |= not bool(self.pawn.get_property("bIsCrouched"))
        if self.active() and elapsed >= .25 and not self.action_done and self.may_perform_action():
            require(self.foreign_calls >= 2, "foreign movement listener never ran")
            self.row["foreign_calls_before_intervention"] = self.foreign_calls
            self.foreign_at_intervention, self.action_done = self.foreign_calls, True
            if self.name == "native-movement":
                # Differential01 proves one-frame AddMovementInput leaves both
                # original/Python montage velocities zero. Use actual native
                # external motion (the same API used by launchers), not a raw
                # Velocity write or replay of CheckForMovement.
                self.pawn.call_function("LaunchCharacter", ue.FVector(0., 0., 240.), False, True)
            elif self.name == "native-crouch": self.pawn.call_function("Crouch", False)
            elif self.name == "native-cancel": self.ability.call_function("K2_CancelAbility")
            elif self.name == "external-native-end": self.ability.call_function("K2_EndAbility")
            elif self.name == "active-profile-switch":
                ue.set_mixin_profile(self.ability, "EmotePython" if self.profile == "EmoteBlueprintFallback" else "EmoteBlueprintFallback")
                self.row["profile_teardown_ended_ability"] = not self.active()
            elif self.name == "paused-world-time":
                self.pause_time, self.pause_position = self.game_time(), self.position()
                require(self.statics.call_function("SetGamePaused", self.world, True), "native Emote pause refused")
                self.paused = True; self.enter("paused"); return
        velocity = self.movement.get_property("Velocity")
        self.row["native_velocity_observed"] = max(self.row["native_velocity_observed"],
            float(ue.find_class("KismetMathLibrary").get_cdo().call_function("VSize", velocity)))
        self.row["native_crouch_observed"] |= bool(self.pawn.get_property("bIsCrouched"))
        if self.active():
            require(elapsed < self.report["native_montage_length"] + 3., "native Emote never ended")
            return
        self.row["active_game_seconds"] = elapsed
        self.row["ability_ended"] = True
        self.foreign_at_end = self.foreign_calls
        self.pawn.call_function("UnCrouch", False)
        self.movement.call_function("StopMovementImmediately")
        self.ended_counts = policy.instance_snapshot(self.ability)
        self.enter("settled")

    def may_perform_action(self): return True

    def paused_tick(self):
        if time.monotonic() - self.phase_started < .3: return
        self.row["native_pause_observed"] = self.game_time() == self.pause_time and abs(self.position() - self.pause_position) < .0001
        self.row["active_during_pause"] = self.active() and len(self.tasks()) == 1
        require(self.statics.call_function("SetGamePaused", self.world, False), "native Emote unpause refused")
        self.paused = False; self.enter("running")

    def restore_player(self):
        self.movement.call_function("StopMovementImmediately")
        self.pawn.set_actor_location(self.original["location"])
        self.pawn.set_actor_rotation(self.original["rotation"])
        self.movement.call_function("SetMovementMode", self.original["mode"], self.original["custom"])
        if self.original["crouched"]: self.pawn.call_function("Crouch", False)
        else: self.pawn.call_function("UnCrouch", False)

    def player_matches(self):
        point = self.pawn.get_actor_location()
        return capture(self.controller) == self.original_model and not self.playing() and \
            bool(self.pawn.get_property("bIsCrouched")) == self.original["crouched"] and \
            all(abs(getattr(point, field) - getattr(self.original["location"], field)) < .01 for field in ("x", "y", "z"))

    def close_observer(self):
        if self.scope is not None:
            self.scope.close(); self.scope = None; self.report["fixture_scopes_closed"] += 1

    def settled(self):
        if time.monotonic() - self.phase_started < .35 or self.playing():
            require(time.monotonic() - self.phase_started < 3., "native Emote montage stop did not settle")
            return
        counts = policy.instance_snapshot(self.ability)
        self.row.update(native_montage_stopped=not self.playing(), native_tasks_after=len(self.tasks()),
            native_end_callbacks=len(self.row["native_montage_events"]),
            widget_grant_preserved=self.widget_state() == self.original_widgets,
            foreign_calls_after_end=self.foreign_calls - self.foreign_at_end,
            no_late_python_movement=counts["movement_checks"] == self.ended_counts["movement_checks"])
        self.row["counters"] = {key: value - self.before[key] for key, value in counts.items()}
        # The original BP intentionally remains a true ClearAll baseline. This
        # fixture cleanup removes only its own lingering original-BP binding.
        self.ability.call_function(policy.REMOVE, self.pawn)
        self.close_observer(); self.restore_player(); self.enter("restored")

    def restored(self):
        if time.monotonic() - self.phase_started < .2: return
        self.row["player_restored"] = self.player_matches()
        require(self.row["player_restored"], "native Emote player/inventory restoration differs")
        self.complete_trial()

    def complete_trial(self):
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1]))
            self.sides = []; ue.log("UEP_EMOTE_CASE_OBSERVED " + self.name)
        self.index += 1
        if self.index == len(self.plan) * 2: self.finish()
        else: self.begin()

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < self.timeout, "native Emote timeout: " + self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "paused": self.paused_tick()
            else: getattr(self, self.phase)()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        try:
            if self.paused: self.statics.call_function("SetGamePaused", self.world, False); self.paused = False
            if hasattr(self, "ability"):
                self.inject(False)
                if self.active(): self.ability.call_function("K2_EndAbility")
                self.ability.call_function(policy.REMOVE, self.pawn)
                self.close_observer(); self.restore_player()
                self.report["original_player_restored"] = self.player_matches()
                self.report["original_widget_grant_preserved"] = self.widget_state() == self.original_widgets
                ue.set_mixin_profile(self.ability, self.original_profile)
                self.report["original_profile_restored"] = str(ue.get_mixin_profile(self.ability)) == self.original_profile
                self.report["original_cdo_untouched"] = str(self.cls.get_cdo().GetPythonMixinProfile()) == self.cdo_profile
            self.close_observer(); self.report["fixture_observers_closed"] = self.scope is None
        except Exception: error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_EMOTE_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report, self.plan)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_EMOTE_SHUTDOWN_" + self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPEmoteResult=")), None)
if result is not None:
    validation = Validation(result)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
