"""Production respawn UI lifetime and local typed messages in the network lane."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage, LyraVerbMessage
from uep_lyra_hud import respawn_timer_mixin as respawn
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_protocol import require
from uep_lyra_respawn_protocol import foreign_delivery_evidence


def visual(widget):
    return {"duration": float(widget.Duration), "start": float(widget.StartTime), "respawning": bool(widget.Respawning),
            "visibility": int(widget.call_function("GetVisibility")), "numeric": float(widget.Time.call_function("GetTargetValue")),
            "text": str(widget.Time.call_function("GetText")),
            "glow": float(widget.FillGlow.call_function("GetDynamicMaterial").call_function("K2_GetScalarParameterValue", "AnimateArcFill")),
            "fill": float(widget.Fill.call_function("GetDynamicMaterial").call_function("K2_GetScalarParameterValue", "AnimateArcFill")),
            "timer_active": bool(respawn.systems().call_function("K2_IsTimerActive", widget, "UpdateRespawnText"))}


class RespawnTimerProbe:
    def __init__(self):
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
        respawn.pools.refresh()
        owned = [ue.find_object(path) for path in respawn.snapshot()["active_widgets"]]
        owned = [widget for widget in owned if valid(widget) and widget.call_function("GetOwningPlayer") == controller]
        require(len(owned) <= 1, "duplicate production respawn owner")
        if not owned:
            self.debug = {"reason": "production-widget-unavailable", "active": respawn.snapshot()["active_widgets"]}
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
            self.baseline.call_function(respawn.RESUME)
            self.helper = ue.new_object(candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetGameInstanceSubsystem", controller, ue.find_class("GameplayMessageSubsystem"))
            require(valid(self.router), "respawn router missing")
            self.world_token = player["world_token"]
        actual, original = visual(candidate), visual(self.baseline)
        self.debug = {"reason": "ready", "phase": self.phase, "python": actual, "blueprint": original, "world_token": self.world_token}
        if self.phase is not None:
            if (any(actual[key] != original[key] for key in actual if key not in ("glow", "fill")) or
                    any(abs(actual[key]-original[key]) > 0.00001 for key in ("glow", "fill"))):
                self.debug["reason"] = "respawn-visual-mismatch"
                return None
            require(candidate._uep_respawn_duration_messages == self.owner_before+1, "respawn duration not exact-once")
            foreign_delivery_evidence(self.foreign_before, candidate._uep_respawn_foreign, self.foreign_pair_rejections)
            self.comparisons += 1
            if actual["visibility"] == 0 and actual["respawning"] and actual["timer_active"]:
                self.visible_comparisons += 1
            self.completed = actual["visibility"] == 1 and not actual["timer_active"] and not actual["respawning"] and self.visible_comparisons > 0
        return {"production_widget": True, "widget": candidate.get_path_name(), "class": candidate.get_class().get_name(),
                "profile": str(ue.get_mixin_profile(candidate)), "controller": controller.get_path_name(),
                "pawn": candidate.call_function("GetOwningPlayerPawn").get_path_name(), "world_token": self.world_token,
                "phase": self.phase, "completed": self.completed, "synthetic_local_messages": True,
                "native_respawn_producer_tested": False, "replicated_message_tested": False, "fixture_event_invoked": False,
                "owner_deliveries": candidate._uep_respawn_duration_messages-self.owner_before if self.phase else 0,
                **(foreign_delivery_evidence(self.foreign_before, candidate._uep_respawn_foreign, self.foreign_pair_rejections) if self.phase else
                   {"foreign_rejections": 0, "total_foreign_rejections": 0, "additional_foreign_rejections": 0}),
                "comparisons": self.comparisons, "visible_comparisons": self.visible_comparisons,
                "foreign_instigator_kind": "owning-pawn-not-playerstate",
                "phase_elapsed": respawn.game_time(candidate)-actual["start"] if self.phase else 0.0,
                "python": actual, "blueprint": original}

    def begin(self, phase):
        require(valid(self.candidate) and valid(self.helper), "respawn probe not armed")
        self.phase, self.completed = phase, False
        self.comparisons = self.visible_comparisons = 0
        self.owner_before, self.foreign_before = self.candidate._uep_respawn_duration_messages, self.candidate._uep_respawn_foreign
        channel = GameplayTag(TagName=respawn.DURATION_CHANNEL)
        self.helper.call_function("BroadcastDuration", self.router, channel,
            LyraInteractionDurationMessage(Instigator=self.controller.PlayerState, Duration=3.0))
        retained = visual(self.candidate)
        pawn = self.controller.get_controlled_pawn()
        self.helper.call_function("BroadcastDuration", self.router, channel, LyraInteractionDurationMessage(Instigator=pawn, Duration=77.0))
        self.helper.call_function("BroadcastVerb", self.router, GameplayTag(TagName=respawn.COMPLETED_CHANNEL), LyraVerbMessage(Instigator=pawn))
        # No native frame/timer can interleave this synchronous pair. Later
        # legitimate native foreign messages are counted separately, not used
        # as proof that either injected message was actually filtered.
        self.foreign_pair_rejections = self.candidate._uep_respawn_foreign-self.foreign_before
        foreign_delivery_evidence(self.foreign_before, self.candidate._uep_respawn_foreign, self.foreign_pair_rejections)
        require(self.candidate._uep_respawn_duration_messages == self.owner_before+1, "respawn synchronous owner delivery not exact-once")
        require(visual(self.candidate) == retained, "foreign respawn payload changed UI")
