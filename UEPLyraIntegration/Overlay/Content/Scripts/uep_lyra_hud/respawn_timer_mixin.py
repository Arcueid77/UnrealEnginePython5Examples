"""Respawn duration/completion UI policy; native timers, audio and UMG retained."""
import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from .weapon_observer import valid
from .ability_progress_mixin import game_time
from . import pooled_widget_lifetime as pools

CLASS = "/ShooterCore/Game/Respawn/W_RespawnTimer.W_RespawnTimer_C"
DURATION_CHANNEL = "Ability.Respawn.Duration.Message"
COMPLETED_CHANNEL = "Ability.Respawn.Completed.Message"
RESUME = "UEPResumeRespawnObservation"
CLEANUP = "UEPRemoveOriginalRespawnAnimationBinding"
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "duration_messages": 0, "completed_messages": 0,
          "foreign_messages": 0, "timer_updates": 0, "timer_sets": 0, "timer_clears": 0,
          "animation_completions": 0, "audio_spawn_attempts": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()), pool_lifetime=pools.snapshot())


def systems():
    return ue.find_class("KismetSystemLibrary").get_cdo()


def countdown_audio(widget):
    # AutoDestroy/world teardown can invalidate the native component before
    # GC nulls this BP reference. UEP may reject wrapping that stale value
    # during property access, before valid(value) can inspect it. Only that
    # exact optional-reference condition is absent audio, not other errors or
    # an invalid widget. Native timers/subscriptions must still be cleaned.
    try:
        audio = widget.CountdownAudio
    except Exception as error:
        if str(error) != "uobject is in invalid state" or not valid(widget):
            raise
        return None
    return audio if valid(audio) else None


def set_timer(widget):
    systems().call_function("K2_SetTimer", widget, "UpdateRespawnText", 0.25, True, False, 0.0, 0.0)
    _stats["timer_sets"] += 1
    widget._uep_respawn_resume_timer = True


def clear_timer(widget):
    systems().call_function("K2_ClearTimer", widget, "UpdateRespawnText")
    _stats["timer_clears"] += 1
    widget._uep_respawn_resume_timer = False


def read(widget, proxy, name):
    payload, success = widget._uep_respawn_reader.call_function(name, proxy)
    if success is not True:
        raise RuntimeError("typed respawn payload extraction failed")
    return payload


def player_state(widget):
    controller = widget.call_function("GetOwningPlayer")
    return controller.PlayerState if valid(controller) else None


def duration_received(widget, payload):
    if payload.Instigator != player_state(widget):
        widget._uep_respawn_foreign += 1
        _stats["foreign_messages"] += 1
        return
    widget.Duration = float(payload.Duration)
    widget.StartTime = game_time(widget)
    if not widget.Respawning:
        widget.call_function("PlayAnimation", widget.Intro, 0.0, 1, 0, 1.0, False)
    widget.Respawning = True
    widget.call_function("UpdateRespawnText")
    set_timer(widget)
    widget.call_function("SetVisibility", 0)
    widget._uep_respawn_duration_messages += 1
    _stats["duration_messages"] += 1


def completed_received(widget, payload):
    if payload.Instigator != player_state(widget):
        widget._uep_respawn_foreign += 1
        _stats["foreign_messages"] += 1
        return
    if widget.Respawning:
        widget.call_function("OnTimerFinished")
    widget._uep_respawn_completed_messages += 1
    _stats["completed_messages"] += 1


def start(widget):
    if widget._uep_respawn_scope is not None:
        return
    pools.refresh()
    if not pools.may_activate(widget):
        return
    helper = ue.new_object(widget.PythonMessageAdapterClass)
    helper.add_to_root()
    scope = SubscriptionScope()
    widget._uep_respawn_scope, widget._uep_respawn_reader = scope, helper
    try:
        scope.listen_gameplay_message(widget, DURATION_CHANNEL, ue.find_struct("LyraInteractionDurationMessage"),
                                      lambda proxy: read(widget, proxy, "ReadDuration"),
                                      lambda channel, payload: duration_received(widget, payload))
        scope.listen_gameplay_message(widget, COMPLETED_CHANNEL, ue.find_struct("LyraVerbMessage"),
                                      lambda proxy: read(widget, proxy, "ReadVerb"),
                                      lambda channel, payload: completed_received(widget, payload))
    except Exception:
        scope.close()
        helper.remove_from_root()
        widget._uep_respawn_scope = widget._uep_respawn_reader = None
        raise
    _active[id(widget)] = widget.get_path_name()
    _stats["scopes_created"] += 1
    try:
        # Collapsed respawn widgets do not Tick. Retain a dormant membership
        # watch so native reinsertion can explicitly rearm observation without
        # fabricating Construct or changing native pool contents.
        pools.watch(widget, lambda value: close(value, keep_pool_watch=True),
                    lambda value: value.call_function(RESUME))
    except Exception:
        close(widget)
        raise


def close(widget, keep_pool_watch=False):
    if not keep_pool_watch:
        pools.unwatch(widget)
    scope, helper = widget._uep_respawn_scope, widget._uep_respawn_reader
    resume_timer = bool(systems().call_function("K2_IsTimerActive", widget, "UpdateRespawnText")) if scope is not None else widget._uep_respawn_resume_timer
    widget._uep_respawn_scope = widget._uep_respawn_reader = None
    widget._uep_respawn_outro_callbacks = 0
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
        clear_timer(widget)
        widget._uep_respawn_resume_timer = resume_timer
        audio = countdown_audio(widget)
        if audio is not None:
            audio.call_function("Stop")


def close_original(widget):
    resume_timer = bool(systems().call_function("K2_IsTimerActive", widget, "UpdateRespawnText"))
    for name in ("RespawnDurationAsyncAction", "RespawnCompletedAsyncAction"):
        proxy = getattr(widget, name)
        setattr(widget, name, None)
        if valid(proxy):
            proxy.call_function("Cancel")
    clear_timer(widget)
    widget._uep_respawn_resume_timer = resume_timer
    widget.call_function(CLEANUP)
    audio = countdown_audio(widget)
    if audio is not None:
        audio.call_function("Stop")


class LyraRespawnTimerPythonProfile:
    def __init__(self):
        self._uep_pool_owner = getattr(self, "_uep_pool_owner", None)
        self._uep_respawn_scope = self._uep_respawn_reader = None
        self._uep_respawn_resume_timer = getattr(self, "_uep_respawn_resume_timer", False)
        self._uep_respawn_outro_callbacks = 0
        self._uep_respawn_duration_messages = self._uep_respawn_completed_messages = 0
        self._uep_respawn_foreign = 0

    def ListenForDuration(self):
        start(self)

    def ResumeObservation(self):
        start(self)
        if self._uep_respawn_scope is not None and self.Respawning and self._uep_respawn_resume_timer:
            set_timer(self)

    ResumeObservation.override = RESUME

    def Construct(self):
        self.call_function("ListenForDuration")
        self.call_function("SetVisibility", 1)

    def UpdateRespawnText(self):
        if self._uep_respawn_scope is None:
            return  # Closed timer/pool continuation must not revive observation.
        # TimeUntilRespawn is a function-local BP variable, not a UObject field.
        remaining = float(self.StartTime) + float(self.Duration) - game_time(self)
        self._uep_respawn_remaining = remaining
        _stats["timer_updates"] += 1
        if remaining > 0.0:
            # The actual compiled BP baseline updates both materials. A compact
            # graph's multi-link pin is not a substitute for VM comparison.
            glow = self.FillGlow.call_function("GetDynamicMaterial")
            fill = self.Fill.call_function("GetDynamicMaterial")
            percent = ue.find_class("KismetMathLibrary").get_cdo().call_function("Divide_DoubleDouble", remaining, float(self.Duration))
            glow.call_function("SetScalarParameterValue", "AnimateArcFill", percent)
            fill.call_function("SetScalarParameterValue", "AnimateArcFill", percent)
            value = ue.find_class("KismetMathLibrary").get_cdo().call_function("FCeil", remaining)
            self.Time.call_function("SetCurrentValue", float(value))
            audio = countdown_audio(self)
            if audio is None:
                self.CountdownAudio = ue.find_class("GameplayStatics").get_cdo().call_function("SpawnSound2D", self,
                    self.PythonCountdownSound, 1.0, 1.0, 0.0, None, False, True)
                _stats["audio_spawn_attempts"] += 1
                audio = countdown_audio(self)
            if audio is not None:
                audio.call_function("SetFloatParameter", "Progress", percent)
        else:
            self.Respawning = False
            self.Time.call_function("SetCurrentValue", 0.0)
            self.call_function("PlayAnimationForward", self.Outro, 1.0, False)
            self._uep_respawn_outro_callbacks += 1  # Original delegates persist.

    def OnTimerFinished(self):
        self.call_function("SetVisibility", 1)
        clear_timer(self)
        audio = countdown_audio(self)
        if audio is not None:
            audio.call_function("SetFloatParameter", "Progress", 0.0)
            audio.call_function("StopDelayed", 0.5)
        # Original completion message does not clear Respawning here.

    def OnAnimationFinished(self, Animation):
        self.call_mixin_original("OnAnimationFinished", Animation)
        if self._uep_respawn_scope is not None and Animation == self.Outro:
            for index in range(self._uep_respawn_outro_callbacks):
                self.call_function("OnTimerFinished")
                _stats["animation_completions"] += 1

    def Destruct(self):
        close(self)

    def __uep_mixin_teardown__(self):
        close(self)


class LyraRespawnTimerBlueprintFallbackProfile:
    def ListenForDuration(self):
        close_original(self)
        self.call_mixin_original("ListenForDuration")

    def ResumeObservation(self):
        proxy = self.RespawnDurationAsyncAction
        if not (valid(proxy) and proxy.call_function("IsActive")):
            self.call_function("ListenForDuration")
        if self.Respawning and getattr(self, "_uep_respawn_resume_timer", False):
            set_timer(self)

    ResumeObservation.override = RESUME

    def Construct(self):
        self.call_mixin_original("Construct")

    def UpdateRespawnText(self):
        self.call_mixin_original("UpdateRespawnText")

    def OnTimerFinished(self):
        self.call_mixin_original("OnTimerFinished")

    def OnAnimationFinished(self, Animation):
        self.call_mixin_original("OnAnimationFinished", Animation)

    def Destruct(self):
        close_original(self)

    def __uep_mixin_teardown__(self):
        close_original(self)
