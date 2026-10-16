"""Weapon/health pickup BP policy; native GAS, timers/replication/FX remain."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from .effect_pad_mixin import valid, ability_system

NAMES = ("B_WeaponSpawner", "B_AbilitySpawner")
CLASSES = tuple("/ShooterCore/Blueprint/"+name+"."+name+"_C" for name in NAMES)
PREFIX, RELOAD = "UEPDispatchSpawner", "UEPSpawnerHasReloadTag"
SPARE = "Lyra.ShooterGame.Weapon.SpareAmmo"
_stats = dict(constructions=0, begins=0, ticks=0, pickups=0, respawns=0, updates=0,
              weapon_gives=0, ability_gives=0, fallback_weapon_gives=0, fallback_ability_gives=0,
              grants=0, refills=0, rejected=0, failures=0, cues=0, errors=[])

def snapshot():
    return copy.deepcopy(_stats)

def library(name):
    return ue.find_class(name).get_cdo()

def construct(actor):
    material = ue.load_object(ue.find_class("MaterialInterface"),
        "/Game/Weapons/Spawnpad/Material/MI_InternalShapeGlow_Circle.MI_InternalShapeGlow_Circle")
    mid = actor.PadMesh.call_function("CreateDynamicMaterialInstance", 0, material, "None")
    actor.set_property("MID_Pad", mid)
    mid.call_function("SetScalarParameterValue", "Intensity", actor.get_property("Glow Intensity"))
    # Original promoted node converts scalar .02 to RGB=.02, Alpha=1,
    # then multiplies two colors. It does NOT multiply alpha by .02.
    color = library("KismetMathLibrary").call_function("Multiply_LinearColorLinearColor", actor.LightColor,
        ue.FLinearColor(.02,.02,.02,1.0))
    mid.call_function("SetVectorParameterValue", "Color", color)
    actor.PointLight.call_function("SetLightColor", actor.LightColor, True)
    actor.PointLight.call_function("SetIntensity", actor.LightIntensity)
    actor.PointLight.call_function("SetAttenuationRadius", actor.LightRadius)
    for component in (actor.NS_GunPad, actor.NS_GunPad_Loading):
        component.call_function("SetVariableLinearColor", "GunPad_Color", actor.LightColor)
    actor.WeaponMesh.call_function("SetCollisionEnabled", 0)
    actor.NS_GunPad_Loading.call_function("SetVariableFloat", "LifeTime", actor.LifeTimeReload)
    _stats["constructions"] += 1

def cue(actor, pawn):
    parameters = library("AbilitySystemBlueprintLibrary").call_function("MakeGameplayCueParameters",
        Instigator=actor, GameplayEffectLevel=1, AbilityLevel=1)
    library("GameplayCueFunctionLibrary").call_function("ExecuteGameplayCueOnActor", pawn,
        GameplayTag(TagName="GameplayCue.ShooterGame.Interact.WeaponPickup"), parameters)
    _stats["cues"] += 1

def weapon(actor, item_class, pawn):
    _stats["weapon_gives"] += 1
    subsystem = library("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem", actor, ue.find_class("LyraGamePhaseSubsystem"))
    if valid(subsystem) and subsystem.call_function("IsPhaseActive", GameplayTag(TagName="ShooterGame.GamePhase.PostGame")):
        _stats["rejected"] += 1
        return False
    controller = pawn.call_function("GetController") if valid(pawn) else None
    inventory = controller.get_component_by_type(ue.find_class("LyraInventoryManagerComponent")) if valid(controller) else None
    quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent")) if valid(controller) else None
    if not valid(inventory):
        _stats["rejected"] += 1
        return False
    existing = inventory.call_function("FindFirstItemStackByDefinition", item_class)
    if valid(existing) and actor.GiveAmmoForDuplicatedWeapons:
        tag = GameplayTag(TagName=SPARE)
        maximum = library("LyraWeaponSpawner").call_function("GetDefaultStatFromItemDef", item_class, tag)
        difference = int(maximum)-int(existing.call_function("GetStatTagStackCount", tag))
        if difference > 0:
            existing.call_function("AddStatTagStack", tag, difference)
            cue(actor, pawn);_stats["refills"] += 1
            return True
        # This original NetMulticast body is typed message transport only;
        # retain its native FText history and wildcard message ABI.
        actor.call_function("Broadcast Failure Message", pawn)
        _stats["failures"] += 1
        return False
    slot = int(quickbar.call_function("GetNextFreeItemSlot")) if valid(quickbar) else 0
    if slot < 0:
        _stats["rejected"] += 1
        return False
    cue(actor, pawn)  # Original order: cue, grant, slot, reload guard, select.
    item = inventory.call_function("AddItemDefinition", item_class, 1)
    if valid(quickbar):
        quickbar.call_function("AddItemToSlot", slot, item)
        reload_active = ue.call_function_by_class(actor, actor.get_class(), RELOAD, {"Pawn": pawn})["ReturnValue"]
        if not (reload_active and actor.IgnorePickUpWhenReload):
            quickbar.call_function("SetActiveSlotIndex", slot)
    _stats["grants"] += 1
    return True

def ability(actor, item_class, pawn):
    _stats["ability_gives"] += 1
    asc = ability_system(pawn) if valid(pawn) else None
    health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent")) if valid(pawn) else None
    if not valid(asc) or not valid(health) or float(health.call_function("GetHealth")) >= float(health.call_function("GetMaxHealth")):
        _stats["rejected"] += 1
        return False
    asc.call_function("BP_ApplyGameplayEffectToSelf", actor.GameplayEffectToApply, 0.0)
    cue(actor, pawn)
    return True

def guarded(function, *args):
    try:
        return function(*args)
    except Exception as error:
        _stats["errors"].append(str(error));raise

class LyraSpawnerPythonProfile:
    def Construction(self):
        guarded(construct, self);return False
    Construction.override = PREFIX+"Construction"

    def Begin(self):
        def apply(actor):
            actor.WeaponMesh.call_function("K2_AddWorldOffset", actor.get_property("Weapon Mesh Offset"), False, bTeleport=False)
            _stats["begins"] += 1
        guarded(apply, self);return False
    Begin.override = PREFIX+"Begin"

    def Tick(self):
        def apply(actor):
            actor.NS_GunPad_Loading.call_function("SetVariableFloat", "RibbonProgression", actor.CoolDownPercentage)
            _stats["ticks"] += 1
        guarded(apply, self);return False
    Tick.override = PREFIX+"Tick"

    def Pickup(self):
        def apply(actor):
            actor.PointLight.call_function("SetVisibility", False, False)
            actor.NS_GunPad.call_function("Deactivate")
            actor.NS_GunPad_Loading.call_function("Activate", True)
            _stats["pickups"] += 1
        guarded(apply, self);return False
    Pickup.override = PREFIX+"Pickup"

    def Respawn(self):
        def apply(actor):
            actor.PointLight.call_function("SetVisibility", True, False)
            actor.NS_GunPad.call_function("Activate", True)
            actor.Timeline_Spawn.call_function("PlayFromStart")
            _stats["respawns"] += 1
        guarded(apply, self);return False
    Respawn.override = PREFIX+"Respawn"

    def Update(self, Value):
        def apply(actor):
            actor.NS_GunPad.call_function("SetVariableFloat", "Luminosity", Value)
            _stats["updates"] += 1
        guarded(apply, self);return False
    Update.override = PREFIX+"Update"

    def WeaponGive(self, WeaponItemClass, ReceivingPawn):
        return int(guarded(weapon, self, WeaponItemClass, ReceivingPawn))
    WeaponGive.override = PREFIX+"WeaponGive"

    def AbilityGive(self, WeaponItemClass, ReceivingPawn):
        return int(guarded(ability, self, WeaponItemClass, ReceivingPawn))
    AbilityGive.override = PREFIX+"AbilityGive"

class LyraSpawnerBlueprintFallbackProfile:
    def Construction(self):
        return self.call_mixin_original(PREFIX+"Construction")
    Construction.override = PREFIX+"Construction"
    def Begin(self):
        return self.call_mixin_original(PREFIX+"Begin")
    Begin.override = PREFIX+"Begin"
    def Tick(self):
        return self.call_mixin_original(PREFIX+"Tick")
    Tick.override = PREFIX+"Tick"
    def Pickup(self):
        return self.call_mixin_original(PREFIX+"Pickup")
    Pickup.override = PREFIX+"Pickup"
    def Respawn(self):
        return self.call_mixin_original(PREFIX+"Respawn")
    Respawn.override = PREFIX+"Respawn"
    def Update(self, Value):
        return self.call_mixin_original(PREFIX+"Update", Value)
    Update.override = PREFIX+"Update"
    def WeaponGive(self, WeaponItemClass, ReceivingPawn):
        _stats["fallback_weapon_gives"] += 1
        return self.call_mixin_original(PREFIX+"WeaponGive", WeaponItemClass, ReceivingPawn)
    WeaponGive.override = PREFIX+"WeaponGive"
    def AbilityGive(self, WeaponItemClass, ReceivingPawn):
        _stats["fallback_ability_gives"] += 1
        return self.call_mixin_original(PREFIX+"AbilityGive", WeaponItemClass, ReceivingPawn)
    AbilityGive.override = PREFIX+"AbilityGive"
