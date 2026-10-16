"""Local synthetic Dash duration on production UI in the two-client lane."""
import unreal_engine as ue
import time
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage
from uep_lyra_hud import dash_cooldown_mixin as dash
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_protocol import require
from uep_lyra_hud.validation_census import UniqueWidgetCensus


def visual(widget):
    return {"duration": float(widget.Duration), "start": float(widget.StartTime), "charging": bool(widget.Charging),
            "visibility": int(widget.CenteringOvr.call_function("GetVisibility")),
            "glow": float(widget.BarGlow.call_function("GetDynamicMaterial").call_function("K2_GetScalarParameterValue", "AnimateArcFill")),
            "fill": float(widget.BarFill.call_function("GetDynamicMaterial").call_function("K2_GetScalarParameterValue", "AnimateArcFill"))}


class DashCooldownProbe:
    def __init__(self):
        self.world_token = self.candidate = self.baseline = self.helper = None
        self.phase, self.completed = None, False
        self.comparisons = self.visible_comparisons = 0
        self.debug = {"reason": "not-created"}
        self.census = UniqueWidgetCensus()

    def close(self):
        if valid(self.baseline):
            self.baseline.RemoveFromParent()
            self.baseline.remove_from_root()
        if valid(self.helper):
            self.helper.remove_from_root()
        self.world_token = self.candidate = self.baseline = self.helper = None
        self.phase, self.completed = None, False

    def observe(self, controller, player):
        dash.pools.refresh()  # Disarm removed pool entries before owner census.
        candidates = [ue.find_object(path) for path in dash.snapshot()["active_widgets"]]
        candidates = [widget for widget in candidates if valid(widget) and widget.call_function("GetOwningPlayer") == controller]
        if not self.census.ready([widget.get_path_name() for widget in candidates], player["world_token"], time.monotonic()):
            self.debug = {"reason": "native-dash-entry-census-not-settled", "count": len(candidates),
                          "paths": [widget.get_path_name() for widget in candidates]}
            return None
        if not candidates:
            self.debug = {"reason": "production-widget-unavailable", "active": dash.snapshot()["active_widgets"]}
            return None
        candidate = candidates[0]
        if self.world_token != player["world_token"] or self.candidate != candidate:
            self.close()
            self.candidate, self.controller = candidate, controller
            self.baseline = controller.create_widget(candidate.get_class())
            self.baseline.add_to_root()
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.AddToViewport(450)
            self.baseline.call_function("SetRenderOpacity", 0.0)
            self.baseline.call_function(dash.RESUME)
            self.helper = ue.new_object(candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetGameInstanceSubsystem", controller, ue.find_class("GameplayMessageSubsystem"))
            require(valid(self.router), "Dash message subsystem missing")
            self.world_token = player["world_token"]
        actual, original = visual(candidate), visual(self.baseline)
        self.debug = {"reason": "ready", "world_token": self.world_token, "phase": self.phase, "python": actual, "blueprint": original}
        if self.phase is not None:
            if (any(actual[key] != original[key] for key in ("duration", "start", "charging", "visibility")) or
                    any(abs(actual[key] - original[key]) >= 0.00001 for key in ("glow", "fill"))):
                self.debug["reason"] = "dash-visual-mismatch"
                return None
            require(candidate._uep_dash_messages == self.owner_before + 1, "Dash owner delivery missing/duplicate")
            require(candidate._uep_dash_foreign == self.foreign_before + 1, "Dash foreign rejection missing/duplicate")
            self.comparisons += 1
            if actual["charging"] and 0.0 < actual["fill"] < 1.0:
                self.visible_comparisons += 1
            self.completed = not actual["charging"] and actual["fill"] == actual["glow"] == 1.0 and self.visible_comparisons > 0
        return {"production_widget": True, "widget": candidate.get_path_name(), "class": candidate.get_class().get_name(),
                "profile": str(ue.get_mixin_profile(candidate)), "controller": controller.get_path_name(),
                "pawn": candidate.call_function("GetOwningPlayerPawn").get_path_name(), "world_token": self.world_token,
                "phase": self.phase, "completed": self.completed, "synthetic_local_messages": True,
                "native_dash_producer_tested": False, "replicated_duration_message_tested": False,
                "python_tick_called_by_probe": False, "foreign_instigator_kind": "owning-controller-not-pawn",
                "comparisons": self.comparisons, "visible_comparisons": self.visible_comparisons,
                "automatic_tick_delta": candidate._uep_dash_ticks - self.ticks_before if self.phase else 0,
                "owner_deliveries": candidate._uep_dash_messages - self.owner_before if self.phase else 0,
                "foreign_rejections": candidate._uep_dash_foreign - self.foreign_before if self.phase else 0,
                "python": actual, "blueprint": original}

    def begin(self, phase):
        require(valid(self.candidate) and valid(self.helper), "Dash probe not armed")
        self.phase, self.completed = phase, False
        self.comparisons = self.visible_comparisons = 0
        self.owner_before, self.foreign_before = self.candidate._uep_dash_messages, self.candidate._uep_dash_foreign
        self.ticks_before = self.candidate._uep_dash_ticks
        channel = GameplayTag(TagName=dash.CHANNEL)
        self.helper.call_function("BroadcastDuration", self.router, channel,
            LyraInteractionDurationMessage(Instigator=self.controller.get_controlled_pawn(), Duration=1.25))
        retained = (self.candidate.Duration, self.candidate.StartTime, self.candidate.Charging)
        self.helper.call_function("BroadcastDuration", self.router, channel,
            LyraInteractionDurationMessage(Instigator=self.controller, Duration=77.0))
        require((self.candidate.Duration, self.candidate.StartTime, self.candidate.Charging) == retained, "foreign Dash changed native model")
