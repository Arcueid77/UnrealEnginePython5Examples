"""Native timer callback decisions; collision/movement implementations stay native."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .grenade_vfx_mixin import LyraGrenadeVFXPythonProfile as VFXPython,LyraGrenadeVFXBlueprintFallbackProfile as VFXBlueprint

METHOD="PostLaunchCleanup"


def evidence(actor):
    row=getattr(actor,"_uep_grenade_cleanup",None)
    if row is None:
        row=dict(python_calls=0,fallback_calls=0,capsule_unignores=0,non_character_skips=0,mesh_unignores=0,rotation_writes=0,
            invalid_capsule_noops=0,invalid_mesh_noops=0,invalid_movement_noops=0)
        actor._uep_grenade_cleanup=row
    return row
def note(actor,name): evidence(actor)[name]+=1


def cleanup(actor):
    note(actor,"python_calls");instigator=actor.get_property("Instigator")
    if valid(instigator) and instigator.is_a(ue.find_class("Character")):
        capsule=instigator.get_property("CapsuleComponent")
        if valid(capsule): capsule.call_function("IgnoreActorWhenMoving",actor,False);note(actor,"capsule_unignores")
        else: note(actor,"invalid_capsule_noops")
    else: note(actor,"non_character_skips")
    # Original cast-failed exec rejoins here,not at function exit.
    mesh=actor.get_property("Mesh")
    if valid(mesh): mesh.call_function("IgnoreActorWhenMoving",instigator,False);note(actor,"mesh_unignores")
    else: note(actor,"invalid_mesh_noops")
    movement=actor.get_property("ProjectileMovement")
    if valid(movement): movement.set_property("bRotationFollowsVelocity",True);note(actor,"rotation_writes")
    else: note(actor,"invalid_movement_noops")


class LyraGrenadeCleanupPythonProfile:
    SetupVFX=VFXPython.SetupVFX
    def PostLaunchCleanup(self): cleanup(self)


class LyraGrenadeCleanupBlueprintFallbackProfile:
    SetupVFX=VFXBlueprint.SetupVFX
    def PostLaunchCleanup(self):
        note(self,"fallback_calls");return self.call_mixin_original(METHOD)
