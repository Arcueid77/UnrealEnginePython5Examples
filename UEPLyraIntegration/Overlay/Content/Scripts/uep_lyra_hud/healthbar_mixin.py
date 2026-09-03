"""Event-driven Python presenter for Lyra's unchanged W_Healthbar type."""

import traceback

import unreal_engine as ue

from . import state


PYTHON_PROFILE = "Python"
BLUEPRINT_FALLBACK_PROFILE = "BlueprintFallback"


def _is_valid(value):
    try:
        return value is not None and value.is_valid()
    except Exception:
        return False


def _record_failure(instance, operation):
    detail = traceback.format_exc()
    state.record_error(instance, operation, detail)
    ue.log_error(detail)


def _unbind_health(instance):
    health = instance._uep_hud_health
    was_bound = instance._uep_hud_health_bound
    instance._uep_hud_health_bound = False
    instance._uep_hud_health = None
    instance._uep_hud_pawn = None
    if was_bound and _is_valid(health):
        try:
            health.unbind_event(
                "OnHealthChanged",
                instance._uep_hud_health_callback,
            )
            health.unbind_event(
                "OnMaxHealthChanged",
                instance._uep_hud_max_health_callback,
            )
        except Exception:
            _record_failure(instance, "unbind_health")
    if was_bound:
        state.record_health_unbind(instance)


def _unbind_controller(instance):
    controller = instance._uep_hud_controller
    was_bound = instance._uep_hud_controller_bound
    instance._uep_hud_controller_bound = False
    instance._uep_hud_controller = None
    if was_bound and _is_valid(controller):
        try:
            controller.unbind_event(
                "OnPossessedPawnChanged",
                instance._uep_hud_pawn_callback,
            )
        except Exception:
            _record_failure(instance, "unbind_controller")
    if was_bound:
        state.record_controller_unbind(instance)


def _cleanup_instance_bindings(instance, reason):
    # Teardown callbacks deliberately cannot resolve profile methods through
    # self. Keep the entire cleanup chain at module scope.
    _unbind_health(instance)
    _unbind_controller(instance)
    ue.log("UEP_LYRA_HUD_BINDINGS_CLEARED " + reason)


def _teardown_instance(instance):
    _cleanup_instance_bindings(instance, "mixin_teardown")
    state.record_teardown(instance)


class LyraHealthbarPythonProfile:
    """Own widget lifecycle and health subscriptions; retain BP visual helpers."""

    def __init__(self):
        self._uep_hud_controller = None
        self._uep_hud_pawn = None
        self._uep_hud_health = None
        self._uep_hud_controller_bound = False
        self._uep_hud_health_bound = False
        # unbind_event requires the exact callable object used by bind_event.
        self._uep_hud_pawn_callback = self._on_possessed_pawn_changed
        self._uep_hud_health_callback = self._on_health_changed
        self._uep_hud_max_health_callback = self._on_max_health_changed
        state.record_initialized(self)

    def __uep_mixin_teardown__(self):
        _teardown_instance(self)

    def _record_failure(self, operation):
        _record_failure(self, operation)

    def _unbind_health(self):
        _unbind_health(self)

    def _unbind_controller(self):
        _unbind_controller(self)

    def _cleanup_bindings(self, reason):
        _cleanup_instance_bindings(self, reason)

    def _health_component_for(self, pawn):
        if not _is_valid(pawn):
            return None
        health_class = ue.find_class("LyraHealthComponent")
        if health_class is None:
            raise RuntimeError("LyraHealthComponent reflection is unavailable")
        return pawn.get_component_by_type(health_class)

    def _bind_pawn(self, pawn, event):
        self._unbind_health()
        self._uep_hud_pawn = pawn if _is_valid(pawn) else None
        if not _is_valid(pawn):
            return
        health = self._health_component_for(pawn)
        if not _is_valid(health):
            return
        health.bind_event("OnHealthChanged", self._uep_hud_health_callback)
        health.bind_event("OnMaxHealthChanged", self._uep_hud_max_health_callback)
        self._uep_hud_health = health
        self._uep_hud_health_bound = True
        state.record_health_bind(self, pawn, health)
        self._update_visuals(event)

    def _bind_controller(self):
        controller = self.call_function("GetOwningPlayer")
        if not _is_valid(controller):
            return
        controller.bind_event(
            "OnPossessedPawnChanged",
            self._uep_hud_pawn_callback,
        )
        self._uep_hud_controller = controller
        self._uep_hud_controller_bound = True
        state.record_controller_bind(self, controller)
        self._bind_pawn(controller.get_controlled_pawn(), "pawn_bound")

    def _update_visuals(self, event, old_value=None, new_value=None):
        health_component = self._uep_hud_health
        if not _is_valid(health_component):
            return
        health = float(health_component.call_function("GetHealth"))
        max_health = float(health_component.call_function("GetMaxHealth"))
        normalized = health / max_health if max_health > 0.0 else 0.0

        self.NormalizedHealth = max(0.0, min(1.0, normalized))
        self.HealthOldValue = health if old_value is None else float(old_value)
        self.HealthNewValue = health if new_value is None else float(new_value)

        # These Blueprint functions are visual primitives only. Python owns
        # subscription, state, normalization and when a render update occurs.
        self.call_function("InitializeBarVisuals")
        number = getattr(self, "HealthNumber", None)
        if _is_valid(number):
            number.call_function("SetCurrentValue", health)

        state.record_visual_update(
            self,
            event,
            health,
            max_health,
            self.NormalizedHealth,
            old_value,
            new_value,
        )
        ue.log(
            "UEP_LYRA_HUD_HEALTH {0:.3f}/{1:.3f} {2}".format(
                health,
                max_health,
                event,
            )
        )

    def _on_possessed_pawn_changed(self, old_pawn, new_pawn):
        try:
            self._bind_pawn(new_pawn, "pawn_changed")
        except Exception:
            self._record_failure("pawn_changed")

    def _on_health_changed(
        self,
        health_component,
        old_value,
        new_value,
        instigator,
    ):
        try:
            if health_component != self._uep_hud_health:
                return
            self._update_visuals("health_changed", old_value, new_value)
        except Exception:
            self._record_failure("health_changed")

    def _on_max_health_changed(
        self,
        health_component,
        old_value,
        new_value,
        instigator,
    ):
        try:
            if health_component != self._uep_hud_health:
                return
            # HealthOldValue/HealthNewValue drive the Blueprint's health
            # visuals, so a max-health-only notification must not write max
            # values into those health slots. Re-read both values and render a
            # stable current-health frame with the new normalization instead.
            self._update_visuals("max_health_changed")
        except Exception:
            self._record_failure("max_health_changed")

    def Construct(self):
        try:
            state.record_construct(self)
            self._cleanup_bindings("reconstruct")
            self.call_function("SetDynamicMaterials")
            self._bind_controller()
            ue.log("UEP_LYRA_PYTHON_HEALTHBAR_CONSTRUCTED")
        except Exception:
            self._record_failure("construct")

    def Destruct(self):
        self._cleanup_bindings("destruct")
        state.record_destruct(self)
        self.call_mixin_original("Destruct")
        ue.log("UEP_LYRA_PYTHON_HEALTHBAR_DESTRUCTED")


class LyraHealthbarBlueprintFallbackProfile:
    """Per-instance escape hatch retaining the complete original BP behavior."""

    def Construct(self):
        self.call_mixin_original("Construct")
