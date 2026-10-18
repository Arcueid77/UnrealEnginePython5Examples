"""Retained Actor teleport/destroy decisions; native location/component APIs."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .grenade_cleanup_mixin import LyraGrenadeCleanupPythonProfile as BasePython,LyraGrenadeCleanupBlueprintFallbackProfile as BaseBlueprint

TELEPORT="Teleport Grenade"
DESTROY="Destroy Grenade"


def evidence(actor):
    row=getattr(actor,"_uep_grenade_actions",None)
    if row is None:
        row=dict(teleport_python=0,teleport_fallback=0,speed_reads=0,conserved_writes=0,missing_movement_reads=0,
            invalid_trail_noops=0,trail_deactivations=0,native_locations=0,movement_activations=0,velocity_writes=0,
            missing_movement_writes=0,vfx_calls=0,destroy_python=0,destroy_fallback=0,native_destroy_calls=0)
        actor._uep_grenade_actions=row
    return row
def note(actor,key): evidence(actor)[key]+=1


def teleport(actor,location,forward):
    note(actor,"teleport_python");math=ue.find_class("KismetMathLibrary").get_cdo();movement=actor.get_property("ProjectileMovement")
    if valid(movement): velocity=movement.get_property("Velocity");note(actor,"speed_reads")
    else: velocity=ue.FVector();note(actor,"missing_movement_reads")
    actor.set_property("ConservedVelocity",math.call_function("VSize",velocity));note(actor,"conserved_writes")
    trail=actor.get_property("NS_Trail")
    if not valid(trail): note(actor,"invalid_trail_noops");return
    trail.call_function("Deactivate");note(actor,"trail_deactivations")
    actor.call_function("K2_SetActorLocation",NewLocation=location,bSweep=False,bTeleport=True);note(actor,"native_locations") # Return intentionally ignored.
    movement=actor.get_property("ProjectileMovement")
    if valid(movement):
        movement.call_function("Activate",True);note(actor,"movement_activations")
        half=math.call_function("Divide_DoubleDouble",actor.get_property("ConservedVelocity"),2.)
        # Original forward input is NOT normalized. Promotable operator B is
        # scalar despite its historical Multiply_VectorVector FunctionRef.
        movement.set_property("Velocity",math.call_function("Multiply_VectorFloat",forward,half));note(actor,"velocity_writes")
    else: note(actor,"missing_movement_writes")
    actor.call_function("Setup VFX");note(actor,"vfx_calls")


class LyraGrenadeActionsPythonProfile:
    SetupVFX=BasePython.SetupVFX
    PostLaunchCleanup=BasePython.PostLaunchCleanup
    def TeleportGrenade(self,TeleportLocation,TeleportForward): teleport(self,TeleportLocation,TeleportForward)
    TeleportGrenade.override=TELEPORT
    def DestroyGrenade(self,PSystem):
        note(self,"destroy_python");note(self,"native_destroy_calls");self.call_function("K2_DestroyActor")
    DestroyGrenade.override=DESTROY


class LyraGrenadeActionsBlueprintFallbackProfile:
    SetupVFX=BaseBlueprint.SetupVFX
    PostLaunchCleanup=BaseBlueprint.PostLaunchCleanup
    def TeleportGrenade(self,TeleportLocation,TeleportForward):
        note(self,"teleport_fallback");return self.call_mixin_original(TELEPORT,TeleportLocation,TeleportForward)
    TeleportGrenade.override=TELEPORT
    def DestroyGrenade(self,PSystem):
        note(self,"destroy_fallback");return self.call_mixin_original(DESTROY,PSystem)
    DestroyGrenade.override=DESTROY
