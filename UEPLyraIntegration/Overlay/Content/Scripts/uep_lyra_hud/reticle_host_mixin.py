"""Retained weapon-reticle host business; native equipment/UMG stay native.

The LyraWeaponUserInterface native Tick still detects the equipped instance
and invokes OnWeaponChanged. Python creates the configured reticles and owns
only its death-observation lifetime; inventory/equipment are never rewritten.
"""

import copy
import unreal_engine as ue

from uep_runtime import SubscriptionScope
from .weapon_observer import valid


HOST_CLASS = "/ShooterCore/UserInterface/HUD/W_WeaponReticleHost.W_WeaponReticleHost_C"
CLEANUP_HELPER = "UEPRemoveOriginalDeathBinding"
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "weapon_changes": 0,
          "reticles_created": 0, "clear_calls": 0, "ticks": 0, "death_callbacks": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()))


def close_scope(widget):
    scope = widget._uep_reticle_host_scope
    widget._uep_reticle_host_scope = None
    _active.pop(id(widget), None)
    if scope is not None:
        try:
            scope.close()
            _stats["scopes_closed"] += 1
        except Exception as error:
            _stats["errors"].append(str(error))
            raise


def remove_original_binding(widget):
    if valid(widget.CurrentHealthComponent):
        # Thin compiled-VM cleanup removes only (this widget, OnDeathStarted).
        # Calling the original death business during teardown would reenter
        # UpdateVisibility's router while the profile is intentionally busy.
        widget.call_function(CLEANUP_HELPER, widget.CurrentHealthComponent)


class LyraReticleHostPythonProfile:
    def __init__(self):
        self._uep_reticle_host_scope = None
        self._uep_reticle_host_bound_health = None
        self._uep_reticle_host_ticks = 0
        self._uep_reticle_host_changes = 0

    def ClearExistingWidgets(self):
        for widget in list(self.SpawnedWidgets):
            self.WidgetStack.call_function("RemoveChild", widget)
        self.SpawnedWidgets = []
        _stats["clear_calls"] += 1

    def OnWeaponChanged(self, OldWeapon, NewWeapon):
        self.call_function("ClearExistingWidgets")
        self._uep_reticle_host_changes += 1
        _stats["weapon_changes"] += 1
        if not valid(NewWeapon):
            return
        item = NewWeapon.call_function("GetInstigator")
        if not valid(item) or not item.is_a(ue.find_class("LyraInventoryItemInstance")):
            return
        fragment = item.call_function("FindFragmentByClass", ue.find_class("InventoryFragment_ReticleConfig"))
        if not valid(fragment):
            return
        controller = self.call_function("GetOwningPlayer")
        for cls in fragment.ReticleWidgets:
            widget = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("Create", self, cls, controller)
            widget.call_function("InitializeFromWeapon", NewWeapon)
            # Reflected arrays are owning copies; assign back instead of
            # appending to a temporary Python list and losing the native change.
            self.SpawnedWidgets = list(self.SpawnedWidgets) + [widget]
            slot = self.WidgetStack.call_function("AddChildToOverlay", widget)
            slot.call_function("SetHorizontalAlignment", 0)  # HAlign_Fill
            slot.call_function("SetVerticalAlignment", 0)  # VAlign_Fill
            _stats["reticles_created"] += 1

    def OnCheckForDeath(self):
        controller = self.call_function("GetOwningPlayer")
        pawn = controller.call_function("K2_GetPawn") if valid(controller) else None
        if not valid(pawn):
            # The authored invalid-Pawn branch sets NewHealthComponent only;
            # it does not reset CurrentHealthComponent or call UpdateVisibility.
            self.NewHealthComponent = None
            return
        health = pawn.call_function("GetComponentByClass", ue.find_class("LyraHealthComponent"))
        self.NewHealthComponent = health
        if health != self.CurrentHealthComponent or (valid(health) and health != self._uep_reticle_host_bound_health):
            close_scope(self)
            self.CurrentHealthComponent = health
            if valid(health):
                scope = SubscriptionScope()
                self._uep_reticle_host_scope = scope
                try:
                    scope.bind_event(health, "OnDeathStarted", lambda actor: self.call_function("OnDeathStarted", actor))
                except Exception:
                    scope.close()
                    self._uep_reticle_host_scope = None
                    raise
                _active[id(self)] = self.get_path_name()
                _stats["scopes_created"] += 1
                self._uep_reticle_host_bound_health = health
                self.call_function("UpdateVisibility")

    def UpdateVisibility(self):
        health = self.CurrentHealthComponent
        visible = valid(health) and not health.call_function("IsDeadOrDying")
        self.VisWrapper.call_function("SetVisibility", 0 if visible else 1)  # Visible / Collapsed

    def OnDeathStarted(self, OwningActor):
        self.call_function("UpdateVisibility")
        close_scope(self)
        _stats["death_callbacks"] += 1

    def Tick(self, MyGeometry, InDeltaTime):
        self.call_function("OnCheckForDeath")
        self._uep_reticle_host_ticks += 1
        _stats["ticks"] += 1

    def Destruct(self):
        close_scope(self)

    def __uep_mixin_teardown__(self):
        # Keep native widgets/CurrentInstance during a live profile switch:
        # native Tick will not emit another OnWeaponChanged for the same weapon.
        close_scope(self)


class LyraReticleHostBlueprintFallbackProfile:
    def __init__(self):
        # A fresh fallback must reattach its own BP delegate on the next Tick,
        # even if the Python profile already stored this Pawn's health pointer.
        self.CurrentHealthComponent = None

    def ClearExistingWidgets(self):
        self.call_mixin_original("ClearExistingWidgets")

    def OnWeaponChanged(self, OldWeapon, NewWeapon):
        self.call_mixin_original("OnWeaponChanged", OldWeapon, NewWeapon)

    def OnCheckForDeath(self):
        self.call_mixin_original("OnCheckForDeath")

    def UpdateVisibility(self):
        self.call_mixin_original("UpdateVisibility")

    def OnDeathStarted(self, OwningActor):
        self.call_mixin_original("OnDeathStarted", OwningActor)

    def Tick(self, MyGeometry, InDeltaTime):
        self.call_mixin_original("Tick", MyGeometry, InDeltaTime)

    def Destruct(self):
        remove_original_binding(self)

    def __uep_mixin_teardown__(self):
        remove_original_binding(self)
