"""Read-only production quickbar/native inventory comparisons in network play."""
import unreal_engine as ue
from uep_lyra_hud import quickbar_slot_mixin as slots
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_protocol import require


def path(value):
    return value.get_path_name() if valid(value) else None


def visual(widget):
    return {"index": int(widget.SlotIndex), "empty": bool(widget.IsEmpty), "selected": bool(widget.IsSelected),
            "numeric": float(widget.WeaponAmmoCount.call_function("GetTargetValue")),
            "text": str(widget.WeaponAmmoCount.call_function("GetText")),
            "icon": path(widget.WeaponCard.call_function("GetDynamicMaterial").call_function("K2_GetTextureParameterValue", "IconTexture")),
            "ammo_icon": path(widget.AmmoIcon.call_function("GetDynamicMaterial").call_function("K2_GetTextureParameterValue", "TextureMask"))}


class QuickBarSlotsProbe:
    def __init__(self):
        self.world_token = None
        self.pairs = []
        self.reused_baseline_epochs = 0
        self.debug = {"reason": "not-created"}

    def close(self):
        for candidate, baseline in self.pairs:
            if valid(baseline):
                baseline.RemoveFromParent()
                baseline.remove_from_root()
        self.pairs, self.world_token = [], None

    def reconcile(self, controller, owned, world_token):
        same_widgets = [pair[0] for pair in self.pairs] == owned and all(valid(pair[1]) for pair in self.pairs)
        if not same_widgets:
            self.close()
            for candidate in owned:
                baseline = controller.create_widget(candidate.get_class())
                baseline.SlotIndex, baseline.SlotInputAction = candidate.SlotIndex, candidate.SlotInputAction
                baseline.add_to_root()
                ue.set_mixin_profile(baseline, "BlueprintFallback")
                baseline.AddToViewport(450)
                baseline.call_function("SetRenderOpacity", 0.0)
                baseline.call_function(slots.RESUME)
                self.pairs.append((candidate, baseline))
        elif self.world_token != world_token:
            # Native production quickbar children survive this travel. Keep
            # their original BP counterparts too, including authored stale
            # numeric/icon state on now-empty slots. Never copy Python UI
            # values into the baseline or replay its OnInitialized.
            for candidate, baseline in self.pairs:
                baseline.call_function("SetOwningPlayer", controller)
                if not baseline.call_function("IsInViewport"):
                    baseline.AddToViewport(450)  # Real native remount if detached.
                baseline.call_function(slots.RESUME)
            self.reused_baseline_epochs += 1
        self.world_token = world_token

    def observe(self, controller, player):
        slots.pools.refresh()
        owned = [ue.find_object(name) for name in slots.snapshot()["active_widgets"]]
        owned = [widget for widget in owned if valid(widget) and widget.call_function("GetOwningPlayer") == controller]
        require(len(owned) <= 3, "duplicate production quickbar owner")
        if len(owned) != 3:
            self.debug = {"reason": "production-slots-unavailable", "count": len(owned)}
            return None
        owned.sort(key=lambda widget: int(widget.SlotIndex))
        require([int(widget.SlotIndex) for widget in owned] == [0, 1, 2], "production slot indices differ")
        self.reconcile(controller, owned, player["world_token"])
        component = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
        require(valid(component), "native quickbar missing")
        native_slots, active = list(component.call_function("GetSlots")), int(component.call_function("GetActiveSlotIndex"))
        rows = []
        for index, (candidate, baseline) in enumerate(self.pairs):
            actual, original = visual(candidate), visual(baseline)
            if actual != original:
                self.debug = {"reason": "quickbar-visual-mismatch", "index": index, "python": actual, "blueprint": original,
                              "production_widget": candidate.get_path_name(), "baseline_widget": baseline.get_path_name(),
                              "reused_baseline_epochs": self.reused_baseline_epochs}
                return None
            item = native_slots[index] if index < len(native_slots) else None
            total = None
            if valid(item):
                from unreal_engine.structs import GameplayTag
                total = sum(int(item.call_function("GetStatTagStackCount", GameplayTag(TagName=tag))) for tag in
                            ("Lyra.ShooterGame.Weapon.MagazineAmmo", "Lyra.ShooterGame.Weapon.SpareAmmo"))
                if not actual["empty"] and (actual["numeric"] != total or actual["selected"] != (index == active)):
                    self.debug = {"reason": "native-quickbar-not-converged", "index": index, "python": actual, "native_total": total, "active": active}
                    return None
            elif not actual["empty"]:
                self.debug = {"reason": "native-empty-slot-not-converged", "index": index, "python": actual}
                return None
            rows.append({"production_widget": True, "widget": candidate.get_path_name(), "class": candidate.get_class().get_name(),
                         "baseline_widget": baseline.get_path_name(),
                         "profile": str(ue.get_mixin_profile(candidate)), "python": actual, "blueprint": original,
                         "native_item": path(item), "native_total": total, "native_active": index == active,
                         "slot_messages": candidate._uep_slot_messages, "active_messages": candidate._uep_slot_active_messages,
                         "named_query_calls": candidate._uep_slot_named_queries,
                         "automatic_ticks": candidate._uep_slot_ticks})
        self.debug = {"reason": "ready", "world_token": self.world_token, "reused_baseline_epochs": self.reused_baseline_epochs,
                      "production_widgets": [candidate.get_path_name() for candidate, baseline in self.pairs]}
        return {"controller": controller.get_path_name(), "pawn": player["pawn_path"], "world_token": self.world_token,
                "slots": rows, "synthetic_local_messages": False, "native_inventory_properties_written": False,
                "external_named_query_migrated": True, "bp_initialization_parity_tested": False,
                "baseline_epoch_policy": "same-production-widget -> same BP baseline; native owner/remount/resume; no state copying",
                "reused_baseline_epochs": self.reused_baseline_epochs}
