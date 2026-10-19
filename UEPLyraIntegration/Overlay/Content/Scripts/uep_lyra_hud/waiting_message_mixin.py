"""Waiting text/countdown policy with original native message listener lifetime."""
from .match_message_mixin import team

CLASS = "/ShooterCore/GameplayCues/W_WaitingForPlayers_Message.W_WaitingForPlayers_Message_C"
TEXT, LISTEN, MESSAGE = "UEPWaitingLocalizedTeamText", "UEPWaitingBeginNativeListen", "UEPWaitingCountdownMessage"


def evidence(widget):
    if not hasattr(widget,"_uep_waiting_message"):
        widget._uep_waiting_message = dict(python_init=0,fallback_init=0,python_messages=0,fallback_messages=0,native_listens=0,countdown_starts=0,ignored_started=0)
    return widget._uep_waiting_message


def initialize(widget):
    counts = evidence(widget); counts["python_init"] += 1; found,index = team(widget)
    widget.call_function(TEXT,index if found else 0)
    widget.call_function(LISTEN); counts["native_listens"] += 1


def countdown(widget):
    counts = evidence(widget); counts["python_messages"] += 1
    if widget.get_property("CountdownStarted"): counts["ignored_started"] += 1; return False
    widget.set_property("CountdownStarted",True)
    widget.call_function("PlayAnimationForward",widget.get_property("CountDown"),1.,False); counts["countdown_starts"] += 1
    return False


class LyraWaitingMessagePythonProfile:
    def OnInitialized(self): initialize(self)
    def CountdownMessage(self): return countdown(self)
    CountdownMessage.override = MESSAGE


class LyraWaitingMessageBlueprintFallbackProfile:
    def OnInitialized(self): evidence(self)["fallback_init"] += 1; return self.call_mixin_original("OnInitialized")
    def CountdownMessage(self): evidence(self)["fallback_messages"] += 1; return True
    CountdownMessage.override = MESSAGE
