"""Failure UI policy; native FText/animation primitives remain native.

The copied native message stays opaque at its FText field. The example's typed
VM adapter compares/copies that field without a Python string round trip.
"""

import copy
import unreal_engine as ue
from unreal_engine.structs import LatentActionInfo

from uep_runtime import SubscriptionScope
from .weapon_observer import valid


CLASS = "/ShooterCore/UserInterface/HUD/W_AbilityFailureFeedback.W_AbilityFailureFeedback_C"
CHANNEL = "Ability.UserFacingSimpleActivateFail.Message"
RESUME = "UEPResumeFailureObservation"
DELAY_COMPLETE = "UEPFailureDelayComplete"
DELAY_UUID = 0x554550
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "tickers_created": 0, "tickers_closed": 0,
          "widget_ticks": 0,
          "native_delays_started": 0, "native_delay_callbacks": 0,
          "messages": 0, "foreign_messages": 0, "health_rejections": 0, "same_reason_ignored": 0,
          "intros": 0, "outros": 0, "completions": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()))


def game_time(widget):
    return float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", widget))


def show(widget, payload):
    widget._uep_failure_reader.call_function("CopyFailureText", widget.FailureReasonTextWidget, payload)
    widget.call_function("SetVisibility", 3)  # Authored HitTestInvisible, not Visible.
    widget.call_function("PlayAnimationForward", widget.Intro, 1.0, False)
    widget._uep_failure_delay_pending = True
    ue.find_class("KismetSystemLibrary").get_cdo().call_function("RetriggerableDelay", widget, 1.0,
        LatentActionInfo(Linkage=0, UUID=DELAY_UUID, ExecutionFunction=DELAY_COMPLETE, CallbackTarget=widget))
    _stats["native_delays_started"] += 1
    _stats["intros"] += 1


def play_outro(widget, continuation):
    # Match PlayAnimation then BindToAnimationFinished ordering. These bounded
    # continuations use the existing native OnAnimationFinished event instead
    # of allocating additional dynamic Python delegates.
    widget.call_function("PlayAnimationForward", widget.Outro, 1.0, False)
    widget._uep_failure_completions.append(continuation)
    _stats["outros"] += 1


def same_reason(widget, payload):
    # This compiled helper has one named output, not a ReturnValue. UEP exposes
    # named outputs as a tuple; (False,) must never be used as a truthy bool.
    result = widget._uep_failure_reader.call_function("SameFailureText", widget.FailureReasonTextWidget, payload)
    if not isinstance(result, tuple) or len(result) != 1 or type(result[0]) is not bool:
        raise RuntimeError("typed failure text comparison output differs")
    return result[0]


def received(widget, payload):
    # BP's async event writes its output frame even when the owner/death branch
    # rejects delivery. Keep the latest opaque message for its deferred outro
    # continuation; the focused baseline must verify this observable ordering.
    widget._uep_failure_payload = payload
    if payload.PlayerController != widget.call_function("GetOwningPlayer"):
        widget._uep_failure_foreign += 1
        _stats["foreign_messages"] += 1
        return
    health = ue.find_class("LyraHealthComponent").get_cdo().call_function(
        "FindHealthComponent", widget.call_function("GetOwningPlayerPawn"))
    if not valid(health) or health.call_function("IsDeadOrDying"):
        _stats["health_rejections"] += 1
        return
    widget._uep_failure_messages += 1
    _stats["messages"] += 1
    if int(widget.call_function("GetVisibility")) == 1:
        show(widget, payload)
    elif same_reason(widget, payload):
        _stats["same_reason_ignored"] += 1  # Original true branch is disconnected.
    else:
        play_outro(widget, "replace")


def start(widget):
    if widget._uep_failure_scope is not None:
        return
    helper = ue.new_object(widget.PythonMessageAdapterClass)
    helper.add_to_root()
    scope = SubscriptionScope()
    widget._uep_failure_scope, widget._uep_failure_reader = scope, helper

    def read(proxy):
        payload, success = helper.call_function("ReadFailure", proxy)
        if success is not True:
            raise RuntimeError("typed failure message extraction failed")
        return payload.clone()

    try:
        scope.listen_gameplay_message(widget, CHANNEL, ue.find_struct("LyraAbilitySimpleFailureMessage"), read,
                                      lambda channel, payload: received(widget, payload))
    except Exception:
        try:
            scope.close()
        finally:
            try:
                helper.remove_from_root()
            finally:
                widget._uep_failure_scope = widget._uep_failure_reader = None
        raise
    _active[id(widget)] = widget.get_path_name()
    _stats["scopes_created"] += 1


def pause_owned_animations(widget):
    for name in ("Intro", "Outro"):
        animation = getattr(widget, name, None)
        if valid(animation):
            widget.call_function("PauseAnimation", animation)


def close(widget):
    scope, helper, ticker = widget._uep_failure_scope, widget._uep_failure_reader, widget._uep_failure_ticker
    widget._uep_failure_scope = widget._uep_failure_reader = widget._uep_failure_ticker = None
    widget._uep_failure_delay_pending = False
    widget._uep_failure_payload = None
    widget._uep_failure_completions = []  # Disarm before cancelling native work.
    _active.pop(id(widget), None)
    errors = []
    for action in ((lambda: ue.remove_ticker(ticker)) if ticker is not None else None,
                   scope.close if scope is not None else None):
        if action is not None:
            try:
                action()
            except Exception as error:
                errors.append(error)
    if ticker is not None:
        _stats["tickers_closed"] += 1
    if scope is not None:
        _stats["scopes_closed"] += 1
    for action in ((lambda: helper.remove_from_root()) if valid(helper) else None,
                   lambda: widget.call_function("CancelLatentActions"),
                   lambda: pause_owned_animations(widget)):
        if action is not None:
            try:
                action()
            except Exception as error:
                errors.append(error)
    if errors:
        _stats["errors"].extend(map(str, errors))
        raise RuntimeError("failure UI cleanup failed") from errors[0]


def close_original(widget):
    proxy = widget.UEPOriginalFailureProxy
    widget.UEPOriginalFailureProxy = None
    # Only this widget's authored delay and two exact original animation
    # delegates. Do not clear other widgets or all animation delegates.
    actions = [(lambda: proxy.call_function("Cancel")) if valid(proxy) else None,
               lambda: widget.call_function("CancelLatentActions"),
               lambda: widget.call_function("UEPRemoveOriginalFailureBindings"),
               lambda: pause_owned_animations(widget)]
    errors = []
    for action in actions:
        if action is not None:
            try:
                action()
            except Exception as error:
                errors.append(error)
    if errors:
        _stats["errors"].extend(map(str, errors))
        raise RuntimeError("original failure UI cleanup failed") from errors[0]


class LyraAbilityFailurePythonProfile:
    def __init__(self):
        self._uep_failure_scope = self._uep_failure_reader = self._uep_failure_ticker = None
        self._uep_failure_delay_pending = False
        self._uep_failure_payload = None
        self._uep_failure_ui_time = self._uep_failure_tick_delta = 0.0
        self._uep_failure_completions = []
        self._uep_failure_messages = self._uep_failure_foreign = 0

    def OnInitialized(self):
        self.call_function("SetVisibility", 1)
        start(self)

    def Construct(self):
        start(self)  # Hidden widget reuse cannot wait for native Widget Tick.

    def ResumeObservation(self):
        start(self)

    ResumeObservation.override = RESUME

    def DelayComplete(self, Linkage):
        if self._uep_failure_scope is None or not self._uep_failure_delay_pending:
            return
        if Linkage != 0:
            raise RuntimeError("unexpected native failure-delay continuation")
        self._uep_failure_delay_pending = False
        _stats["native_delay_callbacks"] += 1
        play_outro(self, "collapse")

    DelayComplete.override = DELAY_COMPLETE

    def OnAnimationFinished(self, Animation):
        self.call_mixin_original("OnAnimationFinished", Animation)
        if self._uep_failure_scope is None or Animation != self.Outro:
            return
        # Native BP bindings persist until explicitly removed; do not silently
        # turn their append/order behavior into one-shot bindings.
        for continuation in tuple(self._uep_failure_completions):
            if self._uep_failure_scope is None:
                break
            _stats["completions"] += 1
            if continuation == "collapse":
                self.call_function("SetVisibility", 1)
            else:
                show(self, self._uep_failure_payload)

    def OutroCompleted(self):
        if self._uep_failure_scope is not None:
            self.call_function("SetVisibility", 1)

    def OutroCurrentCompleted(self):
        if self._uep_failure_scope is not None:
            show(self, self._uep_failure_payload)

    def Destruct(self):
        close(self)

    def __uep_mixin_teardown__(self):
        close(self)


class LyraAbilityFailureBlueprintFallbackProfile:
    def OnInitialized(self):
        self.call_mixin_original("OnInitialized")

    def Construct(self):
        self.call_mixin_original("Construct")
        self.call_function(RESUME)

    def ResumeObservation(self):
        proxy = self.UEPOriginalFailureProxy
        if not valid(proxy) or not proxy.call_function("IsActive"):
            self.call_mixin_original(RESUME)

    ResumeObservation.override = RESUME

    def Destruct(self):
        close_original(self)

    def __uep_mixin_teardown__(self):
        close_original(self)
