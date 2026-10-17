"""The actual retained-class activation event; GAS/RPC/task implementations remain native."""
import unreal_engine as ue
from .dash_local_direction_mixin import LyraDashLocalDirectionPythonProfile, LyraDashLocalDirectionBlueprintFallbackProfile

METHOD = "K2_ActivateAbility"
TASKS = "UEPDashStartNativeTasks"


def evidence(ability):
    value = getattr(ability, "_uep_dash_activation", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, last=None)
        ability._uep_dash_activation = value
    return value


def activate(ability):
    value = evidence(ability); value["python_calls"] += 1
    data = dict(local_controlled=bool(ability.call_function("IsLocallyControlled")), zero_direction=None, committed=None,
        crouched_before=None, uncrouch_called=False, authority=None, rpc_sent=False, native_tasks_started=False, order=["local-control"])
    value["last"] = data
    # Remote authority waits for the unchanged original reliable SendInfo body.
    if not data["local_controlled"]: return
    ability.call_function("UEPDashPrepareLocalDirection"); data["order"].append("prepare-local")
    data["zero_direction"] = bool(ue.find_class("KismetMathLibrary").get_cdo().call_function("Vector_IsNearlyZero", ability.get_property("Direction"), .0001))
    data["order"].append("zero-check")
    if data["zero_direction"]:
        data["order"].append("cancel"); ability.call_function("K2_CancelAbility"); return
    data["committed"] = bool(ability.call_function("K2_CommitAbility")); data["order"].append("commit")
    if not data["committed"]:
        data["order"].append("cancel"); ability.call_function("K2_CancelAbility"); return
    actor = ability.call_function("GetLyraCharacterFromActorInfo")
    data["crouched_before"] = bool(actor.get_property("bIsCrouched"))
    if data["crouched_before"]:
        actor.call_function("UnCrouch", False); data["uncrouch_called"] = True; data["order"].append("uncrouch")
    data["authority"] = bool(ability.call_function("K2_HasAuthority")); data["order"].append("authority")
    if not data["authority"]:
        ability.call_function("SendInfo", ability.get_property("Direction"), ability.get_property("Montage"))
        data["rpc_sent"] = True; data["order"].append("send-info")
    # One native event entry to the original montage/RootMotion/Cue/UI/Delay graph.
    ability.call_function(TASKS); data["native_tasks_started"] = True; data["order"].append("native-tasks")


class LyraDashActivationPythonProfile:
    SelectDirectionalMontage = LyraDashLocalDirectionPythonProfile.__dict__["SelectDirectionalMontage"]
    StoreRemoteInput = LyraDashLocalDirectionPythonProfile.__dict__["StoreRemoteInput"]
    PrepareLocalDirection = LyraDashLocalDirectionPythonProfile.__dict__["PrepareLocalDirection"]
    def Activate(self): return activate(self)
    Activate.override = METHOD


class LyraDashActivationBlueprintFallbackProfile:
    SelectDirectionalMontage = LyraDashLocalDirectionBlueprintFallbackProfile.__dict__["SelectDirectionalMontage"]
    StoreRemoteInput = LyraDashLocalDirectionBlueprintFallbackProfile.__dict__["StoreRemoteInput"]
    PrepareLocalDirection = LyraDashLocalDirectionBlueprintFallbackProfile.__dict__["PrepareLocalDirection"]
    def Activate(self):
        evidence(self)["fallback_calls"] += 1
        return self.call_mixin_original(METHOD)
    Activate.override = METHOD
