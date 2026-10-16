"""Event-driven Python presenter for Lyra's unchanged W_Healthbar type."""

import math
import traceback

import unreal_engine as ue

from . import state


PYTHON_PROFILE = "Python"
BLUEPRINT_FALLBACK_PROFILE = "BlueprintFallback"
OWNED_ANIMATIONS = ("OnDamaged", "OnHealed", "OnEliminated", "OnSpawned")


def normalized_health(health, maximum):
    if not math.isfinite(health) or not math.isfinite(maximum):
        raise ValueError("health presentation requires finite values")
    return max(0.0, min(1.0, health / maximum)) if maximum > 0.0 else 0.0


def _stop_owned_animations(instance, *, flush=False):
    # StopAnimation can synchronously finish an animation. Disarm first so
    # cancelling an old Pawn's damage animation cannot eliminate its successor.
    instance._uep_hud_pending_elimination = False
    for name in OWNED_ANIMATIONS:
        animation = getattr(instance, name, None)
        if _is_valid(animation):
            instance.call_function("StopAnimation", animation)
    if flush:
        # UE 5.8 queues Stop's return-to-start evaluation. OnSpawned's
        # frame-zero material keys set Health_Updated=1; drain that old work
        # BEFORE writing the new health, not after its material parameters.
        # Cleanup/router teardown does not request a flush during destruction.
        instance.call_function("FlushAnimations")


def _cancel_visuals(instance, *, router_teardown=False):
    instance._uep_hud_visual_active = False
    instance._uep_hud_pending_elimination = False
    if _is_valid(instance):
        if router_teardown:
            # StopAnimation can synchronously enter the reflected completion
            # event while the router is deliberately unavailable. Pause has
            # no finish notification; native UMG retains/cleans its own state.
            # There are no Python animation delegates to detach or defer.
            for name in OWNED_ANIMATIONS:
                animation = getattr(instance, name, None)
                if _is_valid(animation):
                    instance.call_function("PauseAnimation", animation)
        else:
            _stop_owned_animations(instance)


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
    try:
        _cancel_visuals(instance, router_teardown=reason == "mixin_teardown")
    except Exception:
        _record_failure(instance, "cancel_visuals")
    _unbind_health(instance)
    _unbind_controller(instance)
    ue.log("UEP_LYRA_HUD_BINDINGS_CLEARED " + reason)


def _teardown_instance(instance):
    _cleanup_instance_bindings(instance, "mixin_teardown")
    state.record_teardown(instance)


class LyraHealthbarPythonProfile:
    """Own widget lifecycle, subscriptions, and the authored visual helpers."""

    def __init__(self):
        self._uep_hud_controller = None
        self._uep_hud_pawn = None
        self._uep_hud_health = None
        self._uep_hud_controller_bound = False
        self._uep_hud_health_bound = False
        self._uep_hud_visual_active = False
        self._uep_hud_pending_elimination = False
        self._uep_hud_presented_health = None
        # unbind_event requires the exact callable object used by bind_event.
        # Keep the original public BP ingress callable by other BPs as well
        # as delegates; production delivery exercises the reflected router.
        self._uep_hud_pawn_callback = lambda old, new: self.call_function("OnPosessedPawnChanged", old, new)
        self._uep_hud_health_callback = lambda component, old, new, instigator: self.call_function(
            "Health Changed", component, old, new, instigator)
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
        _cancel_visuals(self)
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

    def _set_health_materials(self, old_normalized, new_normalized):
        for name in ("BarBorderMID", "BarFillMID", "BarGlowMID"):
            material = getattr(self, name, None)
            if not _is_valid(material):
                raise RuntimeError("healthbar material is unavailable: " + name)
            material.call_function("SetScalarParameterValue", "Health_Current", old_normalized)
            material.call_function("SetScalarParameterValue", "Health_Updated", new_normalized)

    def _play_health_animation(self, name):
        animation = getattr(self, name, None)
        if not _is_valid(animation):
            raise RuntimeError("healthbar animation is unavailable: " + name)
        self.call_function("PlayAnimationForward", animation, 1.0, False)
        state.record_animation(self, name)

    def SetDynamicMaterials(self):
        for name in ("BarBorder", "BarFill", "BarGlow"):
            image = getattr(self, name, None)
            if not _is_valid(image):
                raise RuntimeError("healthbar image is unavailable: " + name)
            material = image.call_function("GetDynamicMaterial")
            if not _is_valid(material):
                raise RuntimeError("healthbar dynamic material is unavailable: " + name)
            setattr(self, name + "MID", material)

    def ResetAnimatedState(self):
        for name in ("BarBorderMID", "BarFillMID", "BarGlowMID"):
            material = getattr(self, name)
            material.call_function("SetScalarParameterValue", "Animate_Damage", 0.0)
            material.call_function("SetScalarParameterValue", "Animate_DamageFade", 0.0)
            if name != "BarFillMID":
                material.call_function("SetScalarParameterValue", "Animate_Glow_AlphaChange", 0.0)
                material.call_function("SetScalarParameterValue", "Animate_Glow_ColorChange", 0.0)

    def InitializeBarVisuals(self):
        self._set_health_materials(1.0, 1.0)
        self.ResetAnimatedState()
        self.HealthNumber.call_function(
            "InterpolateToValue", float(self.NormalizedHealth) * 100.0, 1.0, 4.0, 0.0
        )

    def _render_health(self, event, health, max_health, old_value):
        number = getattr(self, "HealthNumber", None)
        if not _is_valid(number):
            raise RuntimeError("healthbar number is unavailable")

        if not self._uep_hud_visual_active or (
            health > 0.0 and ((self._uep_hud_presented_health is not None
                               and self._uep_hud_presented_health <= 0.0)
                              or (event == "health_changed" and old_value <= 0.0))
        ):
            # The component can be present before ASC initialization: getters
            # read 0/0, then its first replicated event reports old=100,new=100.
            # Detect recovery from the value actually presented, not only the
            # native attribute delta, or OnEliminated remains visible at Health=100.
            _stop_owned_animations(self, flush=True)
            self._uep_hud_visual_active = True
            # Initialize only for the initial/new Pawn, never on ordinary damage.
            self.InitializeBarVisuals()
            self._set_health_materials(self.NormalizedHealth, self.NormalizedHealth)
            number.call_function("SetCurrentValue", health)
            self._play_health_animation("OnSpawned" if health > 0.0 else "OnEliminated")
            return "spawn" if health > 0.0 else "eliminated"

        if event == "max_health_changed":
            # A denominator change is neither healing nor damage; retain any
            # pending death and numeric interpolation, updating only the ratio.
            self._set_health_materials(self.NormalizedHealth, self.NormalizedHealth)
            return "rescale"

        if old_value == health:
            return "unchanged"

        _stop_owned_animations(self, flush=True)
        self.ResetAnimatedState()
        self._set_health_materials(normalized_health(old_value, max_health), self.NormalizedHealth)
        # Match the authored duration/rate, but let CommonUI interpolate from
        # its currently displayed value. A second hit must not snap the number.
        number.call_function("InterpolateToValue", health, 1.0, 4.0, 0.0)
        self._uep_hud_pending_elimination = health <= 0.0
        self._play_health_animation("OnDamaged" if health < old_value else "OnHealed")
        return "damage" if health < old_value else "heal"

    def _update_visuals(self, event, old_value=None, new_value=None):
        health_component = self._uep_hud_health
        if not _is_valid(health_component):
            return
        health = float(health_component.call_function("GetHealth"))
        max_health = float(health_component.call_function("GetMaxHealth"))
        self.NormalizedHealth = normalized_health(health, max_health)
        self.HealthOldValue = health if old_value is None else float(old_value)
        self.HealthNewValue = health if new_value is None else float(new_value)

        transition = self._render_health(event, health, max_health, self.HealthOldValue)
        self._uep_hud_presented_health = health

        state.record_visual_update(
            self,
            event,
            health,
            max_health,
            self.NormalizedHealth,
            old_value,
            new_value,
            transition,
        )
        ue.log(
            "UEP_LYRA_HUD_HEALTH {0:.3f}/{1:.3f} {2}".format(health, max_health, event)
        )

    def OnAnimationFinished(self, Animation):
        # This reflected BlueprintNativeEvent already exists in UUserWidget.
        # No extra animation delegate (or C++ adapter) needs lifetime ownership.
        self.call_mixin_original("OnAnimationFinished", Animation)
        try:
            if (
                not self._uep_hud_visual_active
                or not self._uep_hud_pending_elimination
                or Animation != self.OnDamaged
                or self.call_function("IsAnimationPlaying", Animation)
            ):
                return
            health = self._uep_hud_health
            if not _is_valid(health) or float(health.call_function("GetHealth")) > 0.0:
                return
            self._uep_hud_pending_elimination = False
            self.call_function("EventOnEliminated")
        except Exception:
            self._record_failure("animation_finished")

    def _on_possessed_pawn_changed(self, old_pawn, new_pawn):
        try:
            self._bind_pawn(new_pawn, "pawn_changed")
        except Exception:
            self._record_failure("pawn_changed")

    def OnPosessedPawnChanged(self, OldPawn, NewPawn):
        state.record_public_entry(self, "OnPosessedPawnChanged")
        self._on_possessed_pawn_changed(OldPawn, NewPawn)

    def HealthChanged(self, HealthComponent, OldValue, NewValue, Instigator):
        state.record_public_entry(self, "Health Changed")
        self._on_health_changed(HealthComponent, OldValue, NewValue, Instigator)

    HealthChanged.override = "Health Changed"

    def EventOnEliminated(self):
        state.record_public_entry(self, "EventOnEliminated")
        self._play_health_animation("OnEliminated")

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
            self.SetDynamicMaterials()
            self._bind_controller()
            ue.log("UEP_LYRA_PYTHON_HEALTHBAR_CONSTRUCTED")
        except Exception:
            self._record_failure("construct")

    def Destruct(self):
        self._cleanup_bindings("destruct")
        state.record_destruct(self)
        ue.log("UEP_LYRA_PYTHON_HEALTHBAR_DESTRUCTED")


class LyraHealthbarBlueprintFallbackProfile:
    """Per-instance escape hatch retaining the complete original BP behavior."""

    def Construct(self):
        self.call_mixin_original("Construct")
