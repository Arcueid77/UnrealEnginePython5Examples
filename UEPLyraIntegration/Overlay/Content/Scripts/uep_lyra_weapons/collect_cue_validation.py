"""Real manager executions and native Timeline samples; no callback replay."""
import atexit,copy,json,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from .hero_burst_cue_mixin import lib
from . import collect_cue_mixin as policy,collect_cue_lifecycle_mixin as lifetime
from .collect_cue_contract import FALSE_FIELDS,CASES,require,validate
def path(v):return v.get_path_name() if valid(v) else None
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def near(a,b,tol=.02):return len(a)==len(b) and all(abs(x-y)<=tol for x,y in zip(a,b))
def total(a,key):return sum(policy.evidence(a)[p+'_'+key] for p in ('python','fallback'))
class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.profile_index=0;self.case_index=0;self.actors=[];self.cues=[];self.selector=None;self.rooted=False
    def params(self,pawn,target):return lib('AbilitySystemBlueprintLibrary').call_function('MakeGameplayCueParameters',NormalizedMagnitude=0.,RawMagnitude=0.,EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),AggregatedTargetTags=GameplayTagContainer(),Location=ue.FVector(),Normal=ue.FVector(),Instigator=pawn,EffectCauser=target,SourceObject=target,PhysicalMaterial=None,GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.transform_before=[vec(self.pawn.get_actor_location()),vec(self.pawn.get_property('RootComponent').call_function('K2_GetComponentScale'))];self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');self.duration_before=self.cls.get_cdo().get_property('SuckUpAnimTime');self.socket_before=self.cls.get_cdo().get_property('In Socket Name');self.rooted=self.cls.is_rooted()
        if not self.rooted:self.cls.add_to_root()
        author=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPCollectCueAuthoring=')));proof=json.loads((author/'assets.json').read_text(encoding='utf-8-sig'));self.curves={name:ue.load_object(ue.find_class('CurveFloat'),path) for name,path in proof['curve_paths'].items()};self.report['native_cue_recycling_and_timer_cleanup_enabled']=all(lib('KismetSystemLibrary').call_function('GetConsoleVariableIntValue',name)>0 for name in ('AbilitySystem.GameplayCueActorRecycle','AbilitySystem.ClearCueNotifyTimers'));self.start_case()
    def start_case(self):
        self.profile=('BlueprintFallback','Python')[self.profile_index];self.spec=CASES[self.case_index];name,duration,socket,switch=self.spec;self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.cls.get_cdo().set_property('SuckUpAnimTime',duration);self.cls.get_cdo().set_property('In Socket Name',socket)
        for cue in self.cues:
            if valid(cue):ue.set_mixin_profile(cue,self.profile);cue.set_property('SuckUpAnimTime',duration);cue.set_property('In Socket Name',socket)
        self.target=self.world.actor_spawn(ue.find_class('StaticMeshActor'));self.actors.append(self.target);mesh=self.target.get_property('StaticMeshComponent');mesh.call_function('SetMobility',2);mesh.call_function('SetStaticMesh',ue.load_object(ue.find_class('StaticMesh'),'/Engine/BasicShapes/Cube.Cube'));center=self.pawn.get_actor_location();self.target.call_function('K2_SetActorLocation',NewLocation=ue.FVector(center.x+150.,center.y+60.,center.z+20.),bSweep=False,bTeleport=True);self.target.call_function('SetActorScale3D',ue.FVector(.4,.7,1.2));origin,extent=policy.bounds(self.pawn,True);_,item_extent=policy.bounds(self.target,False);end=self.pawn.call_function('K2_GetActorLocation') if socket=='None' else self.pawn.call_function('GetComponentByClass',ue.find_class('SkeletalMeshComponent')).call_function('GetSocketLocation',socket);self.expected_points=[vec(self.target.get_actor_location()),[origin.x,origin.y,origin.z+extent.z+item_extent.z*.6],vec(end)];self.before={path(a):copy.deepcopy(policy.evidence(a)) for a in self.cues if valid(a)};self.row=dict(profile=self.profile,name=name,samples=0,all_samples_match_native_spline_distance_and_uniform_scale=True,all_samples_match_original_native_curves=True);self.report['cases'].append(self.row);self.started_case=self.game_time();self.param=self.params(self.controller if name=='invalid-pawn' else self.pawn,self.target);lib('GameplayCueFunctionLibrary').call_function('ExecuteGameplayCueOnActor',self.pawn,GameplayTag(TagName='GameplayCue.ShooterGame.Interact.Collect'),self.param);self.cue=None;self.switched=False;self.enter('locate')
    def observe(self):
        require(time.monotonic()-self.phase_started<12.,'collect Cue phase timeout: '+self.phase)
        if self.phase=='locate':
            candidates=[a for a in ue.tobject_iterator(self.cls) if valid(a) and a.call_function('GetOwner')==self.pawn and a.get_property('ActorToPickup')==self.target]
            if not candidates:return
            self.cue=candidates[-1]
            if self.cue not in self.cues:self.cues.append(self.cue)
            self.old=self.before.get(path(self.cue),dict(python_play=0,fallback_play=0,python_update=0,fallback_update=0,python_finish=0,fallback_finish=0));self.row['native_manager_executed_exact_class']=total(self.cue,'play')-sum(self.old[p+'_play'] for p in ('python','fallback'))==1;self.row['source_target_collision_and_lifespan_set']=not self.target.call_function('GetActorEnableCollision') and 0.<self.target.call_function('GetLifeSpan')<=3.;self.timeline=self.cue.get_property('ItemSuckUp')
            if self.spec[0]=='invalid-pawn':self.row.update(invalid_pawn_no_timeline=not self.timeline.call_function('IsPlaying') and total(self.cue,'finish')-sum(self.old[p+'_finish'] for p in ('python','fallback'))==0,self_lifespan_cleared=self.cue.call_function('GetLifeSpan')==0.);self.explicit_retire();return
            spline=self.cue.get_property('Spline_PickedUpAnim');self.spline=spline;points=[vec(spline.call_function('GetLocationAtSplinePoint',i,1)) for i in range(3)];mesh=self.pawn.call_function('GetComponentByClass',ue.find_class('SkeletalMeshComponent'));self.row['original_spline_points_and_world_attachment_match']=all(near(a,b) for a,b in zip(points,self.expected_points)) and spline.call_function('GetAttachParent')==mesh;expected_rate=0. if self.spec[1]==0 else 1./self.spec[1];self.row['native_play_rate_matches_source']=abs(self.timeline.call_function('GetPlayRate')-expected_rate)<.001;self.row['native_timeline_length']=float(self.timeline.call_function('GetTimelineLength'));self.row['owned_target_lifespan_extended_for_long_timeline']=self.row['native_timeline_length']*self.spec[1]>=2.9
            if self.row['owned_target_lifespan_extended_for_long_timeline']:self.target.call_function('SetLifeSpan',0.)
            self.enter('timeline')
        elif self.phase=='timeline':
            values=policy.evidence(self.cue);curves=values['last_curves']
            if curves is not None and total(self.cue,'update')>sum(self.old[p+'_update'] for p in ('python','fallback')):
                position,scale=curves;distance=self.spline.call_function('GetSplineLength')*position;expected=vec(self.spline.call_function('GetLocationAtDistanceAlongSpline',distance,1));root=self.target.get_property('RootComponent');self.row['all_samples_match_native_spline_distance_and_uniform_scale'] &=near(vec(root.call_function('K2_GetComponentLocation')),expected) and near(vec(root.call_function('K2_GetComponentScale')),[scale]*3,.001);clock=self.timeline.call_function('GetPlaybackPosition');self.row['all_samples_match_original_native_curves'] &=abs(position-self.curves['NewTrack_0'].call_function('GetFloatValue',clock))<.001 and abs(scale-self.curves['ItemScale'].call_function('GetFloatValue',clock))<.001;self.row['samples']+=1
            if self.spec[3] and not self.switched and self.timeline.call_function('GetPlaybackPosition')>.2:ue.set_mixin_profile(self.cue,'Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback');self.switched=True
            if self.spec[0]=='zero-rate':
                if time.monotonic()-self.phase_started<.2:return
                self.row['zero_rate_preserves_stalled_native_timeline']=self.timeline.call_function('IsPlaying') and self.timeline.call_function('GetPlaybackPosition')==0. and total(self.cue,'finish')-sum(self.old[p+'_finish'] for p in ('python','fallback'))==0;self.timeline.call_function('Stop');self.explicit_retire();return
            finished=total(self.cue,'finish')-sum(self.old[p+'_finish'] for p in ('python','fallback'))
            if finished!=1:return
            self.row.update(actual_native_update_count=total(self.cue,'update')-sum(self.old[p+'_update'] for p in ('python','fallback')),native_finish_count=finished,native_finished_hides_then_retains_self_three_seconds=bool(self.cue.get_property('bHidden')) and 2.8<=self.cue.call_function('GetLifeSpan')<=3.)
            expected_profile='Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback';prefix='python' if (expected_profile if self.spec[3] else self.profile)=='Python' else 'fallback';self.row['pending_profile_switch_used_current_update_and_finish']=values[prefix+'_finish']-self.old[prefix+'_finish']==1 and (not self.spec[3] or self.switched);self.enter('pool')
        elif self.phase=='pool':
            require(valid(self.cue),'collect Cue destroyed instead of pooled')
            if self.cue.call_function('GetOwner') is not None:return
            self.after_retire()
    def explicit_retire(self):
        lifetime.clean(self.cue);self.cue.set_property('ActorToPickup',None);self.cue.set_property('PawnWhoPickedUp',None);self.cue.call_function('K2_EndGameplayCue');self.after_retire()
    def after_retire(self):
        self.row['pool_actor_alive_hidden_ownerless_and_resource_free']=valid(self.cue) and bool(self.cue.get_property('bHidden')) and self.cue.call_function('GetOwner') is None and self.cue.call_function('GetLifeSpan')==0. and not lib('LyraSystemStatics').call_function('FindComponentsByClass',self.cue,ue.find_class('SplineComponent'),False)
        if valid(self.target):self.target.actor_destroy()
        self.case_index+=1
        if self.case_index==len(CASES):self.case_index=0;self.profile_index+=1
        if self.profile_index<2:self.start_case()
        else:self.finish()
    def cleanup(self):
        for a in self.cues:
            if valid(a):
                a.get_property('ItemSuckUp').call_function('Stop');lifetime.clean(a);a.call_function('K2_EndGameplayCue');ue.clear_mixin_profile(a)
        for a in self.actors:
            if valid(a):a.actor_destroy()
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector);self.cls.get_cdo().set_property('SuckUpAnimTime',self.duration_before);self.cls.get_cdo().set_property('In Socket Name',self.socket_before)
        if not self.rooted:self.cls.remove_from_root()
        self.report['owned_actor_roots_and_class_selectors_restored']=all(not valid(a) for a in self.actors) and (self.rooted or not self.cls.is_rooted()) and self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector and self.cls.get_cdo().get_property('SuckUpAnimTime')==self.duration_before and self.cls.get_cdo().get_property('In Socket Name')==self.socket_before;self.report['primary_player_inventory_health_and_transform_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before and self.transform_before==[vec(self.pawn.get_actor_location()),vec(self.pawn.get_property('RootComponent').call_function('K2_GetComponentScale'))]
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<360.,'collect Cue readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_COLLECT_CUE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_COLLECT_CUE_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPCollectCueResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
