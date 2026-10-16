"""Interaction-duration BP presentation using native game time and typed messages."""

import copy
import unreal_engine as ue

from uep_runtime import SubscriptionScope
from .weapon_observer import valid


CLASS = "/ShooterCore/UserInterface/HUD/W_AbilityProgress.W_AbilityProgress_C"
CHANNEL = "Ability.Interaction.Duration.Message"
LISTEN_EVENT = "Listen For Duration Messages"
RESUME_EVENT = "UEPResumeDurationObservation"
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "messages": 0, "foreign_messages": 0, "ticks": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()))


def game_time(widget):
    return float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", widget))


def apply_duration(widget, duration):
    widget.Duration = float(duration)
    widget.StartTime = game_time(widget)
    widget.call_function("SetVisibility", 0)
    widget.ProgressBorder.call_function("GetDynamicMaterial").call_function(
        "SetVectorParameterValue", "ActiveRange", ue.FLinearColor(0.0, 0.0, 0.0, 0.0))


def read_payload(widget, proxy):
    payload, success = widget._uep_progress_reader.call_function("ReadDuration", proxy)
    if success is not True:
        raise RuntimeError("typed duration message extraction failed")
    return payload


def received(widget, payload):
    # Match the authored equality, including None==None; do not invent a new
    # Pawn-validity rule while migrating this UI business.
    if payload.Instigator != widget.call_function("GetOwningPlayerPawn"):
        widget._uep_progress_foreign_messages += 1
        _stats["foreign_messages"] += 1
        return
    apply_duration(widget, payload.Duration)
    widget._uep_progress_messages += 1
    _stats["messages"] += 1


def start(widget):
    if widget._uep_progress_scope is not None:
        return
    helper = ue.new_object(widget.PythonMessageAdapterClass)
    helper.add_to_root()
    scope = SubscriptionScope()
    widget._uep_progress_scope, widget._uep_progress_reader = scope, helper
    try:
        scope.listen_gameplay_message(widget, CHANNEL, ue.find_struct("LyraInteractionDurationMessage"),
                                      lambda proxy: read_payload(widget, proxy),
                                      lambda channel, payload: received(widget, payload))
    except Exception:
        scope.close()
        helper.remove_from_root()
        widget._uep_progress_scope = widget._uep_progress_reader = None
        raise
    _active[id(widget)] = widget.get_path_name()
    _stats["scopes_created"] += 1


def close(widget):
    scope, helper = widget._uep_progress_scope, widget._uep_progress_reader
    widget._uep_progress_scope = widget._uep_progress_reader = None
    _active.pop(id(widget), None)
    try:
        if scope is not None:
            scope.close()
            _stats["scopes_closed"] += 1
    except Exception as error:
        _stats["errors"].append(str(error))
        raise
    finally:
        if valid(helper):
            helper.remove_from_root()


def cancel_original(widget):
    proxy = widget.UEPOriginalDurationProxy
    widget.UEPOriginalDurationProxy = None
    if valid(proxy):
        proxy.call_function("Cancel")


class LyraAbilityProgressPythonProfile:
    def __init__(self):
        self._uep_progress_scope = self._uep_progress_reader = None
        self._uep_progress_ticks = 0
        self._uep_progress_messages = self._uep_progress_foreign_messages = 0

    def OnInitialized(self):
        self.call_function(LISTEN_EVENT)

    def ListenForDurationMessages(self):
        start(self)
        # The original async factory's `then` also sets the default duration
        # before any delivery. Construct subsequently collapses the widget.
        apply_duration(self, 0.0)

    ListenForDurationMessages.override = LISTEN_EVENT

    def ResumeObservation(self):
        # Explicit business activation for a hidden live Profile; no replay of
        # OnInitialized/Construct and no duration/visibility reset.
        start(self)

    ResumeObservation.override = RESUME_EVENT

    def Construct(self):
        # OnInitialized runs only once. A reused, collapsed widget cannot rely
        # on Tick to rearm after Destruct/level travel removed its listener.
        start(self)
        self.call_function("SetVisibility", 1)

    def Tick(self, MyGeometry, InDeltaTime):
        start(self)
        elapsed = game_time(self) - float(self.StartTime)
        remaining = float(self.Duration) - elapsed
        percent = ue.find_class("KismetMathLibrary").get_cdo().call_function("Divide_DoubleDouble", elapsed, float(self.Duration))
        text = ue.find_class("KismetTextLibrary").get_cdo().call_function(
            "Conv_DoubleToText", remaining, 0, False, False, 1, 324, 0, 0 if remaining >= 1.0 else 1)
        self.ProgressText.call_function("SetText", text)
        self.ProgressBorder.call_function("GetDynamicMaterial").call_function("SetScalarParameterValue", "Percent", percent)
        if percent >= 1.0:
            self.call_function("SetVisibility", 1)
        self._uep_progress_ticks += 1
        _stats["ticks"] += 1

    def Destruct(self):
        close(self)

    def __uep_mixin_teardown__(self):
        close(self)


class LyraAbilityProgressBlueprintFallbackProfile:
    def OnInitialized(self):
        self.call_mixin_original("OnInitialized")

    def ListenForDurationMessages(self):
        cancel_original(self)
        self.call_mixin_original(LISTEN_EVENT)

    ListenForDurationMessages.override = LISTEN_EVENT

    def ResumeObservation(self):
        proxy = self.UEPOriginalDurationProxy
        if valid(proxy) and proxy.call_function("IsActive"):
            return
        duration, started, visibility = self.Duration, self.StartTime, self.call_function("GetVisibility")
        self.call_mixin_original(LISTEN_EVENT)
        self.Duration, self.StartTime = duration, started
        self.call_function("SetVisibility", visibility)

    ResumeObservation.override = RESUME_EVENT

    def Construct(self):
        self.call_mixin_original("Construct")
        self.call_function(RESUME_EVENT)

    def Tick(self, MyGeometry, InDeltaTime):
        self.call_mixin_original("Tick", MyGeometry, InDeltaTime)

    def Destruct(self):
        cancel_original(self)

    def __uep_mixin_teardown__(self):
        cancel_original(self)
