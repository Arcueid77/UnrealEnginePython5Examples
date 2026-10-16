"""Test-only native lethal GE producer; never relax the bounded bridge API."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag

DAMAGE = "/Game/GameplayEffects/Damage/GE_Damage_Basic_SetByCaller.GE_Damage_Basic_SetByCaller_C"


def apply(asc, health_before):
    if health_before <= 0:
        raise RuntimeError("Lethal fixture requires a living authority Pawn")
    context = asc.call_function("MakeEffectContext")
    spec = asc.call_function("MakeOutgoingSpec", ue.load_class(DAMAGE), 1., context)
    spec = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function(
        "AssignTagSetByCallerMagnitude", spec, GameplayTag(TagName="SetByCaller.Damage"), float(health_before))
    # The original instant GE executes native HealthSet/OnOutOfHealth -> death
    # GameplayEvent. Do not write Health or send/replay that event ourselves.
    asc.call_function("BP_ApplyGameplayEffectSpecToSelf", spec)
