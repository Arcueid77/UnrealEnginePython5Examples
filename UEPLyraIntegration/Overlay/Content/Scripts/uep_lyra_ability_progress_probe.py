"""Opt-in network UI comparison using local, synthetic duration messages.

Game time, the production widget and native Slate Tick are real. This is not
replicated GameplayMessage delivery or a native interaction ability producer.
"""

import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage

from uep_lyra_hud import ability_progress_mixin as progress
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_protocol import require


def visual(widget):
    material = widget.ProgressBorder.call_function("GetDynamicMaterial")
    color = material.call_function("K2_GetVectorParameterValue", "ActiveRange")
    return {"duration": float(widget.Duration), "start": float(widget.StartTime),
            "visibility": int(widget.call_function("GetVisibility")),
            "text": str(widget.ProgressText.call_function("GetText")),
            "percent": float(material.call_function("K2_GetScalarParameterValue", "Percent")),
            "active_range": [float(getattr(color, field)) for field in ("r", "g", "b", "a")]}


class AbilityProgressProbe:
    def __init__(self):
        self.world_token = self.candidate = self.baseline = self.helper = None
        self.phase = None
        self.completed = False
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
        candidates = [ue.find_object(path) for path in progress.snapshot()["active_widgets"]]
        candidates = [widget for widget in candidates if valid(widget) and widget.call_function("GetOwningPlayer") == controller]
        require(len(candidates) <= 1, "duplicate production ability progress owner")
        if not candidates:
            self.debug = {"reason": "production-widget-unavailable", "active": progress.snapshot()["active_widgets"]}
            return None
        candidate = candidates[0]
        if self.world_token != player["world_token"] or self.candidate != candidate:
            self.close()
            self.candidate, self.controller = candidate, controller
            self.baseline = controller.create_widget(candidate.get_class())
            self.baseline.add_to_root()
            self.baseline.AddToViewport(450)
            self.baseline.call_function("SetRenderOpacity", 0.0)
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.call_function(progress.RESUME_EVENT)
            self.helper = ue.new_object(candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetGameInstanceSubsystem", controller, ue.find_class("GameplayMessageSubsystem"))
            require(valid(self.router), "duration message subsystem missing")
            self.world_token = player["world_token"]
        original, actual = visual(self.baseline), visual(candidate)
        self.debug = {"reason": "ready", "phase": self.phase, "world_token": self.world_token,
                      "python": actual, "blueprint": original}
        if self.phase is not None:
            if (any(original[key] != actual[key] for key in ("duration", "start", "visibility", "text", "active_range"))
                    or abs(original["percent"] - actual["percent"]) >= 0.00001):
                self.debug["reason"] = "duration-visual-mismatch"
                return None
            require(candidate._uep_progress_messages == self.owner_before + 1, "duration owner delivery duplicated")
            require(candidate._uep_progress_foreign_messages == self.foreign_before + 1, "duration foreign filtering duplicated")
            self.comparisons += 1
            if actual["visibility"] == 0 and 0.0 < actual["percent"] < 1.0:
                self.visible_comparisons += 1
            self.completed = (actual["visibility"] == 1 and actual["percent"] >= 1.0
                              and candidate._uep_progress_ticks > self.ticks_before + 1)
        return {"production_widget": True, "widget": candidate.get_path_name(),
                "class": candidate.get_class().get_name(), "profile": ue.get_mixin_profile(candidate),
                "controller": controller.get_path_name(), "pawn": candidate.call_function("GetOwningPlayerPawn").get_path_name(),
                "world_token": self.world_token, "phase": self.phase, "completed": self.completed,
                "synthetic_local_messages": True, "native_interaction_producer_tested": False,
                "replicated_duration_message_tested": False, "python_tick_called_by_probe": False,
                "owner_deliveries": candidate._uep_progress_messages - self.owner_before if self.phase is not None else 0,
                "foreign_rejections": candidate._uep_progress_foreign_messages - self.foreign_before if self.phase is not None else 0,
                "comparisons": self.comparisons, "visible_comparisons": self.visible_comparisons,
                "foreign_instigator_kind": "owning-controller-not-pawn",
                "automatic_tick_delta": candidate._uep_progress_ticks - self.ticks_before if self.phase is not None else 0,
                "blueprint": original, "python": actual}

    def begin(self, phase):
        require(valid(self.candidate) and valid(self.helper), "duration probe is not armed")
        pawn = self.controller.get_controlled_pawn()
        self.phase, self.completed = phase, False
        self.comparisons = self.visible_comparisons = 0
        self.owner_before = self.candidate._uep_progress_messages
        self.foreign_before = self.candidate._uep_progress_foreign_messages
        self.ticks_before = self.candidate._uep_progress_ticks
        channel = GameplayTag(TagName=progress.CHANNEL)
        self.helper.call_function("BroadcastDuration", self.router, channel,
                                  LyraInteractionDurationMessage(Instigator=pawn, Duration=1.25))
        retained = (self.candidate.Duration, self.candidate.StartTime)
        self.helper.call_function("BroadcastDuration", self.router, channel,
                                  LyraInteractionDurationMessage(Instigator=self.controller, Duration=77.0))
        require((self.candidate.Duration, self.candidate.StartTime) == retained, "foreign duration changed production model")
