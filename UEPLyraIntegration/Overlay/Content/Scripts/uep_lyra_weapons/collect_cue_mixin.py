"""Original collect spline setup and native Timeline-driven movement/scale."""
import unreal_engine as ue
from .hero_burst_cue_mixin import lib
from . import collect_cue_lifecycle_mixin as lifetime
from uep_lyra_world.effect_pad_mixin import valid
CLASS=lifetime.CLASS
CREATE='UEPCollectCueCreateOriginalSpline'
TARGET='UEPCollectCuePrepareOriginalTarget'
ERROR='UEPCollectCuePrintOriginalInvalidPawn'
START='UEPCollectCueBeginOriginalTimeline'
UPDATE='UEPCollectCueTimelineUpdate'
FINISH='UEPCollectCueTimelineFinished'
def evidence(a):
    if not hasattr(a,'_uep_collect_cue'):a._uep_collect_cue=dict(python_play=0,fallback_play=0,python_update=0,fallback_update=0,python_finish=0,fallback_finish=0,invalid_pawn=0,diagnostic_fallbacks=0,last_curves=None,points=None)
    return a._uep_collect_cue
def bounds(actor,colliding):return actor.call_function('GetActorBounds',bOnlyCollidingComponents=colliding,bIncludeFromChildActors=False)
def play(a,MyTarget,Parameters):
    values=evidence(a);values['python_play']+=1;pawn=Parameters.Instigator;pawn=pawn if valid(pawn) and pawn.is_a(ue.find_class('Pawn')) else None;target=Parameters.EffectCauser;a.set_property('PawnWhoPickedUp',pawn);a.set_property('ActorToPickup',target);a.call_function(TARGET,target)
    if not valid(pawn):
        values['invalid_pawn']+=1;a.call_function(lifetime.GATE,0.);a.call_function('SetLifeSpan',0.);a.call_function(ERROR);return
    if not valid(target):values['diagnostic_fallbacks']+=1;return a.call_mixin_original('PlayPickup',MyTarget,Parameters)
    spline=a.call_function(CREATE);a.set_property('Spline_PickedUpAnim',spline);origin,extent=bounds(pawn,True);_,item_extent=bounds(target,False);start=target.call_function('K2_GetActorLocation');middle=ue.FVector(origin.x,origin.y,origin.z+extent.z+item_extent.z*.6);socket=a.get_property('In Socket Name');mesh=pawn.call_function('GetComponentByClass',ue.find_class('SkeletalMeshComponent'));no_socket=lib('KismetMathLibrary').call_function('EqualEqual_NameName',socket,'None');end=pawn.call_function('K2_GetActorLocation') if no_socket else mesh.call_function('GetSocketLocation',socket);points=[start,middle,end];values['points']=[[float(v.x),float(v.y),float(v.z)] for v in points];spline.call_function('SetSplinePoints',points,1,True);spline.call_function('K2_AttachToComponent',mesh,'None',1,1,1,True);timeline=a.get_property('ItemSuckUp');rate=lib('KismetMathLibrary').call_function('Divide_DoubleDouble',1.,float(a.get_property('SuckUpAnimTime')));timeline.call_function('SetPlayRate',rate);a.call_function(START)
def update(a,Position,Scale):
    values=evidence(a);values['python_update']+=1;values['last_curves']=[float(Position),float(Scale)]
    try:target=a.get_property('ActorToPickup');spline=a.get_property('Spline_PickedUpAnim')
    except Exception as error:
        if 'invalid state' not in str(error):raise
        values['diagnostic_fallbacks']+=1;return True
    if not valid(target) or not valid(spline):values['diagnostic_fallbacks']+=1;return True
    root=target.get_property('RootComponent');distance=lib('KismetMathLibrary').call_function('Lerp',0.,float(spline.call_function('GetSplineLength')),Position);location=spline.call_function('GetLocationAtDistanceAlongSpline',distance,1);root.call_function('K2_SetWorldLocation',NewLocation=location,bSweep=False,bTeleport=False);scale=lib('KismetMathLibrary').call_function('Lerp',0.,1.,Scale);root.call_function('SetWorldScale3D',ue.FVector(scale,scale,scale));return False
def finish(a):evidence(a)['python_finish']+=1;a.call_function('SetActorHiddenInGame',True);a.call_function(lifetime.GATE,3.);a.call_function('SetLifeSpan',3.);return False
def profile(name):
    methods={k:v for k,v in vars(getattr(lifetime,'LyraCollectCueLifecycle'+name+'Profile')).items() if not k.startswith('__')};fallback=name=='BlueprintFallback'
    def PlayPickup(self,MyTarget,Parameters):
        if fallback:evidence(self)['fallback_play']+=1;self.call_mixin_original('PlayPickup',MyTarget,Parameters)
        else:play(self,MyTarget,Parameters)
    def TimelineUpdate(self,Position,Scale):
        if fallback:evidence(self)['fallback_update']+=1;evidence(self)['last_curves']=[float(Position),float(Scale)];return True
        return update(self,Position,Scale)
    TimelineUpdate.override=UPDATE
    def TimelineFinished(self):
        if fallback:evidence(self)['fallback_finish']+=1;return True
        return finish(self)
    TimelineFinished.override=FINISH;methods.update(PlayPickup=PlayPickup,TimelineUpdate=TimelineUpdate,TimelineFinished=TimelineFinished);return methods
for name in ('Python','BlueprintFallback'):globals()['LyraCollectCue'+name+'Profile']=type('LyraCollectCue'+name+'Profile',(),profile(name))
