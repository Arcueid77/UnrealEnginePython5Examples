"""ADS BP camera/speed/input/UI choices; native movement/input/camera/audio stay."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, ModifyContextOptions
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_hud.message_payload_validation_fields import ON, CONTROLLER
from . import widget_lifecycle as widgets

CLASS = "/ShooterCore/Input/Abilities/GA_ADS.GA_ADS_C"
ACTIVATE_GATE, BROADCAST_GATE = "UEPADSActivateGate", "UEPADSBroadcastGate"
NATIVE_END, GUARD = "UEPADSNativeEndGate", "UEPADSTearingDown"
MAPPING = "/ShooterCore/Input/Mappings/IMC_ADS_Speed.IMC_ADS_Speed"
UI = "/ShooterCore/Input/Abilities/Struct_UIMessaging.Struct_UIMessaging"
CAMERA = "/ShooterCore/Camera/CM_ThirdPersonADS.CM_ThirdPersonADS_C"
_active = {}
_stats = dict(activations=0, scopes_created=0, scopes_closed=0, tasks_created=0, input_releases=0,
    native_ends=0, ui_on=0, ui_off=0, helpers_rooted=0, helpers_unrooted=0,
    mappings_added=0, mappings_removed=0, widget_added=0, widget_removed=0, errors=[])


def snapshot(): return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))
def library(name): return ue.find_class(name).get_cdo()


def input_system(ability):
    controller = ability.call_function("GetLyraPlayerControllerFromActorInfo")
    return library("SubsystemBlueprintLibrary").call_function("GetLocalPlayerSubsystem", controller,
        ue.find_class("EnhancedInputLocalPlayerSubsystem")) if valid(controller) else None


def options(): return ModifyContextOptions(bIgnoreAllPressedKeysUntilRelease=False, bForceImmediately=False, bNotifyUserSettings=False)


def broadcast(ability, enabled):
    payload = ue.load_object(ue.find_class("UserDefinedStruct"), UI)()
    setattr(payload, ON, bool(enabled)); setattr(payload, CONTROLLER, ability.call_function("GetLyraPlayerControllerFromActorInfo"))
    ability.set_property("MessageUI", payload)
    router = library("SubsystemBlueprintLibrary").call_function("GetGameInstanceSubsystem", ability, ue.find_class("GameplayMessageSubsystem"))
    helper = ue.new_object(ue.load_class("/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C"))
    helper.add_to_root(); _stats["helpers_rooted"] += 1
    try:
        helper.call_function("BroadcastUI", router, GameplayTag(TagName="Gameplay.Message.ADS"), payload)
        _stats["ui_on" if enabled else "ui_off"] += 1
    finally: helper.remove_from_root(); _stats["helpers_unrooted"] += 1


def sound(ability, enabled):
    name = "sfx_ZoomIn_nl_meta_Preset" if enabled else "sfx_ZoomOut_nl_meta_Preset"
    value = ue.load_object(ue.find_class("SoundBase"), "/Game/Audio/MetaSounds/"+name+"."+name)
    library("GameplayStatics").call_function("PlaySound2D", ability, value, 1., 1., 0., None, None, True)


def close(ability):
    scope = ability._uep_ads_scope; ability._uep_ads_scope = None
    _active.pop(id(ability), None)
    if scope is not None: scope.close(); _stats["scopes_closed"] += 1


def cleanup(ability, routed=True):
    if not ability._uep_ads_effects_live: return
    ability._uep_ads_effects_live = False
    ability.call_function("ClearCameraMode")
    if ability.call_function("IsLocallyControlled"):
        if routed: ability.call_function("BroadcastToUI", False)
        else: broadcast(ability, False)
        sound(ability, False)
    pawn = ability.call_function("GetLyraCharacterFromActorInfo")
    pawn.CharacterMovement.set_property("MaxWalkSpeed", ability.get_property("Max Walk SpeedDefault"))
    native = input_system(ability)
    if valid(native):
        native.call_function("RemoveMappingContext", ue.load_object(ue.find_class("InputMappingContext"), MAPPING), options())
        _stats["mappings_removed"] += 1


def released(ability, elapsed):
    _stats["input_releases"] += 1; ability.call_function("K2_EndAbility")


def activate(ability):
    close(ability)
    scope = SubscriptionScope(); ability._uep_ads_scope = scope
    _active[id(ability)] = ability.get_path_name(); _stats["activations"] += 1; _stats["scopes_created"] += 1
    try:
        ability.call_function("SetCameraMode", ue.load_class(CAMERA))
        movement = ability.call_function("GetLyraCharacterFromActorInfo").CharacterMovement
        ability.set_property("Max Walk SpeedDefault", float(movement.MaxWalkSpeed)); ability._uep_ads_effects_live = True
        movement.set_property("MaxWalkSpeed", ability.get_property("Max Walk SpeedDefault")*float(ability.ADSMultiplier))
        native = input_system(ability)
        if valid(native):
            native.call_function("AddMappingContext", ue.load_object(ue.find_class("InputMappingContext"), MAPPING), 11, options())
            _stats["mappings_added"] += 1
        if ability.call_function("IsLocallyControlled"):
            ability.call_function("BroadcastToUI", True); sound(ability, True)
        task = library("AbilityTask_WaitInputRelease").call_function("WaitInputRelease", ability, True)
        _stats["tasks_created"] += 1
        scope.bind_event(task, "OnRelease", lambda elapsed: released(ability, elapsed)); task.call_function("ReadyForActivation")
    except Exception as error:
        _stats["errors"].append(str(error)); teardown(ability); raise


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        if ability.get_property("bIsActive"):
            # Busy Mixin routing is deliberately disarmed. Shared cleanup must
            # not call the mixed public BroadcastToUI during this native end.
            cleanup(ability, routed=False); ability.call_function("K2_EndAbility")
    finally: ability.set_property(GUARD, False)


class LyraADSPythonProfile:
    def __init__(self): self._uep_ads_scope, self._uep_ads_effects_live = None, False
    def K2_ActivateAbility(self):
        activate(self); return False
    K2_ActivateAbility.override = ACTIVATE_GATE
    def BroadcastToUI(self, ON):
        broadcast(self, ON); return False
    BroadcastToUI.override = BROADCAST_GATE

    def NativeEnded(self, bWasCancelled):
        close(self); cleanup(self); _stats["native_ends"] += 1
        return False
    NativeEnded.override = NATIVE_END

    # UEP deliberately collects only local class entries. Explicitly forward
    # the shared parent policy, keeping UI ownership on native grant/removal.
    def K2_OnAbilityAdded(self):
        _stats["widget_added"] += widgets.add_many(self)

    def K2_OnAbilityRemoved(self):
        widgets.remove_many(self); _stats["widget_removed"] += 1

    def __uep_mixin_teardown__(self): teardown(self)


class LyraADSBlueprintFallbackProfile:
    def __init__(self): self._uep_ads_scope, self._uep_ads_effects_live = None, False

    def K2_ActivateAbility(self):
        self._uep_ads_effects_live = True
        return True
    K2_ActivateAbility.override = ACTIVATE_GATE

    def BroadcastToUI(self, ON): return True
    BroadcastToUI.override = BROADCAST_GATE

    def NativeEnded(self, bWasCancelled):
        self._uep_ads_effects_live = False
        return True
    NativeEnded.override = NATIVE_END

    # Shared parent UI is already migrated and independently grant/remove
    # validated. Keep that same native-registration policy on both ADS sides;
    # only ADS-owned business falls back to its retained original BP.
    def K2_OnAbilityAdded(self): widgets.add_many(self)
    def K2_OnAbilityRemoved(self): widgets.remove_many(self)
    def __uep_mixin_teardown__(self): teardown(self)
