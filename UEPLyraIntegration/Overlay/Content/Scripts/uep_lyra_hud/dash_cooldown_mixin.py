"""Dash UI business on the retained widget, using native duration/health/UMG."""

import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from .weapon_observer import valid
from .ability_progress_mixin import game_time
from . import pooled_widget_lifetime as pools

CLASS = "/ShooterCore/Game/Dash/W_DashCooldown.W_DashCooldown_C"
CHANNEL = "Ability.Dash.Duration.Message"
RESUME = "UEPResumeDashObservation"
PROXY = "UEPOriginalDashProxy"
CLEANUP = "UEPRemoveOriginalDashDeathBinding"
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "messages": 0,
          "foreign_messages": 0, "ticks": 0, "death_callbacks": 0,
          "health_binds": 0, "health_unbinds": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()), pool_lifetime=pools.snapshot())


def close_scope(scope, health=False):
    if scope is not None:
        try:
            scope.close()
            _stats["scopes_closed"] += 1
            if health:
                _stats["health_unbinds"] += 1
        except Exception as error:
            _stats["errors"].append(str(error))
            raise


def start(widget):
    if widget._uep_dash_scope is not None:
        return
    pools.refresh()
    if not pools.may_activate(widget):
        return
    helper = ue.new_object(widget.PythonMessageAdapterClass)
    helper.add_to_root()
    scope = SubscriptionScope()
    widget._uep_dash_scope, widget._uep_dash_reader = scope, helper
    try:
        scope.listen_gameplay_message(widget, CHANNEL, ue.find_struct("LyraInteractionDurationMessage"),
                                      lambda proxy: read(widget, proxy),
                                      lambda channel, payload: received(widget, payload))
    except Exception:
        scope.close()
        helper.remove_from_root()
        widget._uep_dash_scope = widget._uep_dash_reader = None
        raise
    _active[id(widget)] = widget.get_path_name()
    _stats["scopes_created"] += 1
    try:
        pools.watch(widget, close)
    except Exception:
        close(widget)
        raise


def read(widget, proxy):
    payload, success = widget._uep_dash_reader.call_function("ReadDuration", proxy)
    if success is not True:
        raise RuntimeError("Dash typed duration extraction failed")
    return payload


def received(widget, payload):
    if payload.Instigator != widget.call_function("GetOwningPlayerPawn"):
        widget._uep_dash_foreign += 1
        _stats["foreign_messages"] += 1
        return
    widget.Duration = float(payload.Duration)
    widget.StartTime = game_time(widget)
    if widget.call_function("IsAnimationPlaying", widget.InactiveToActive):
        widget.call_function("StopAnimation", widget.InactiveToActive)
    widget.call_function("UpdateCooldownPercent", 0.0)
    widget.call_function("PlayAnimationForward", widget.ActiveToInactive, 1.0, False)
    widget.Charging = True
    widget._uep_dash_messages += 1
    _stats["messages"] += 1


def close(widget):
    pools.unwatch(widget)
    scope, helper = widget._uep_dash_scope, widget._uep_dash_reader
    health_scopes = list(widget._uep_dash_health.values())
    widget._uep_dash_scope = widget._uep_dash_reader = None
    widget._uep_dash_health = {}
    widget._uep_dash_seen_health.clear()
    _active.pop(id(widget), None)
    errors = []
    for owned, is_health in [(scope, False)] + [(item[1], True) for item in health_scopes]:
        try:
            close_scope(owned, is_health)
        except Exception as error:
            errors.append(error)
    if valid(helper):
        helper.remove_from_root()
    # These retained animations have no Python completion subscription or
    # latent continuation. They belong to native UMG and must keep playing
    # through a live Profile switch; pausing them changes the original UI.
    if errors:
        raise RuntimeError("Dash cleanup failed") from errors[0]


def close_original(widget):
    proxy = getattr(widget, PROXY)
    setattr(widget, PROXY, None)
    if valid(proxy):
        proxy.call_function("Cancel")
    healths = list(widget._uep_dash_original_health.values()) + [widget.CurrentHealthComponent]
    widget._uep_dash_original_health = {}
    for health in healths:
        if valid(health):
            widget.call_function(CLEANUP, health)


class LyraDashCooldownPythonProfile:
    def __init__(self):
        self._uep_pool_owner = getattr(self, "_uep_pool_owner", None)
        self._uep_dash_scope = self._uep_dash_reader = None
        self._uep_dash_health, self._uep_dash_seen_health = {}, set()
        self._uep_dash_ticks = self._uep_dash_messages = self._uep_dash_foreign = 0
        self._uep_dash_deaths = 0

    def OnInitialized(self):
        self.call_function("ListenForDuration")

    def ListenForDuration(self):
        start(self)

    def ResumeObservation(self):
        start(self)  # Explicit hidden activation, never lifecycle/model replay.

    ResumeObservation.override = RESUME

    def Construct(self):
        start(self)
        self.call_function("UpdateCooldownPercent", 1.0)
        self.call_function("PlayAnimationForward", self.InactiveToActive, 1.0, False)

    def UpdateCooldownPercent(self, Percent: float):
        for image in (self.BarGlow, self.BarFill):
            image.call_function("GetDynamicMaterial").call_function(
                "SetScalarParameterValue", "AnimateArcFill", Percent)

    def UpdateVisibility(self):
        health = self.CurrentHealthComponent
        visible = valid(health) and not health.call_function("IsDeadOrDying")
        self.CenteringOvr.call_function("SetVisibility", 3 if visible else 1)

    def OnCheckForDeath(self):
        controller = self.call_function("GetOwningPlayer")
        pawn = controller.call_function("K2_GetPawn") if valid(controller) else None
        if not valid(pawn):
            # The original invalid-Pawn branch stops after setting NewHealth.
            self.NewHealthComponent = None
            return
        health = pawn.call_function("GetComponentByClass", ue.find_class("LyraHealthComponent"))
        self.NewHealthComponent = health
        key = health.get_path_name() if valid(health) else None
        changed = health != self.CurrentHealthComponent
        fresh_profile = key is not None and key not in self._uep_dash_seen_health
        if not (changed or fresh_profile):
            return
        self.CurrentHealthComponent = health
        if not valid(health):
            return  # Authored invalid-health branch does not update visibility.
        if key not in self._uep_dash_health:
            scope = SubscriptionScope()
            scope.bind_event(health, "OnDeathStarted", lambda actor: self.call_function("OnDeathStarted", actor))
            self._uep_dash_health[key] = (health, scope)
            self._uep_dash_seen_health.add(key)
            _stats["scopes_created"] += 1
            _stats["health_binds"] += 1
        # The original retains old-health bindings until its death callback.
        # Do not silently rewrite that branch order when replacing its business.
        self.call_function("UpdateVisibility")

    def OnDeathStarted(self, OwningActor):
        self.call_function("UpdateVisibility")
        health = self.CurrentHealthComponent
        key = health.get_path_name() if valid(health) else None
        binding = self._uep_dash_health.pop(key, None)
        if binding is not None:
            close_scope(binding[1], True)
        self._uep_dash_deaths += 1
        _stats["death_callbacks"] += 1

    def Tick(self, MyGeometry, InDeltaTime):
        start(self)
        if self._uep_dash_scope is None:
            return  # An inactive native pool entry must not rebind health.
        self.call_function("OnCheckForDeath")
        if self.Charging:
            elapsed = game_time(self) - float(self.StartTime)
            percent = ue.find_class("KismetMathLibrary").get_cdo().call_function(
                "Divide_DoubleDouble", elapsed, float(self.Duration))
            self.call_function("UpdateCooldownPercent", percent)
            if percent >= 1.0:
                self.Charging = False
                self.call_function("PlayAnimationForward", self.InactiveToActive, 1.0, False)
                self.call_function("UpdateCooldownPercent", 1.0)
        self._uep_dash_ticks += 1
        _stats["ticks"] += 1

    def Destruct(self):
        close(self)

    def __uep_mixin_teardown__(self):
        close(self)


class LyraDashCooldownBlueprintFallbackProfile:
    def __init__(self):
        self._uep_dash_original_health = {}
        self.CurrentHealthComponent = None  # Next natural Tick binds original.

    def OnInitialized(self):
        self.call_mixin_original("OnInitialized")

    def ListenForDuration(self):
        proxy = getattr(self, PROXY)
        if valid(proxy):
            proxy.call_function("Cancel")
        self.call_mixin_original("ListenForDuration")

    def ResumeObservation(self):
        proxy = getattr(self, PROXY)
        if not (valid(proxy) and proxy.call_function("IsActive")):
            self.call_function("ListenForDuration")

    ResumeObservation.override = RESUME

    def Construct(self):
        self.call_mixin_original("Construct")
        self.call_function(RESUME)

    def UpdateCooldownPercent(self, Percent: float):
        self.call_mixin_original("UpdateCooldownPercent", Percent)

    def UpdateVisibility(self):
        self.call_mixin_original("UpdateVisibility")

    def OnCheckForDeath(self):
        self.call_mixin_original("OnCheckForDeath")
        if valid(self.CurrentHealthComponent):
            self._uep_dash_original_health[self.CurrentHealthComponent.get_path_name()] = self.CurrentHealthComponent

    def OnDeathStarted(self, OwningActor):
        self.call_mixin_original("OnDeathStarted", OwningActor)

    def Tick(self, MyGeometry, InDeltaTime):
        self.call_mixin_original("Tick", MyGeometry, InDeltaTime)

    def Destruct(self):
        close_original(self)

    def __uep_mixin_teardown__(self):
        close_original(self)
