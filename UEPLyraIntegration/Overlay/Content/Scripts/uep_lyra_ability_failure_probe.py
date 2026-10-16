"""Local typed failure messages in the real two-client weapon/lifetime lane."""

import time
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraAbilitySimpleFailureMessage
from uep_lyra_hud import ability_failure_mixin as failure
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_protocol import require


def visual(widget):
    return {"text": str(widget.FailureReasonTextWidget.call_function("GetText")),
            "visibility": int(widget.call_function("GetVisibility"))}


class AbilityFailureProbe:
    def __init__(self, peer):
        self.peer = peer
        self.world_token = self.candidate = self.baseline = self.helper = None
        self.phase, self.completed = None, False
        self.comparisons = self.visible_comparisons = 0
        self.debug = {"reason": "not-created"}

    def close(self):
        if valid(self.baseline):
            self.baseline.RemoveFromParent()
            self.baseline.remove_from_root()
        if valid(self.helper):
            self.helper.remove_from_root()
        self.world_token = self.candidate = self.baseline = self.helper = None
        self.phase, self.completed = None, False

    def observe(self, controller, player):
        candidates = [ue.find_object(path) for path in failure.snapshot()["active_widgets"]]
        owned = [widget for widget in candidates if valid(widget) and widget.call_function("GetOwningPlayer") == controller]
        require(len(owned) <= 1, "duplicate production failure-feedback owner")
        if not owned:
            self.debug = {"reason": "production-widget-unavailable", "active": failure.snapshot()["active_widgets"]}
            return None
        candidate = owned[0]
        if self.world_token != player["world_token"] or self.candidate != candidate:
            self.close()
            self.candidate, self.controller = candidate, controller
            self.baseline = controller.create_widget(candidate.get_class())
            self.baseline.add_to_root()
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.AddToViewport(450)
            self.baseline.call_function("SetRenderOpacity", 0.0)
            self.baseline.call_function(failure.RESUME)
            self.helper = ue.new_object(candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetGameInstanceSubsystem", controller, ue.find_class("GameplayMessageSubsystem"))
            require(valid(self.router), "failure message subsystem missing")
            self.world_token = player["world_token"]
        actual, original = visual(candidate), visual(self.baseline)
        self.debug = {"reason": "ready", "phase": self.phase, "python": actual, "blueprint": original, "world_token": self.world_token}
        if self.phase is not None:
            if actual != original:
                self.debug["reason"] = "failure-visual-mismatch"
                return None
            require(candidate._uep_failure_messages >= self.owner_before + 1, "failure owner message missing")
            require(candidate._uep_failure_foreign >= self.foreign_before + 1, "failure null-controller filter missing")
            self.comparisons += 1
            if actual["visibility"] == 3 and actual["text"] == self.expected_reason:
                self.visible_comparisons += 1
            self.completed = actual["visibility"] == 1 and self.visible_comparisons > 0
        return {"production_widget": True, "widget": candidate.get_path_name(), "class": candidate.get_class().get_name(),
                "profile": str(ue.get_mixin_profile(candidate)), "controller": controller.get_path_name(),
                "pawn": candidate.call_function("GetOwningPlayerPawn").get_path_name(), "world_token": self.world_token,
                "phase": self.phase, "completed": self.completed, "synthetic_local_messages": True,
                "native_ability_producer_tested": False, "replicated_failure_message_tested": False,
                "fixture_event_invoked": False, "timer_clock": "native-retriggerable-delay",
                "foreign_controller_kind": "null-controller", "comparisons": self.comparisons,
                "visible_comparisons": self.visible_comparisons,
                "owner_deliveries": candidate._uep_failure_messages - self.owner_before if self.phase else 0,
                "foreign_rejections": candidate._uep_failure_foreign - self.foreign_before if self.phase else 0,
                "expected_synthetic_reason": self.expected_reason if self.phase else None,
                "phase_elapsed": time.monotonic() - self.started if self.phase else 0,
                "python": actual, "blueprint": original}

    def begin(self, phase):
        require(valid(self.candidate) and valid(self.helper), "failure probe is not armed")
        self.phase, self.completed = phase, False
        self.comparisons = self.visible_comparisons = 0
        self.owner_before, self.foreign_before = self.candidate._uep_failure_messages, self.candidate._uep_failure_foreign
        self.expected_reason = "UEP " + self.peer + " " + phase
        self.started = time.monotonic()
        channel = GameplayTag(TagName=failure.CHANNEL)
        self.helper.call_function("BroadcastFailure", self.router, channel,
            LyraAbilitySimpleFailureMessage(PlayerController=self.controller, UserFacingReason=self.expected_reason))
        retained = visual(self.candidate)
        self.helper.call_function("BroadcastFailure", self.router, channel,
            LyraAbilitySimpleFailureMessage(UserFacingReason="foreign null controller"))
        require(visual(self.candidate) == retained, "foreign controller changed failure presentation")
