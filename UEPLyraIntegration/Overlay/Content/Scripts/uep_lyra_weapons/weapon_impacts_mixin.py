"""Original impact bucketing/spawn policy; native Niagara, Data Channels and latent node."""
import unreal_engine as ue
from unreal_engine.enums import ENCPoolMethod
from unreal_engine.structs import NiagaraDataChannelSearchParameters
from uep_lyra_world.effect_pad_mixin import valid

CLASS="/Game/Effects/Blueprints/B_WeaponImpacts.B_WeaponImpacts_C"
STRUCT="/Game/Effects/Blueprints/SurfaceImpacts.SurfaceImpacts"
CHANNEL="/Game/Effects/DataChannels/ImpactDataChannel.ImpactDataChannel"
POSITIONS="ImpactPositions_6_4DAE749E4058967754F0BB873262A3B7"
NORMALS="ImpcatNormals_5_E3297B4A4DE28BD6A85D8EA46FD6060A"
DELAY="UEPWeaponImpactsBeginNativeDelay"
AFTER="UEPWeaponImpactsAfterNativeDelay"
METHODS=("Fire","AddImpactsToBuckets","SpawnParticlesFromImpacts","SpawnFromArrays","SpawnFromDataChannels",AFTER)
TEMPLATES=("Default","Character","Concrete","Glass")


def lib(name):return ue.find_class(name).get_cdo()


def evidence(actor):
    value=getattr(actor,"_uep_weapon_impacts",None)
    if value is None:
        value={name:0 for name in ("python_calls","fallback_calls","bucket_calls","selector_calls","array_calls","channel_calls",
            "spawns","reuses","invalid_templates","invalid_components","native_array_batches","native_channel_rows",
            "native_delay_requests","python_cleanup","fallback_cleanup","cleanup_repeats","destroys")}
        actor._uep_weapon_impacts=value
    return value


def bucket(points=(),normals=()):
    value=ue.load_struct(STRUCT)();value.set_field(POSITIONS,list(points));value.set_field(NORMALS,list(normals));return value


def fields(value):return list(value.get_field(POSITIONS)),list(value.get_field(NORMALS))
def at(values,index):return values[index] if 0<=index<len(values) else ue.FVector()
def surface_bucket(actor,surface):
    buckets=list(actor.get_property("ImpactBuckets"))
    return fields(buckets[surface]) if 0<=surface<len(buckets) else ([],[])


def add_impacts(actor):
    evidence(actor)["bucket_calls"]+=1
    # Array elements are borrowed UScriptStruct views. Detach them before the
    # property setter clears/reallocates the native array during writeback.
    buckets=[value.clone() for value in actor.get_property("ImpactBuckets")]
    for value in buckets:value.set_field(POSITIONS,[]);value.set_field(NORMALS,[])
    points=list(actor.get_property("ImpactPositions"));normals=list(actor.get_property("ImpactNormals"))
    for index,surface in enumerate(actor.get_property("ImpactSurfaceTypes")):
        surface=int(surface)
        while len(buckets)<=surface:buckets.append(bucket())
        positions,directions=fields(buckets[surface]);positions.append(at(points,index));directions.append(at(normals,index))
        buckets[surface].set_field(POSITIONS,positions);buckets[surface].set_field(NORMALS,directions)
    actor.set_property("ImpactBuckets",buckets)


def select_spawns(actor):
    evidence(actor)["selector_calls"]+=1
    for index,value in enumerate(actor.get_property("ImpactBuckets")):
        points,normals=fields(value)
        if not points or not normals:continue
        surface=index&255
        method="SpawnFromDataChannels" if actor.get_property("Use Data Channels") and surface in (2,3) else "SpawnFromArrays"
        actor.call_function(method,surface)


def spawn_arrays(actor,surface):
    counts=evidence(actor);counts["array_calls"]+=1;surface=int(surface)
    template=actor.get_property(TEMPLATES[surface]) if 0<=surface<len(TEMPLATES) else None
    if not valid(template):counts["invalid_templates"]+=1;return
    points,normals=surface_bucket(actor,surface);position=at(points,0)
    systems=list(actor.get_property("Impact Systems"));component=systems[surface] if 0<=surface<len(systems) else None
    # The authored branch reuses a valid component only when distance is GREATER
    # than threshold squared. It tests neither IsActive nor template equality.
    threshold=float(actor.get_property("Distance Threshold"));reuse=False
    if valid(component):
        distance=lib("KismetMathLibrary").call_function("Vector_DistanceSquared",position,component.call_function("K2_GetComponentLocation"))
        reuse=float(distance)>threshold*threshold
    if reuse:counts["reuses"]+=1
    else:
        component=lib("NiagaraFunctionLibrary").call_function("SpawnSystemAtLocation",WorldContextObject=actor,SystemTemplate=template,
            Location=position,Rotation=ue.FRotator(),Scale=ue.FVector(1.,1.,1.),bAutoDestroy=True,bAutoActivate=True,
            PoolingMethod=getattr(ENCPoolMethod,"None"),bPreCullCheck=True)
        counts["spawns"]+=1
        while len(systems)<=surface:systems.append(None)
        systems[surface]=component;actor.set_property("Impact Systems",systems)
    if not valid(component):counts["invalid_components"]+=1;return
    component.call_function("K2_SetWorldLocation",NewLocation=position,bSweep=False,bTeleport=False)
    arrays=lib("NiagaraDataInterfaceArrayFunctionLibrary")
    arrays.call_function("SetNiagaraArrayPosition",component,"User.ImpactPositions",points)
    component.call_function("SetVariableInt","NumberOfHits",len(points))
    arrays.call_function("SetNiagaraArrayVector",component,"User.ImpactNormals",normals)
    component.call_function("SetVariablePosition","User.MuzzlePosition",actor.get_property("MuzzlePosition"))
    component.call_function("Activate",False);counts["native_array_batches"]+=1


def spawn_channel(actor,surface):
    counts=evidence(actor);counts["channel_calls"]+=1;surface=int(surface);points,normals=surface_bucket(actor,surface)
    search=NiagaraDataChannelSearchParameters(OwningComponent=actor.get_property("DefaultSceneRoot"),Location=at(points,0),bOverrideLocation=True)
    writer=lib("NiagaraDataChannelLibrary").call_function("WriteToNiagaraDataChannel",WorldContextObject=actor,
        Channel=ue.load_object(ue.find_class("NiagaraDataChannelAsset"),CHANNEL),SearchParams=search,Count=len(points),
        bVisibleToGame=True,bVisibleToCPU=True,bVisibleToGPU=True,DebugSource="")
    if not valid(writer):return
    for index,point in enumerate(points):
        writer.call_function("WritePosition","ImpactPosition",index,point)
        writer.call_function("WriteVector","ImpactNormal",index,at(normals,index))
        writer.call_function("WritePosition","MuzzlePosition",index,actor.get_property("MuzzlePosition"))
        writer.call_function("WriteEnum","ImpactSurface",index,surface);counts["native_channel_rows"]+=1


def fire(actor):
    counts=evidence(actor);counts["python_calls"]+=1
    actor.call_function("AddImpactsToBuckets");actor.call_function("SpawnParticlesFromImpacts")
    for field in ("ImpactPositions","ImpactNormals","ImpactSurfaceTypes"):actor.set_property(field,[])
    counts["native_delay_requests"]+=1;actor.call_function(DELAY)


def cleanup(actor):
    counts=evidence(actor);counts["python_cleanup"]+=1;actor.set_property("Has Valid Systems",False)
    for component in actor.get_property("Impact Systems"):
        if valid(component):actor.set_property("Has Valid Systems",True)
    if actor.get_property("Has Valid Systems"):
        counts["cleanup_repeats"]+=1;counts["native_delay_requests"]+=1;actor.call_function(DELAY)
    else:counts["destroys"]+=1;actor.call_function("K2_DestroyActor")


class LyraWeaponImpactsPythonProfile:
    def Fire(self):fire(self)
    def AddImpactsToBuckets(self):add_impacts(self)
    def SpawnParticlesFromImpacts(self):select_spawns(self)
    def SpawnFromArrays(self,SurfaceType):spawn_arrays(self,SurfaceType)
    def SpawnFromDataChannels(self,SurfaceType):spawn_channel(self,SurfaceType)
    def AfterDelay(self):cleanup(self)
    AfterDelay.override=AFTER


class LyraWeaponImpactsBlueprintFallbackProfile:
    def Fire(self):
        evidence(self)["fallback_calls"]+=1;return self.call_mixin_original("Fire")
    def AddImpactsToBuckets(self):return self.call_mixin_original("AddImpactsToBuckets")
    def SpawnParticlesFromImpacts(self):return self.call_mixin_original("SpawnParticlesFromImpacts")
    def SpawnFromArrays(self,SurfaceType):return self.call_mixin_original("SpawnFromArrays",SurfaceType)
    def SpawnFromDataChannels(self,SurfaceType):return self.call_mixin_original("SpawnFromDataChannels",SurfaceType)
    def AfterDelay(self):
        evidence(self)["fallback_cleanup"]+=1;return self.call_mixin_original(AFTER)
    AfterDelay.override=AFTER
