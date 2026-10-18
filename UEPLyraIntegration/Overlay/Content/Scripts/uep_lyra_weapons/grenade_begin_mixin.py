"""Retained Actor BeginPlay decisions; material/collision/timer work is native."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .grenade_actions_mixin import LyraGrenadeActionsPythonProfile as ActionsPython,LyraGrenadeActionsBlueprintFallbackProfile as ActionsBlueprint


def evidence(actor):
    row=getattr(actor,"_uep_grenade_begin",None)
    if row is None:
        row=dict(python_calls=0,fallback_calls=0,material_requests=0,invalid_material_noops=0,character_capsule_ignores=0,
            character_mesh_ignores=0,non_character_skips=0,invalid_capsule_noops=0,invalid_mesh_noops=0,vfx_calls=0,detonate_timers=0,timer_handle_writes=0,cleanup_timers=0)
        actor._uep_grenade_begin=row
    return row
def note(actor,key): evidence(actor)[key]+=1


def schedule(system,actor,name,duration):
    # Native K2_SetTimer binds this Actor's named zero-input UFunction,then
    # calls the original K2_SetTimerDelegate path. Both original delays have
    # zero start variance. Do not bind a Python lambda/alternate owner/ticker.
    return system.call_function("K2_SetTimer",Object=actor,FunctionName=name,Time=duration,bLooping=False,bMaxOncePerFrame=False,
        InitialStartDelay=0.,InitialStartDelayVariance=0.)


def begin(actor):
    note(actor,"python_calls");material=actor.get_property("MaterialExplosion")
    if valid(material):
        material.call_function("SetForceMipLevelsToBeResident",OverrideForceMiplevelsToBeResident=True,bForceMiplevelsToBeResidentValue=True,ForceDuration=3.,CinematicTextureGroups=0,bFastResponse=True)
        note(actor,"material_requests")
    else: note(actor,"invalid_material_noops")
    instigator=actor.get_property("Instigator")
    if valid(instigator) and instigator.is_a(ue.find_class("Character")):
        capsule=instigator.get_property("CapsuleComponent")
        if valid(capsule): capsule.call_function("IgnoreActorWhenMoving",actor,True);note(actor,"character_capsule_ignores")
        else: note(actor,"invalid_capsule_noops")
        mesh=actor.get_property("Mesh")
        if valid(mesh): mesh.call_function("IgnoreActorWhenMoving",instigator,True);note(actor,"character_mesh_ignores")
        else: note(actor,"invalid_mesh_noops")
    else: note(actor,"non_character_skips")
    actor.call_function("Setup VFX");note(actor,"vfx_calls")
    system=ue.find_class("KismetSystemLibrary").get_cdo()
    handle=schedule(system,actor,"Detonate",float(actor.get_property("TimeBeforeExplode")));note(actor,"detonate_timers")
    actor.set_property("Timer",handle);note(actor,"timer_handle_writes")
    schedule(system,actor,"PostLaunchCleanup",.16);note(actor,"cleanup_timers")


class LyraGrenadeBeginPythonProfile:
    SetupVFX=ActionsPython.SetupVFX
    PostLaunchCleanup=ActionsPython.PostLaunchCleanup
    TeleportGrenade=ActionsPython.TeleportGrenade
    DestroyGrenade=ActionsPython.DestroyGrenade
    def ReceiveBeginPlay(self): begin(self)


class LyraGrenadeBeginBlueprintFallbackProfile:
    SetupVFX=ActionsBlueprint.SetupVFX
    PostLaunchCleanup=ActionsBlueprint.PostLaunchCleanup
    TeleportGrenade=ActionsBlueprint.TeleportGrenade
    DestroyGrenade=ActionsBlueprint.DestroyGrenade
    def ReceiveBeginPlay(self):
        note(self,"fallback_calls");return self.call_mixin_original("ReceiveBeginPlay")
