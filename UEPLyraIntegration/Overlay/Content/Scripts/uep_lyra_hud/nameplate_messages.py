"""Names/layout of the retained project-defined nameplate message structs."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from .weapon_observer import valid

INFO = "/Game/UI/Indicators/Message_NameplateInfo.Message_NameplateInfo"
REQUEST = "/Game/UI/Indicators/Message_NameplateRequest.Message_NameplateRequest"
PAWN = "Pawn_2_664CF5634FF0B13BFD2867B6123BF66D"
MANAGER = "NameplateManager_4_664CF5634FF0B13BFD2867B6123BF66D"
PREFIX = "Gameplay.Message.Nameplate."


def payload_type(path):
    return ue.load_object(ue.find_class("UserDefinedStruct"), path)


def router(context):
    return ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
        "GetGameInstanceSubsystem", context, ue.find_class("GameplayMessageSubsystem"))


def broadcast(context, helper, action, value):
    info = action != "Discover"
    payload = payload_type(INFO if info else REQUEST)()
    setattr(payload, PAWN if info else MANAGER, value)
    helper.call_function("BroadcastNameplateInfo" if info else "BroadcastNameplateRequest",
                         router(context), GameplayTag(TagName=PREFIX+action), payload)


def read(helper, proxy, info):
    payload, success = helper.call_function("ReadNameplateInfo" if info else "ReadNameplateRequest", proxy)
    if success is not True:
        raise RuntimeError("typed nameplate message extraction failed")
    return payload


def owner_pawn(source):
    owner = source.call_function("GetOwner")
    return owner if valid(owner) and owner.is_a(ue.find_class("Pawn")) else None
