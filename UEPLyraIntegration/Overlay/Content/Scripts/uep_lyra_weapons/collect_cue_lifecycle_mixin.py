"""Pool-safe cleanup before the original collect Cue's self lifespan expires."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
CLASS='/ShooterMaps/GameplayCues/GC_Collect_Effect.GC_Collect_Effect_C'
GATE='UEPCollectCueScheduleNativeRecycle'
DEADLINE='UEPCollectCueNativeRecycleDeadline'
# Native timer ordering: finish and clear Actor::LifeSpanExpired just before
# the original lifespan deadline, within the same ordinary game frame.
DEADLINE_LEAD=.001
def evidence(a):
    if not hasattr(a,'_uep_collect_cue_lifecycle'):a._uep_collect_cue_lifecycle=dict(python_execute=0,fallback_execute=0,python_schedule=0,fallback_schedule=0,python_release=0,fallback_release=0,removed_splines=0,scheduled_seconds=[])
    return a._uep_collect_cue_lifecycle
def clean(a):
    for component in lib('LyraSystemStatics').call_function('FindComponentsByClass',a,ue.find_class('SplineComponent'),False):
        if valid(component) and component.call_function('GetOwner')==a:component.call_function('K2_DestroyComponent',a);evidence(a)['removed_splines']+=1
    a.set_property('Spline_PickedUpAnim',None)
def execute(a,target,params,prefix):
    evidence(a)[prefix+'_execute']+=1;clean(a);return a.call_mixin_original('OnExecute',target,params)
def schedule(a,Seconds,prefix):
    values=evidence(a);values[prefix+'_schedule']+=1;values['scheduled_seconds'].append(float(Seconds));lib('KismetSystemLibrary').call_function('K2_SetTimer',a,DEADLINE,max(0.,float(Seconds)-DEADLINE_LEAD),False,False,0.,0.);return True
def release(a,prefix):
    evidence(a)[prefix+'_release']+=1;clean(a);a.set_property('ActorToPickup',None);a.set_property('PawnWhoPickedUp',None);a.call_function('K2_EndGameplayCue')
def profile(prefix):
    def OnExecute(self,MyTarget,Parameters):return execute(self,MyTarget,Parameters,prefix)
    def Schedule(self,Seconds:float):return schedule(self,Seconds,prefix)
    Schedule.override=GATE
    def Deadline(self):release(self,prefix)
    Deadline.override=DEADLINE
    return dict(OnExecute=OnExecute,Schedule=Schedule,Deadline=Deadline)
for name,prefix in (('Python','python'),('BlueprintFallback','fallback')):globals()['LyraCollectCueLifecycle'+name+'Profile']=type('LyraCollectCueLifecycle'+name+'Profile',(),profile(prefix))
