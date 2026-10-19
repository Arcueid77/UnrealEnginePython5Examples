"""Original decal cache/trigger/array policy; Niagara and latent actions stay native."""
import unreal_engine as ue
from unreal_engine.enums import ENCPoolMethod
from uep_lyra_world.effect_pad_mixin import valid

CLASS="/Game/Effects/Blueprints/B_WeaponDecals.B_WeaponDecals_C"
DELAY="UEPWeaponDecalsBeginNativeDelay"
AFTER="UEPWeaponDecalsAfterNativeDelay"


def lib(name):return ue.find_class(name).get_cdo()


def evidence(actor):
    value=getattr(actor,"_uep_weapon_decals",None)
    if value is None:
        value=dict(python_calls=0,fallback_calls=0,spawns=0,reuses=0,trigger_writes=0,surface_elements=0,
            native_parameter_batches=0,invalid_components=0,native_delay_requests=0,python_cleanup=0,
            fallback_cleanup=0,cleanup_repeats=0,destroys=0)
        actor._uep_weapon_decals=value
    return value


def fire(actor):
    counts=evidence(actor);counts["python_calls"]+=1;component=actor.get_property("Decal")
    if not valid(component) or not component.call_function("IsActive"):
        component=lib("NiagaraFunctionLibrary").call_function("SpawnSystemAtLocation",WorldContextObject=actor,
            SystemTemplate=actor.get_property("Decal System"),Location=ue.FVector(),Rotation=ue.FRotator(),Scale=ue.FVector(1.,1.,1.),
            bAutoDestroy=True,bAutoActivate=True,PoolingMethod=getattr(ENCPoolMethod,"None"),bPreCullCheck=True)
        counts["spawns"]+=1;actor.set_property("Decal",component);actor.set_property("Impact Trigger",False)
    else:counts["reuses"]+=1
    trigger=not bool(actor.get_property("Impact Trigger"));actor.set_property("Impact Trigger",trigger);counts["trigger_writes"]+=1
    if valid(component):component.call_function("SetVariableBool","User.Trigger",trigger)
    # BP Array_Set(bSizeToFit=True) overwrites/grows but never truncates the tail.
    surfaces=list(actor.get_property("Surface Types"))
    for index,value in enumerate(actor.get_property("Impact Surface Types")):
        if index==len(surfaces):surfaces.append(int(value))
        else:surfaces[index]=int(value)
        counts["surface_elements"]+=1
    actor.set_property("Surface Types",surfaces)
    if valid(component):
        arrays=lib("NiagaraDataInterfaceArrayFunctionLibrary")
        arrays.call_function("SetNiagaraArrayInt32",component,"User.ImpactSurfaces",surfaces)
        arrays.call_function("SetNiagaraArrayPosition",component,"User.ImpactPositions",actor.get_property("ImpactPositions"))
        arrays.call_function("SetNiagaraArrayVector",component,"User.ImpactNormals",actor.get_property("ImpactNormals"))
        component.call_function("SetVariableInt","User.NumberOfHits",len(actor.get_property("ImpactPositions")))
        counts["native_parameter_batches"]+=1
    else:counts["invalid_components"]+=1
    counts["native_delay_requests"]+=1;actor.call_function(DELAY)


def cleanup(actor):
    counts=evidence(actor);counts["python_cleanup"]+=1
    if valid(actor.get_property("Decal")):
        counts["cleanup_repeats"]+=1;counts["native_delay_requests"]+=1;actor.call_function(DELAY)
    else:counts["destroys"]+=1;actor.call_function("K2_DestroyActor")


class LyraWeaponDecalsPythonProfile:
    def Fire(self):fire(self)
    Fire.override="fire"
    def AfterDelay(self):cleanup(self)
    AfterDelay.override=AFTER


class LyraWeaponDecalsBlueprintFallbackProfile:
    def Fire(self):
        evidence(self)["fallback_calls"]+=1;return self.call_mixin_original("fire")
    Fire.override="fire"
    def AfterDelay(self):
        evidence(self)["fallback_cleanup"]+=1;return self.call_mixin_original(AFTER)
    AfterDelay.override=AFTER
