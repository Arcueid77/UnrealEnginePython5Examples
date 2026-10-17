"""Grenade UI ownership policy; UIExtension, GAS and widgets remain native."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid
from .melee_trace_mixin import native_outputs

CLASS="/ShooterCore/Input/Abilities/GA_Grenade.GA_Grenade_C"
WIDGET="/ShooterCore/Weapons/Grenade/W_GrenadeCooldown.W_GrenadeCooldown_C"
TAG="HUD.Slot.ExtraEquipment"


def evidence(ability):
    value=getattr(ability,"_uep_grenade_widget",None)
    if value is None:
        value=dict(avatar_python=0,removed_python=0,avatar_fallback=0,removed_fallback=0,
            existing_noops=0,nonlocal_noops=0,missing_subsystem_noops=0,registrations=0,unregistrations=0,opaque_default_noops=0)
        ability._uep_grenade_widget=value
    return value


def handle_valid(handle):
    result=ue.find_class("UIExtensionHandleFunctions").get_cdo().call_function("IsValid",handle)
    fields=native_outputs("UIExtensionHandleFunctions","IsValid",result)
    value=fields["ReturnValue"]
    if type(value) is not bool: raise RuntimeError("native UIExtension IsValid did not return bool")
    return value


class LyraGrenadeWidgetPythonProfile:
    def K2_OnPawnAvatarSet(self):
        counts=evidence(self);counts["avatar_python"]+=1
        if handle_valid(self.get_property("Extension")): counts["existing_noops"]+=1;return
        if not self.call_function("IsLocallyControlled"): counts["nonlocal_noops"]+=1;return
        subsystem=ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem",self,ue.find_class("UIExtensionSubsystem"))
        if not valid(subsystem): counts["missing_subsystem_noops"]+=1;return
        # Original context is the ASC's owning Actor (PlayerState), not the
        # replaceable Pawn or its Controller. Preserve tag/class/priority.
        context=self.call_function("GetOwningActorFromActorInfo")
        handle=subsystem.call_function("K2_RegisterExtensionAsWidgetForContext",GameplayTag(TagName=TAG),ue.load_class(WIDGET),context,-1)
        self.set_property("Extension",handle);counts["registrations"]+=1

    def K2_OnAbilityRemoved(self):
        counts=evidence(self);counts["removed_python"]+=1
        # Original removal is unconditional, including invalid/nonlocal handles.
        ue.find_class("UIExtensionHandleFunctions").get_cdo().call_function("Unregister",self.get_property("Extension"))
        counts["unregistrations"]+=1
        # Native Unregister removes the extension, not its opaque DataPtr.
        # The original BP's empty struct literal has no reflected fields and
        # retains that pointer too (native Differential01). A C++-constructed
        # empty UIExtensionHandle would change the original post-event state.
        # ClearAbility immediately owns the remaining native destruction.
        counts["opaque_default_noops"]+=1


class LyraGrenadeWidgetBlueprintFallbackProfile:
    def K2_OnPawnAvatarSet(self):
        evidence(self)["avatar_fallback"]+=1;self.call_mixin_original("K2_OnPawnAvatarSet")
    def K2_OnAbilityRemoved(self):
        evidence(self)["removed_fallback"]+=1;self.call_mixin_original("K2_OnAbilityRemoved")
