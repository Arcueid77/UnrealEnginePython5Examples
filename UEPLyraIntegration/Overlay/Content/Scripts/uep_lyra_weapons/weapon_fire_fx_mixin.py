"""Original shell/muzzle/tracer cache and trigger decisions, native Niagara."""
import unreal_engine as ue
from unreal_engine.enums import EAttachLocation,ENCPoolMethod,ERelativeTransformSpace
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs

CLASS="/Game/Effects/Blueprints/B_WeaponFire.B_WeaponFire_C"
DELAY="UEPWeaponFireBeginNativeDelay"
AFTER="UEPWeaponFireAfterNativeDelay"
STAGES=(("Enable Shell Eject","NS_ShellEject","Shell Eject System","Shell Eject Trigger","ShellEject"),
        ("Enable Muzzle Flash","NS_MuzzleFlash","Muzzle Flash System","Muzzle Flash Trigger","Muzzle"),
        ("Enable Tracer","NS_Tracer","Tracer System","Tracer Trigger","Muzzle"))


def lib(name):return ue.find_class(name).get_cdo()


def evidence(actor):
    value=getattr(actor,"_uep_weapon_fire_fx",None)
    if value is None:
        value=dict(python_calls=0,fallback_calls=0,enabled=0,spawns=0,reuses=0,trigger_writes=0,invalid_components=0,
            shell_mesh_writes=0,direction_writes=0,impact_array_writes=0,native_delay_requests=0,python_cleanup=0,fallback_cleanup=0,cleanup_repeats=0,destroys=0)
        actor._uep_weapon_fire_fx=value
    return value


def socket(actor,name,space):
    mesh=actor.get_property("Skeletal Mesh Component")
    if not valid(mesh):return ue.FVector()
    transform=mesh.call_function("GetSocketTransform",name,space)
    return native_outputs("KismetMathLibrary","BreakTransform",lib("KismetMathLibrary").call_function("BreakTransform",transform))["Location"]


def fire(actor):
    counts=evidence(actor);counts["python_calls"]+=1
    for index,(flag,field,system,trigger,socket_name) in enumerate(STAGES):
        if not actor.get_property(flag):continue
        counts["enabled"]+=1;component=actor.get_property(field)
        if not valid(component) or not component.call_function("IsActive"):
            component=lib("NiagaraFunctionLibrary").call_function("SpawnSystemAttached",SystemTemplate=actor.get_property(system),
                AttachToComponent=actor.get_property("DefaultSceneRoot"),AttachPointName="None",
                Location=socket(actor,socket_name,ERelativeTransformSpace.RTS_Actor),Rotation=ue.FRotator(0.,0.,90.),
                LocationType=EAttachLocation.KeepRelativeOffset,bAutoDestroy=True,bAutoActivate=True,
                PoolingMethod=getattr(ENCPoolMethod,"None"),bPreCullCheck=True)
            counts["spawns"]+=1;actor.set_property(field,component)
            if index==0 and valid(component):
                component.call_function("SetVariableStaticMesh","User.ShellEjectStaticMesh",actor.get_property("Shell Eject Mesh"));counts["shell_mesh_writes"]+=1
            actor.set_property(trigger,False)
        else:counts["reuses"]+=1
        actor.set_property(trigger,not bool(actor.get_property(trigger)));counts["trigger_writes"]+=1
        if not valid(component):counts["invalid_components"]+=1;continue
        component.call_function("SetVariableBool","User.Trigger",actor.get_property(trigger))
        if index==1:
            positions=list(actor.get_property("ImpactPositions"))
            point=positions[0] if positions else ue.FVector()
            direction=lib("KismetMathLibrary").call_function("Normal",lib("KismetMathLibrary").call_function("Subtract_VectorVector",point,
                socket(actor,"Muzzle",ERelativeTransformSpace.RTS_World)),.0001)
            component.call_function("SetVariableVec3","User.Direction",direction);counts["direction_writes"]+=1
        elif index==2:
            lib("NiagaraDataInterfaceArrayFunctionLibrary").call_function("SetNiagaraArrayVector",component,"User.ImpactPositions",actor.get_property("ImpactPositions"))
            counts["impact_array_writes"]+=1
    counts["native_delay_requests"]+=1;actor.call_function(DELAY)


def cleanup(actor):
    counts=evidence(actor);counts["python_cleanup"]+=1
    # The source graph deliberately checks validity, not active simulation.
    if any(valid(actor.get_property(field)) for _,field,_,_,_ in STAGES):
        counts["cleanup_repeats"]+=1;counts["native_delay_requests"]+=1;actor.call_function(DELAY)
    else:counts["destroys"]+=1;actor.call_function("K2_DestroyActor")


class LyraWeaponFireFXPythonProfile:
    def Fire(self):fire(self)
    def AfterDelay(self):cleanup(self)
    AfterDelay.override=AFTER


class LyraWeaponFireFXBlueprintFallbackProfile:
    def Fire(self):
        evidence(self)["fallback_calls"]+=1;return self.call_mixin_original("Fire")
    def AfterDelay(self):
        evidence(self)["fallback_cleanup"]+=1;return self.call_mixin_original(AFTER)
    AfterDelay.override=AFTER
