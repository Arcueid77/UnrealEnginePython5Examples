"""Original looping GameplayCue widget policy behind base-owned native gates."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/Game/GameplayCueNotifies/GCNL_Widget_Base.GCNL_Widget_Base_C"
START, REMOVE = "UEPCueWidgetStart", "UEPCueWidgetRemove"
INTERFACE = "/Game/GameplayCueNotifies/I_GameplayCueWidget.I_GameplayCueWidget_C"
UNRESOLVED = "Unable to determine local player for widget from Instigator:  "


def lib(name): return ue.find_class(name).get_cdo()


def evidence(actor):
    if not hasattr(actor, "_uep_cue_widget"):
        actor._uep_cue_widget = dict(python_start=0, fallback_start=0, python_remove=0, fallback_remove=0,
            bot_skips=0, remote_skips=0, unresolved=0, creates=0, adds=0, messages=0, removals=0, invalid_widgets=0)
    return actor._uep_cue_widget


def message(actor, text):
    lib("KismetSystemLibrary").call_function("PrintString", WorldContextObject=actor, InString=text,
        bPrintToScreen=True, bPrintToLog=True, TextColor=ue.FLinearColor(0., .66, 1., 1.), Duration=2., Key="None")


def start(actor, parameters):
    counts = evidence(actor); counts["python_start"] += 1
    instigator = lib("AbilitySystemBlueprintLibrary").call_function("GetInstigatorActor", parameters)
    controller = None
    if valid(instigator):
        if instigator.is_a(ue.find_class("PlayerState")):
            if instigator.get_property("bIsABot"): counts["bot_skips"] += 1; return False
            controller = instigator.call_function("GetPlayerController")
            if valid(controller):
                if not controller.call_function("IsLocalController"): counts["remote_skips"] += 1; return False
            else:
                counts["unresolved"] += 1
                message(actor, UNRESOLVED+lib("KismetSystemLibrary").call_function("GetDisplayName", instigator)); return False
        else:
            counts["unresolved"] += 1
            message(actor, UNRESOLVED+lib("KismetSystemLibrary").call_function("GetDisplayName", instigator)); return False
    actor.set_property("OptionalLocalController", controller)
    widget = lib("WidgetBlueprintLibrary").call_function("Create", actor, actor.get_property("WidgetToSpawn"), controller)
    actor.set_property("SpawnedWidget", widget); counts["creates"] += 1
    if valid(widget):
        # The original always sends the interface message after AddToPlayerScreen,
        # including when that native operation returns false.
        widget.call_function("AddToPlayerScreen", 0); counts["adds"] += 1
        if lib("KismetSystemLibrary").call_function("DoesImplementInterface", widget, ue.load_class(INTERFACE)):
            widget.call_function("ConstructFromCueParams", parameters); counts["messages"] += 1
    else: counts["invalid_widgets"] += 1; message(actor, "Failed to create widget!")
    return False


def remove(actor):
    counts = evidence(actor); counts["python_remove"] += 1
    widget = actor.get_property("SpawnedWidget")
    if valid(widget): widget.call_function("RemoveFromParent"); counts["removals"] += 1
    # Source deliberately retains SpawnedWidget and OptionalLocalController.
    return False


class LyraCueWidgetPythonProfile:
    def Start(self, Target, Parameters, SpawnResults): return start(self, Parameters)
    Start.override = START
    def Remove(self, Target, Parameters, SpawnResults): return remove(self)
    Remove.override = REMOVE


class LyraCueWidgetBlueprintFallbackProfile:
    def Start(self, Target, Parameters, SpawnResults): evidence(self)["fallback_start"] += 1; return True
    Start.override = START
    def Remove(self, Target, Parameters, SpawnResults): evidence(self)["fallback_remove"] += 1; return True
    Remove.override = REMOVE
