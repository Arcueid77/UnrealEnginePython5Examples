"""Python equivalents of the original audio/VFX macros, without native caches."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid

WEAPON='/Game/Weapons/B_Weapon.B_Weapon_C'
INVISIBLE='/Game/Characters/Heroes/Mannequin/Meshes/SKM_Manny_Invis.SKM_Manny_Invis'
MAGAZINE='Lyra.ShooterGame.Weapon.MagazineAmmo'
_calls=dict(weapon=0,ammo=0,tag=0,specific=0)


def snapshot():return dict(_calls)
def weapon_for(target):
    _calls['weapon']+=1;equipment=target.call_function('GetComponentByClass',ue.find_class('LyraEquipmentManagerComponent'))
    if not valid(equipment):return None
    instances=equipment.call_function('GetEquipmentInstancesOfType',ue.find_class('LyraWeaponInstance'))
    if not instances or not valid(instances[0]):return None
    actors=instances[0].call_function('GetSpawnedActors')
    if not actors or not valid(actors[0]) or not actors[0].is_a(ue.load_class(WEAPON)):return None
    return actors[0]
def weapon_ammo(actor):
    """Return completion/ammo/diagnostic, preserving the macro's unwired exits."""
    _calls['ammo']+=1;instigator=actor.get_property('Instigator')
    if not valid(instigator):return False,0,False
    controller=instigator.call_function('GetController')
    if not valid(controller):return False,0,False
    quickbar=controller.get_component_by_type(ue.find_class('LyraQuickBarComponent'))
    if not valid(quickbar):return False,0,False
    item=quickbar.call_function('GetActiveSlotItem')
    if not valid(item):return False,0,True
    tag=GameplayTag(TagName=MAGAZINE);ammo=int(item.call_function('GetStatTagStackCount',tag)) if item.call_function('HasStatTag',tag) else 0
    return True,ammo,False
def ignore_tag(mesh):_calls['tag']+=1;return bool(mesh.call_function('ComponentHasTag','ignore'))
def ignore_specific(mesh):
    _calls['specific']+=1;return mesh.call_function('GetSkeletalMeshAsset')==ue.load_object(ue.find_class('SkeletalMesh'),INVISIBLE)
