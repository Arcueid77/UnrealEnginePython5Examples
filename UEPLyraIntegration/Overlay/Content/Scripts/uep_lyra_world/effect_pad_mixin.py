"""Gameplay Effect Pad construction and overlap intent on its retained BP class.

Match the authored Level=0, empty EffectContext and removal by source class.
The disconnected PrintString/attribute-read nodes are not runtime business.
Native GAS retains effect execution, duration, authority and replication.
"""

import unreal_engine as ue

from uep_lyra_hud.weapon_observer import valid


BEGIN_EVENT = "BndEvt__Volume_K2Node_ComponentBoundEvent_0_ComponentBeginOverlapSignature__DelegateSignature"
END_EVENT = "BndEvt__Volume_K2Node_ComponentBoundEvent_1_ComponentEndOverlapSignature__DelegateSignature"
CONSTRUCT_FUNCTION = "UEPConstructEffectPad"


def construct(pad):
    effect = pad.GameplayEffectToApply
    if not valid(effect):
        return
    if effect == pad.GE_Damage:
        material, text = pad.MAT_DamagePad, "DAMAGE"
    elif effect == pad.GE_Heal:
        material, text = pad.MAT_HealPad, "HEAL"
    else:
        material = pad.MAT_SpecialPad
        text = ue.find_class("KismetSystemLibrary").get_cdo().call_function("GetClassDisplayName", effect)
    pad.Pad.call_function("CreateDynamicMaterialInstance", 0, material)
    pad.Text.call_function("K2_SetText", text)
    # Only the special-class branch sets size; preserve authored defaults for
    # the DAMAGE/HEAL branches and invalid-class no-op behavior.
    if effect not in (pad.GE_Damage, pad.GE_Heal):
        pad.Text.call_function("SetWorldSize", 20.0)
    pad._uep_effect_pad_constructions += 1


def ability_system(actor):
    return ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("GetAbilitySystemComponent", actor)


class LyraEffectPadPythonProfile:
    def __init__(self):
        self._uep_effect_pad_constructions = 0
        self._uep_effect_pad_begin_intents = 0
        self._uep_effect_pad_end_intents = 0

    def UserConstructionScript(self):
        construct(self)

    # The retained BP construction (including explicit child Parent calls)
    # forwards virtually to this helper. One parent router serves descendants.
    UserConstructionScript.override = CONSTRUCT_FUNCTION

    def BeginOverlap(self, OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex, bFromSweep, SweepResult):
        asc = ability_system(OtherActor)
        if valid(asc):
            context = ue.find_struct("GameplayEffectContextHandle")()
            asc.call_function("BP_ApplyGameplayEffectToSelf", self.GameplayEffectToApply, 0.0, context)
            self._uep_effect_pad_begin_intents += 1

    BeginOverlap.override = BEGIN_EVENT

    def EndOverlap(self, OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex):
        asc = ability_system(OtherActor)
        if valid(asc):
            asc.call_function("RemoveActiveGameplayEffectBySourceEffect", self.GameplayEffectToApply, None, -1)
            self._uep_effect_pad_end_intents += 1

    EndOverlap.override = END_EVENT


class LyraEffectPadBlueprintFallbackProfile:
    def UserConstructionScript(self):
        self.call_mixin_original(CONSTRUCT_FUNCTION)

    UserConstructionScript.override = CONSTRUCT_FUNCTION

    def BeginOverlap(self, OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex, bFromSweep, SweepResult):
        self.call_mixin_original(BEGIN_EVENT, OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex, bFromSweep, SweepResult)

    BeginOverlap.override = BEGIN_EVENT

    def EndOverlap(self, OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex):
        self.call_mixin_original(END_EVENT, OverlappedComponent, OtherActor, OtherComp, OtherBodyIndex)

    EndOverlap.override = END_EVENT
