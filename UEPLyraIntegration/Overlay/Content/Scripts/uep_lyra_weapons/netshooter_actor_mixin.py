"""Original net ray/strand/overlap policy; native physics, RPC, DoOnce and Delay."""
import unreal_engine as ue
from unreal_engine.structs import GameplayEffectContextHandle
from unreal_engine.enums import ETraceTypeQuery,EDrawDebugTrace
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs,break_hit

CLASS="/ShooterCore/Weapons/NetShooter_PROTO/B_NetShooter.B_NetShooter_C"
HIT="UEPNetShooterAfterNativeHitGate"
BODY="UEPNetShooterSpawnComponentsBody"
DELAY="UEPNetShooterBeginNativeLifeDelay"
AFTER="UEPNetShooterAfterNativeLifeDelay"
BIND="UEPNetShooterBindRayOverlap"
DAMAGE="/ShooterCore/Weapons/Rifle/GE_Damage_RifleAuto.GE_Damage_RifleAuto_C"


def lib(name):return ue.find_class(name).get_cdo()
def evidence(actor):
    value=getattr(actor,"_uep_netshooter_actor",None)
    if value is None:
        value={key:0 for key in ("hit_bodies","fallback_hit_bodies","traces","hits","rpc_requests","spawn_bodies","fallback_spawn_bodies",
            "components","hidden","native_overlap_binds","overlaps","fallback_overlaps","effect_requests","invalid_source_asc","native_life_delays","life_ends","fallback_life_ends")}
        actor._uep_netshooter_actor=value
    return value


def hit(actor,location,normal):
    row=evidence(actor);row["hit_bodies"]+=1;math=lib("KismetMathLibrary")
    start=math.call_function("Add_VectorVector",location,math.call_function("Multiply_VectorFloat",normal,float(actor.get_property("OffsetImpact"))))
    actor.set_property("Start",start)
    for _ in range(max(0,int(actor.get_property("NumberOfWeb"))+1)):
        jitter=math.call_function("MakeVector",*(float(math.call_function("RandomFloatInRange",-10.,10.)) for _ in range(3)))
        direction=math.call_function("Add_VectorVector",normal,jitter)
        end=math.call_function("Add_VectorVector",math.call_function("Multiply_VectorFloat",direction,float(actor.get_property("DistanceTrace"))),location)
        result=lib("KismetSystemLibrary").call_function("LineTraceSingle",WorldContextObject=actor,Start=start,End=end,TraceChannel=ETraceTypeQuery.TraceTypeQuery2,
            bTraceComplex=True,ActorsToIgnore=[],DrawDebugType=getattr(EDrawDebugTrace,"None"),bIgnoreSelf=True,
            TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=5.)
        fields=native_outputs("KismetSystemLibrary","LineTraceSingle",result);row["traces"]+=1
        if fields["ReturnValue"]:
            row["hits"]+=1;row["rpc_requests"]+=1;actor.call_function("SpawnComponents",fields["OutHit"])
    row["native_life_delays"]+=1;actor.call_function(DELAY)


def spawn(actor,result):
    row=evidence(actor);row["spawn_bodies"]+=1;parts=break_hit(result);math=lib("KismetMathLibrary")
    distance=float(math.call_function("Vector_Distance",parts["TraceStart"],parts["ImpactPoint"]))
    rotation=math.call_function("FindLookAtRotation",parts["TraceStart"],parts["TraceEnd"])
    transform=ue.FTransform(actor.get_actor_location(),rotation,math.call_function("MakeVector",distance,3.,3.))
    component=actor.call_function("AddComponent",TemplateName="NODE_AddStaticMeshComponent-0",bManualAttachment=True,RelativeTransform=transform,ComponentTemplateContext=None,bDeferredFinish=False)
    row["components"]+=1;sphere=actor.get_property("Sphere")
    if valid(sphere):sphere.call_function("SetHiddenInGame",True,False);row["hidden"]+=1
    if valid(component):actor.call_function(BIND,component);row["native_overlap_binds"]+=1


def overlap(actor,other):
    row=evidence(actor);row["overlaps"]+=1;gas=lib("AbilitySystemBlueprintLibrary")
    source=gas.call_function("GetAbilitySystemComponent",actor.call_function("GetInstigator"))
    target=gas.call_function("GetAbilitySystemComponent",other)
    if valid(source):
        source.call_function("BP_ApplyGameplayEffectToTarget",GameplayEffectClass=ue.load_class(DAMAGE),Target=target,Level=0.,Context=GameplayEffectContextHandle())
        row["effect_requests"]+=1
    else:row["invalid_source_asc"]+=1


class LyraNetShooterActorPythonProfile:
    def HitBody(self,HitLocation,HitNormal):hit(self,HitLocation,HitNormal)
    HitBody.override=HIT
    def SpawnBody(self,HitResult):spawn(self,HitResult)
    SpawnBody.override=BODY
    def OverlapRays(self,OverlappedComponent,OtherActor,OtherComp,OtherBodyIndex,bFromSweep,SweepResult):overlap(self,OtherActor)
    def LifeEnded(self):evidence(self)["life_ends"]+=1;self.call_function("K2_DestroyActor")
    LifeEnded.override=AFTER


class LyraNetShooterActorBlueprintFallbackProfile:
    def HitBody(self,HitLocation,HitNormal):evidence(self)["fallback_hit_bodies"]+=1;return self.call_mixin_original(HIT,HitLocation,HitNormal)
    HitBody.override=HIT
    def SpawnBody(self,HitResult):evidence(self)["fallback_spawn_bodies"]+=1;return self.call_mixin_original(BODY,HitResult)
    SpawnBody.override=BODY
    def OverlapRays(self,OverlappedComponent,OtherActor,OtherComp,OtherBodyIndex,bFromSweep,SweepResult):
        evidence(self)["fallback_overlaps"]+=1;return self.call_mixin_original("OverlapRays",OverlappedComponent,OtherActor,OtherComp,OtherBodyIndex,bFromSweep,SweepResult)
    def LifeEnded(self):evidence(self)["fallback_life_ends"]+=1;return self.call_mixin_original(AFTER)
    LifeEnded.override=AFTER
