"""Health receiver decisions only; GAS, health replication and AI sense stay native."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .parts_changed_mixin import LyraCharacterPartsChangedPythonProfile as PartsPython, LyraCharacterPartsChangedBlueprintFallbackProfile as PartsBlueprint

BOUND_EVENT = "BndEvt__Hero_ShooterMannequin_HealthComponent_K2Node_ComponentBoundEvent_0_LyraHealth_AttributeChanged__DelegateSignature"


def evidence(actor):
    value = getattr(actor, "_uep_character_health_changed", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, authority_noops=0, instigator_noops=0,
            self_noops=0, controller_noops=0, damage_reports=0, last_report=None)
        actor._uep_character_health_changed = value
    return value


class LyraCharacterHealthChangedPythonProfile:
    ClearInventory = PartsPython.ClearInventory
    GetEmoteAudioComponent = PartsPython.GetEmoteAudioComponent
    SetEmoteAudioComponent = PartsPython.SetEmoteAudioComponent
    ChangeQuickbarSlot = PartsPython.ChangeQuickbarSlot
    AddInitialInventory = PartsPython.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = PartsPython.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = PartsPython.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = PartsPython.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = PartsPython.K2_OnDeathFinished
    K2_OnReset = PartsPython.K2_OnReset
    PythonCharacterPartsChanged = PartsPython.PythonCharacterPartsChanged

    def PythonHealthChanged(self, HealthComponent, OldValue: float, NewValue: float, Instigator):
        counts = evidence(self); counts["python_calls"] += 1; counts["last_report"] = None
        if not self.call_function("HasAuthority"):
            counts["authority_noops"] += 1; return
        if not valid(Instigator) or not Instigator.is_a(ue.find_class("PlayerState")):
            counts["instigator_noops"] += 1; return
        pawn = Instigator.call_function("GetPawn")
        if pawn == self:
            counts["self_noops"] += 1; return
        controller = self.call_function("GetController")
        ai = ue.find_class("AIBlueprintHelperLibrary").get_cdo().call_function("GetAIController", controller)
        if not valid(ai):
            counts["controller_noops"] += 1; return
        # Preserve the original raw Old-New value, zero HitLocation and default
        # Tag. A missing Pawn uses BP's default vector without a null-read warning.
        location = pawn.call_function("K2_GetActorLocation") if valid(pawn) else ue.FVector(0., 0., 0.)
        amount = float(OldValue)-float(NewValue)
        ue.find_class("AISense_Damage").get_cdo().call_function("ReportDamageEvent", self, ai, pawn,
            amount, location, ue.FVector(0., 0., 0.))
        counts["damage_reports"] += 1
        counts["last_report"] = dict(amount=amount, controller=ai.get_path_name(),
            instigator=pawn.get_path_name() if valid(pawn) else None,
            location=[float(location.x), float(location.y), float(location.z)], hit_location=[0., 0., 0.])

    PythonHealthChanged.override = BOUND_EVENT


class LyraCharacterHealthChangedBlueprintFallbackProfile:
    ClearInventory = PartsBlueprint.ClearInventory
    GetEmoteAudioComponent = PartsBlueprint.GetEmoteAudioComponent
    SetEmoteAudioComponent = PartsBlueprint.SetEmoteAudioComponent
    ChangeQuickbarSlot = PartsBlueprint.ChangeQuickbarSlot
    AddInitialInventory = PartsBlueprint.AddInitialInventory
    CreateOrUpdateOutlineIfNeeded = PartsBlueprint.CreateOrUpdateOutlineIfNeeded
    OnTeamOrCosmeticsChanged = PartsBlueprint.OnTeamOrCosmeticsChanged
    UpdateCustomStencilFromTeamID = PartsBlueprint.UpdateCustomStencilFromTeamID
    K2_OnDeathFinished = PartsBlueprint.K2_OnDeathFinished
    K2_OnReset = PartsBlueprint.K2_OnReset
    PythonCharacterPartsChanged = PartsBlueprint.PythonCharacterPartsChanged

    def PythonHealthChanged(self, HealthComponent, OldValue: float, NewValue: float, Instigator):
        counts = evidence(self); counts["fallback_calls"] += 1; counts["last_report"] = None
        self.call_mixin_original(BOUND_EVENT, HealthComponent, OldValue, NewValue, Instigator)

    PythonHealthChanged.override = BOUND_EVENT
