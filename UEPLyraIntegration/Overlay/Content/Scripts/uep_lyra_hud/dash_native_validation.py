"""Real GAS Dash request and death event, not a synthetic duration producer.

Invalid-health feedback is a separately declared synthetic-message fixture.
No ability/CDO/Health/velocity is edited and no widget event is invoked.
"""
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayEventData, LyraAbilitySimpleFailureMessage
from .dash_cooldown_validation import DashValidation, state, check
from . import dash_cooldown_mixin as dash, ability_failure_mixin as failure
from .weapon_observer import valid

ABILITY = "/ShooterCore/Game/Dash/GA_Hero_Dash.GA_Hero_Dash_C"
CASES = ("native-dash-duration", "native-repeat-request-rejected", "native-countdown-completed",
         "native-death-started", "invalid-health-feedback-rejected")


class NativeDashValidation(DashValidation):
    def __init__(self, result):
        super().__init__(result)
        self.report.update(mode="native-dash-gas-death-and-invalid-health", cases=[],
                           native_dash_producer_tested=False, native_death_event_tested=False,
                           lethal_damage_tested=False, invalid_health_feedback_tested=False,
                           fixture_event_invoked=False, ability_or_health_properties_written=False,
                           physical_key_input_tested=False, native_failure_producer_tested=False,
                           duration_broadcast_called_by_fixture=False)

    def setup_failure(self):
        cls = ue.load_class(failure.CLASS)
        widgets, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("GetAllWidgetsOfClass", self.world, [], cls, False)
        owned = [widget for widget in widgets if widget.call_function("GetOwningPlayer") == self.controller]
        check(len(owned) == 1, "native failure feedback production owner missing/duplicate")
        self.failure_candidate = owned[0]
        self.failure_baseline = self.controller.create_widget(cls)
        self.failure_baseline.add_to_root()
        self.widgets.append(self.failure_baseline)
        ue.set_mixin_profile(self.failure_baseline, "BlueprintFallback")
        self.failure_baseline.AddToViewport(450)
        self.failure_baseline.call_function("SetRenderOpacity", 0.0)
        self.failure_baseline.call_function(failure.RESUME)
        self.asc = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("GetAbilitySystemComponent", self.pawn)
        check(valid(self.asc), "native Pawn ASC unavailable")
        self.ability = ue.load_class(ABILITY)
        self.health = ue.find_class("LyraHealthComponent").get_cdo().call_function("FindHealthComponent", self.pawn)
        check(valid(self.health), "native Health unavailable")
        self.report["ability_class"] = self.ability.get_path_name()
        self.report["request_entry"] = "native ASC.TryActivateAbilityByClass; movement intent via Pawn.AddMovementInput"
        self.enter("move")

    @staticmethod
    def failure_state(widget):
        return {"text": str(widget.FailureReasonTextWidget.call_function("GetText")),
                "visibility": int(widget.call_function("GetVisibility"))}

    def invalid_health(self):
        # Clearing UserWidget's owning player can fall back to player zero.
        # Use the native post-death controller transition, not a fake pointer
        # or Health/CDO write, to establish an actually absent owning Pawn.
        self.controller.call_function("UnPossess")
        check(self.controller.get_controlled_pawn() is None, "native UnPossess did not remove Pawn")
        cls = self.failure_candidate.get_class()
        pair = [self.controller.create_widget(cls), self.controller.create_widget(cls)]
        for index, widget in enumerate(pair):
            widget.add_to_root()
            self.widgets.append(widget)
            if index == 1:
                ue.set_mixin_profile(widget, "BlueprintFallback")
            widget.AddToViewport(450)
            if index == 1:
                widget.call_function(failure.RESUME)
            check(widget.call_function("GetOwningPlayerPawn") is None, "invalid-health fixture has a Pawn")
        before = [self.failure_state(widget) for widget in pair]
        rejects = failure.snapshot()["health_rejections"]
        expected_rejections = failure.snapshot()["active_count"]
        self.helper.call_function("BroadcastFailure", self.router, GameplayTag(TagName=failure.CHANNEL),
                                  LyraAbilitySimpleFailureMessage(PlayerController=self.controller, UserFacingReason="UEP invalid health fixture"))
        check([self.failure_state(widget) for widget in pair] == before, "invalid Health changed failure UI")
        check(expected_rejections > 0 and failure.snapshot()["health_rejections"] == rejects + expected_rejections,
              "Python invalid-health rejection count differs")
        self.report["cases"].append({"name": "invalid-health-feedback-rejected", "synthetic_payload": True,
                                     "python": before[0], "blueprint": before[1], "owner_has_pawn": False})
        self.report["invalid_health_feedback_tested"] = True

    def finish(self, error=None):
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic() - self.started)
        self.write()
        (ue.log_error if error else ue.log)("UEP_DASH_NATIVE_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        final, failed = dash.snapshot(), failure.snapshot()
        self.report.update(shutdown=final, failure_shutdown=failed)
        pool = final["pool_lifetime"]
        if (final["active_count"] or final["scopes_created"] != final["scopes_closed"] or final["errors"] or
                final["health_binds"] != final["health_unbinds"] or pool["active_count"] or pool["ticker_active"] or
                pool["registered"] != pool["unregistered"] or pool["errors"] or failed["active_count"] or
                failed["scopes_created"] != failed["scopes_closed"] or failed["errors"]):
            self.report.update(status="failed", error="native Dash/failure/pool scopes survived exit")
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_NATIVE_SHUTDOWN_" + self.report["status"].upper())

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 200, "native Dash total timeout")
            if self.phase == "ready":
                self.ready()
                if self.phase != "ready":
                    self.setup_failure()
                return True
            elapsed = time.monotonic() - self.phase_started
            check(elapsed < 25, "native Dash phase timeout: " + self.phase)
            if self.phase == "move":
                self.pawn.call_function("AddMovementInput", self.pawn.call_function("GetActorForwardVector"), 1.0, False)
                if elapsed > 0.15:
                    self.before_messages = self.candidate._uep_dash_messages
                    self.failure_before = self.failure_candidate._uep_failure_messages
                    accepted = self.asc.call_function("TryActivateAbilityByClass", self.ability, False)
                    self.report["native_request_accepted"] = accepted
                    check(accepted is True, "granted native Dash request rejected")
                    self.enter("duration")
            elif self.phase == "duration" and elapsed > 0.3:
                check(self.candidate._uep_dash_messages == self.before_messages + 1, "native Dash duration not exact-once")
                check(self.candidate.Charging and self.candidate.Duration > 0, "native Dash did not start charging UI")
                self.compare("native-dash-duration", True)
                self.report["native_dash_producer_tested"] = True
                rejected = self.asc.call_function("TryActivateAbilityByClass", self.ability, False)
                check(rejected is False and self.candidate._uep_dash_messages == self.before_messages + 1, "native repeated Dash not rejected")
                self.report["cases"].append({"name": "native-repeat-request-rejected", "accepted": rejected,
                                             "duration_deliveries": self.candidate._uep_dash_messages - self.before_messages})
                deliveries = self.failure_candidate._uep_failure_messages - self.failure_before
                self.report["native_failure_delivery_count"] = deliveries
                self.report["native_failure_producer_tested"] = deliveries == 1
                if deliveries:
                    check(deliveries == 1, "native failure delivered more than once")
                    actual, original = self.failure_state(self.failure_candidate), self.failure_state(self.failure_baseline)
                    check(actual == original and actual["visibility"] == 3, "native failure BP/Python mismatch")
                    self.report["native_failure_presentation"] = actual
                self.enter("expiry")
            elif self.phase == "expiry" and not any(widget.Charging for widget in (self.candidate, self.baseline)) and elapsed > 0.5:
                self.compare("native-countdown-completed", True)
                self.report["image"] = str(self.path.parent / "dash-cooldown.png")
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="' + self.report["image"] + '"', self.controller)
                self.enter("death-shot-wait")
            elif self.phase == "death-shot-wait" and elapsed > 0.4:
                before = self.candidate._uep_dash_deaths
                tag = GameplayTag(TagName="GameplayEvent.Death")
                ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor", self.pawn, tag,
                    GameplayEventData(EventTag=tag, Instigator=self.pawn, Target=self.pawn))
                check(self.health.call_function("IsDeadOrDying") is True, "native GAS death state not reached")
                check(self.candidate._uep_dash_deaths == before + 1, "native death delegate not exact-once")
                actual, original = state(self.candidate), state(self.baseline)
                check(actual["visibility"] == original["visibility"] == 1, "native death did not hide both Dash wrappers")
                self.report["cases"].append({"name": "native-death-started", "death_state": int(self.health.call_function("GetDeathState")),
                                             "python": actual, "blueprint": original, "death_callbacks": 1})
                self.report["native_death_event_tested"] = True
                self.report["dead_health_tested"] = True
                self.invalid_health()
                check([case["name"] for case in self.report["cases"]] == list(CASES), "native Dash cases incomplete")
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


result = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("-UEPDashNativeResult=")), None)
if result:
    _validation = NativeDashValidation(result)
    _ticker = ue.add_ticker(_validation.tick, 0.0)
