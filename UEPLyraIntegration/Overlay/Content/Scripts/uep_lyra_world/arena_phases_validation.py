"""Observe default3/120/10s Arena flow and natural ServerTravel into a new round."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from .effect_pad_mixin import valid
from . import arena_phases_mixin as policy
from .arena_phases_contract import validate,phase_groups
CUE_CLASS='/TopDownArena/GameplayCues/GCN_GetReady.GCN_GetReady_C'
MODE_CLASS='/TopDownArena/Game/Modes/B_TopDownArena_GameComponent_Base.B_TopDownArena_GameComponent_Base_C'
def arg(n):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+n+'='))
def path(o):return o.get_path_name() if valid(o) else None
def frame():return int(policy.lib('KismetSystemLibrary').call_function('GetFrameCount'))
def game(o):return float(policy.lib('GameplayStatics').call_function('GetTimeSeconds',o))
class Validation:
    def __init__(self,result):
        self.path=Path(result);self.mode=arg('UEPArenaPhasesMode');self.started=time.monotonic();self.finished=False;self.roots=[];self.selectors={};self.last_sample=0.;self.last_notice=0.;self.cues={};self.report=dict(status='running',error=None,mode=self.mode,events=[],samples=[],last_postgame_seconds=0.,warmup_effect_with_registered_handles_observed=False,playing_warmup_effect_removed=False,natural_ready_widget_seen=False,natural_ready_widget_removed=False,default_durations=dict(warmup=3.,postgame=10.,round=120.))
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','callbacks_replayed','phases_started_by_fixture','round_properties_written','time_dilation_changed','native_delays_replaced','manual_travel_requested'):self.report[k]=False
        self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.cue_class=ue.load_class(CUE_CLASS);self.mode_class=ue.load_class(MODE_CLASS);self.effect_class=ue.load_class(policy.EFFECT)
        for cls in list(self.classes.values())+[self.cue_class,self.mode_class,self.effect_class]:
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
        if float(self.classes['warmup'].get_cdo().get_property('GetReadyTime'))!=3. or float(self.classes['postgame'].get_cdo().get_property('NewGameTime'))!=10.:raise RuntimeError('original default phase durations required')
        owner=self
        def observed(base,key,name):
            def call(a,*args):
                before=owner.record(a,key,name,'before');counts=policy.evidence(a);result=base(a,*args)
                # A native phase transition can retire this ability immediately.
                # Retain POD metadata and the Python counter dict before calling
                # production code; never dereference the retired UObject after.
                owner.report['events'].append(dict(before,stage='after',counts=copy.deepcopy(counts),real_seconds=time.monotonic()-owner.started,frame=frame(),metadata_captured_before_handler=True));return result
            if name=='AfterWait':call.override=policy.WARM_AFTER if key=='warmup' else policy.POST_AFTER
            return call
        for key,cls in self.classes.items():
            names=['K2_ActivateAbility']+(['K2_OnEndAbility'] if key!='postgame' else [])+(['ClearUserFacingCue','ActivateUserFacingCue'] if key=='warmup' else [])
            if self.mode=='Baseline':
                methods={}
                for name in names:
                    def original(a,*args,_name=name):return a.call_mixin_original(_name,*args)
                    methods[name]=observed(original,key,name)
                ue.register_mixin_profile(cls,'BaselineObserve',type('BaselineArenaPhase'+key,(),methods),make_default=True)
            else:
                self.selectors[key]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.mode);ue.register_declared_mixin(cls)
                if key!='playing':names.append('AfterWait')
                for name,source in self.sources(key).items():ue.register_mixin_profile(cls,name,type('ObservedArenaPhase'+key+name,(),{n:observed(getattr(source,n),key,n) for n in names}))
    def sources(self,key):
        cls={'warmup':'Warmup','playing':'Playing','postgame':'Postgame'}[key];return {name:getattr(policy,'LyraArena'+cls+name+'Profile') for name in ('Python','BlueprintFallback')}
    def record(self,a,key,name,stage):
        owning=a.call_function('GetOwningActorFromActorInfo');self.report['events'].append(dict(phase=key,method=name,stage=stage,ability=path(a),game_seconds=game(a),real_seconds=time.monotonic()-self.started,frame=frame(),authority=valid(owning) and int(owning.call_function('GetLocalRole'))==3,counts=copy.deepcopy(policy.evidence(a))))
        if name=='K2_ActivateAbility' and stage=='before':ue.log('UEP_ARENA_PHASES_ENTER '+key+' '+str(self.report['events'][-1]['game_seconds']))
        return self.report['events'][-1]
    def write(self):atomic_write(self.path,self.report)
    def sample(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'TopDown' not in world.get_name():continue
            state=policy.lib('GameplayStatics').call_function('GetGameState',world)
            if not valid(state):continue
            phases=policy.subsystem(world,'LyraGamePhaseSubsystem');system=policy.subsystem(world,'LyraGlobalAbilitySystem')
            if not valid(phases) or not valid(system):continue
            active={name:bool(phases.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.'+name))) for name in ('Warmup','Playing','PostGame')};effects=system.get_property('AppliedEffects');entry=effects.get(self.effect_class);handles=len(entry.Handles) if entry is not None else 0;seconds=game(world);mode=state.call_function('GetComponentByClass',self.mode_class)
            self.report['samples'].append(dict(game_seconds=seconds,frame=frame(),effect_present=entry is not None,handles=handles,**active));self.report['samples']=self.report['samples'][-800:]
            if active['Warmup'] and handles>=1:self.report['warmup_effect_with_registered_handles_observed']=True
            if active['Playing'] and entry is None:self.report['playing_warmup_effect_removed']=True
            if active['PostGame']:self.report['last_postgame_seconds']=max(self.report['last_postgame_seconds'],seconds)
            for cue in ue.tobject_iterator(self.cue_class):
                if not valid(cue) or cue.get_world()!=world:continue
                widget=cue.get_property('SpawnedWidget')
                if valid(widget) and widget.call_function('IsInViewport'):self.report['natural_ready_widget_seen']=True;self.cues[path(cue)]=True
                if active['Playing'] and path(cue) in self.cues and (not valid(widget) or not widget.call_function('IsInViewport')):self.report['natural_ready_widget_removed']=True
            if valid(mode) and active['Playing'] and not self.report.get('round_duration_observed'):
                server=float(state.call_function('GetServerWorldTimeSeconds'));left=float(mode.get_property('ServerWorld_GameEndTime'))-server
                if not 118.5<=left<=120.1:raise RuntimeError('original natural round must start with120 seconds')
                self.report['round_duration_observed']=True
    def tick(self,delta):
        if self.finished:return False
        try:
            now=time.monotonic()
            if now-self.started>270.:raise RuntimeError('default Arena cycle/restart observation timeout')
            if now-self.last_sample>=.2:self.last_sample=now;self.sample();self.write()
            activations=[e for e in self.report['events'] if e['method']=='K2_ActivateAbility' and e['stage']=='after']
            groups=phase_groups(activations)
            if [g[0]['phase'] for g in groups]==['warmup','playing','postgame','warmup'] and len(groups[-1])>=2:self.finish();return False
            if now-self.last_notice>=30.:self.last_notice=now;ue.log('UEP_ARENA_PHASES_OBSERVING '+str(round(now-self.started,1))+'s')
            return True
        except Exception:self.finish(traceback.format_exc());return False
    def cleanup(self):
        for key,cls in self.classes.items():
            if self.mode=='Baseline':ue.unregister_mixin(cls)
            else:
                for name,source in self.sources(key).items():ue.register_mixin_profile(cls,name,source)
                cls.get_cdo().set_property('PythonMixinProfile',self.selectors[key])
        self.report['selectors_restored']=all(self.classes[k].get_cdo().get_property('PythonMixinProfile')==v for k,v in self.selectors.items())
        for cls in reversed(self.roots):cls.remove_from_root()
        self.report['all_classes_unrooted']=all(not cls.is_rooted() for cls in self.roots);self.report['cleanup_complete']=self.report['selectors_restored'] and self.report['all_classes_unrooted']
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ARENA_PHASES_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_PHASES_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaPhasesResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
