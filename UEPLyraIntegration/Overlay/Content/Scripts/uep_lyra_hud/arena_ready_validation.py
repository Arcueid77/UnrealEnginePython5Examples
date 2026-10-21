"""Observe actual Arena warmup/Cue construction before and after widget migration."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from . import cue_widget_mixin as cue,arena_ready_mixin as policy
from .arena_ready_contract import validate

def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def path(obj):return obj.get_path_name() if valid(obj) else None
def vec(value):return [float(value.x),float(value.y)]
def transform(widget):
    value=widget.get_property('MessageTextWidget').get_property('RenderTransform');return dict(translation=vec(value.Translation),scale=vec(value.Scale),shear=vec(value.Shear),angle=float(value.Angle))

class Validation:
    def __init__(self,result):
        self.path=Path(result);self.started=time.monotonic();self.mode=arg('UEPArenaReadyMode');self.finished=False;self.report=dict(status='running',error=None,mode=self.mode,natural_cues=[],natural_widgets=[],phase_samples=[],owned_widgets=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,audio_playback_tested=False,phase_or_cue_callbacks_replayed=False,phase_timers_changed=False,python_animation_clock_added=False);self.roots=[];self.natural={};self.cues={};self.owned=[];self.world=None;self.selector=None;self.statics=cue.lib('GameplayStatics');self.phase='natural';self.cls=ue.load_class(policy.CLASS);self.cue_cls=ue.load_class(policy.CUE);self.parent_cls=ue.load_class(cue.CLASS);ue.register_declared_mixin(self.parent_cls)
        for obj in (self.cls,self.cue_cls,self.parent_cls):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        if self.mode!='Baseline':self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');self.cls.get_cdo().set_property('PythonMixinProfile',self.mode);ue.register_declared_mixin(self.cls)
    def write(self):atomic_write(self.path,self.report)
    def seconds(self):return float(self.statics.call_function('GetTimeSeconds',self.world))
    def sample(self,w):
        a=w.get_property('GetReady_Intro');return dict(game_seconds=self.seconds(),position=float(w.call_function('GetAnimationCurrentTime',a)),playing=bool(w.call_function('IsAnimationPlaying',a)),forward=bool(w.call_function('IsAnimationPlayingForward',a)),in_viewport=bool(w.call_function('IsInViewport')),visibility=int(w.call_function('GetVisibility')),animation_start=float(a.call_function('GetStartTime')),animation_end=float(a.call_function('GetEndTime')),transform=transform(w))
    def discover(self):
        for world in ue.all_worlds():
            if world.get_world_type() in (1,3) and 'TopDown' in world.get_name():self.world=world;break
        if self.world is None:return
        controller=self.statics.call_function('GetPlayerController',self.world,0)
        if not valid(controller):return
        self.controller=controller;phases=cue.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraGamePhaseSubsystem'))
        active={name:bool(phases.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.'+name))) for name in ('Warmup','Playing','PostGame')};self.report['phase_samples'].append(dict(game_seconds=self.seconds(),**active));self.report['phase_samples']=self.report['phase_samples'][-600:]
        for a in ue.tobject_iterator(self.cue_cls):
            if not valid(a) or a.get_world()!=self.world:continue
            key=path(a)
            if key not in self.cues:self.cues[key]=a;self.report['natural_cues'].append(dict(actor=key,first_game_seconds=self.seconds(),not_rooted=not a.is_rooted(),parent_policy_before=copy.deepcopy(cue.evidence(a))))
            w=a.get_property('SpawnedWidget')
            if valid(w) and w.is_a(self.cls):
                name=path(w)
                if name not in self.natural:
                    row=dict(widget=name,cue=key,owning_player=path(w.call_function('GetOwningPlayer')),first=self.sample(w),samples=[],counts_before=copy.deepcopy(policy.evidence(w)));self.natural[name]=(w,row);self.report['natural_widgets'].append(row)
        for w,row in self.natural.values():
            if valid(w):row['samples'].append(self.sample(w));row['samples']=row['samples'][-600:]
        if active['Playing'] and self.natural and all(valid(w) and not w.call_function('IsInViewport') for w,_ in self.natural.values()):
            for w,row in self.natural.values():row['counts_after']=copy.deepcopy(policy.evidence(w));row['removed_at_playing']=True
            for row in self.report['natural_cues']:
                a=self.cues[row['actor']];row['parent_policy_after']=copy.deepcopy(cue.evidence(a)) if valid(a) else None
            self.phase='owned';self.own_start=self.seconds();self.create_owned()
    def create_owned(self):
        w=cue.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);self.owned.append(w);w.call_function('AddToPlayerScreen',0);self.owned_row=dict(first=self.sample(w),samples=[],counts_before=copy.deepcopy(policy.evidence(w)));self.report['owned_widgets'].append(self.owned_row)
    def observe_owned(self):
        w=self.owned[-1];state=self.sample(w);self.owned_row['samples'].append(state)
        maximum=max(v['position'] for v in self.owned_row['samples'])
        if state['playing'] or maximum<state['animation_end']-.1:
            if self.seconds()-self.own_start>state['animation_end']-state['animation_start']+3.:raise RuntimeError('owned native animation did not complete')
            return
        self.owned_row['counts_after']=copy.deepcopy(policy.evidence(w));self.owned_row['native_animation_finished']=True;self.finish()
    def cleanup(self):
        for w in self.owned:
            if valid(w):w.call_function('RemoveFromParent')
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        for obj in self.roots:obj.remove_from_root()
        self.report['owned_widgets_removed_and_roots_selectors_restored']=all(not valid(w) or not w.call_function('IsInViewport') for w in self.owned) and all(not obj.is_rooted() for obj in self.roots) and (self.selector is None or self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector)
    def tick(self,delta):
        if self.finished:return False
        try:
            if time.monotonic()-self.started>180.:raise RuntimeError('Arena ready native observation timeout')
            if self.phase=='natural':self.discover()
            else:self.observe_owned()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ARENA_READY_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_READY_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaReadyResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
