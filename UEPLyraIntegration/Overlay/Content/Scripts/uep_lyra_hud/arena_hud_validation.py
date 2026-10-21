"""Actual extension ingress and paused native UMG time boundaries, without Tick replay."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from . import arena_hud_mixin as policy,arena_player_tile_mixin as tile_policy
from .arena_hud_contract import CASES,validate
PROBE='/Game/UEPValidation/BP_ArenaHUDProbe.BP_ArenaHUDProbe_C'
COMPONENT='/TopDownArena/UserInterface/Player/B_PlayerUIComponent.B_PlayerUIComponent_C'
def arg(n):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+n+'='))
def path(o):return o.get_path_name() if valid(o) else None
def frame():return int(policy.lib('KismetSystemLibrary').call_function('GetFrameCount'))
def game(w):return float(policy.lib('GameplayStatics').call_function('GetTimeSeconds',w))
def label(w):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',w.get_property('TimeLabel').call_function('GetText'))
def entries(w):return sorted(path(v) for v in policy.one(w.get_property('UIExtensionPointWidget_358').call_function('GetAllEntries')))

class Validation:
    def __init__(self,result):
        self.path=Path(result);self.mode=arg('UEPArenaHUDMode');self.started=time.monotonic();self.finished=False;self.phase='natural';self.world=None;self.roots=[];self.widgets=[];self.selectors={};self.trace={};self.owned_component=None;self.index=0;self.frames=0
        self.report=dict(status='running',error=None,mode=self.mode,full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,timer_tick_or_ready_replayed=False,native_delegates_broadcast_by_fixture=False,production_round_properties_changed=False,python_clock_added=False,clock_cases=[],original_list_empty_events_stay_native=True)
        self.classes={k:ue.load_class(v) for k,v in (('list',policy.LIST),('timer',policy.TIMER),('probe',PROBE),('mode',policy.MODE),('component',COMPONENT))}
        for cls in self.classes.values():self.root(cls)
        self.probe=self.classes['probe'].get_cdo();owner=self
        def observed(base,key):
            def call(w,*args):
                counts=owner.traces(w);counts[key]+=1;counts[key+'_frame']=frame();return base(w,*args)
            if key=='ready':call.override=policy.READY
            return call
        for key,methods in (('list',dict(OnGetWidgetClassForData_0='select',OnConfigureWidgetForData_0='configure')),('timer',dict(Construct='construct',ExperienceReady='ready',Tick='tick'))):
            cls=self.classes[key]
            if self.mode=='Baseline':
                wrapped={}
                for method,event in methods.items():
                    target=policy.READY if event=='ready' else method
                    def original(w,*args,_target=target):return w.call_mixin_original(_target,*args)
                    wrapped[method]=observed(original,event)
                ue.register_mixin_profile(cls,'BaselineObserve',type('BaselineArenaHUD'+key,(),wrapped),make_default=True)
            else:
                self.selectors[key]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.mode);ue.register_declared_mixin(cls)
                for name,base in self.sources(key).items():ue.register_mixin_profile(cls,name,type('ObservedArenaHUD'+key+name,(),{method:observed(getattr(base,method),event) for method,event in methods.items()}))
    def traces(self,w):return self.trace.setdefault(path(w),dict(select=0,configure=0,construct=0,ready=0,tick=0))
    def sources(self,key):return dict(Python=policy.LyraArenaListPythonProfile,BlueprintFallback=policy.LyraArenaListBlueprintFallbackProfile) if key=='list' else dict(Python=policy.LyraArenaRoundPythonProfile,BlueprintFallback=policy.LyraArenaRoundBlueprintFallbackProfile)
    def root(self,o):
        if not o.is_rooted():o.add_to_root();self.roots.append(o)
    def create(self,key):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[key],self.controller);self.root(w);self.widgets.append(w);w.call_function('AddToPlayerScreen',0);return w
    def write(self):atomic_write(self.path,self.report)
    def enter(self,name):self.phase=name;self.since=time.monotonic();self.start_frame=frame()
    def actual_state(self):return [bool(self.real_mode.get_property('IsPlaying')),float(self.real_mode.get_property('ServerWorld_GameEndTime'))]
    def discover(self):
        for w in ue.all_worlds():
            if w.get_world_type() in (1,3) and 'TopDown' in w.get_name():self.world=w;break
        if self.world is None:return
        controller=policy.lib('GameplayStatics').call_function('GetPlayerController',self.world,0)
        if not valid(controller):return
        found={}
        for key in ('list','timer'):
            for w in ue.tobject_iterator(self.classes[key]):
                if valid(w) and w.call_function('GetOwningPlayer')==controller and ((key=='list' and len(entries(w))>=1) or (key=='timer' and valid(w.get_property('TopDownArenaMode')) and self.traces(w)['tick']>=2)):
                    found[key]=w;break
        if len(found)!=2:return
        self.controller=controller;self.host=found['list'];self.real_timer=found['timer'];self.ps=controller.get_property('PlayerState');self.game_state=policy.lib('GameplayStatics').call_function('GetGameState',self.world);self.real_mode=self.game_state.call_function('GetComponentByClass',self.classes['mode']);self.report['natural_list']=True;self.report['natural_timer']=dict(ready_calls=self.traces(self.real_timer)['ready'],tick_calls=self.traces(self.real_timer)['tick'],mode_is_actual_component=self.real_timer.get_property('TopDownArenaMode')==self.real_mode);self.report['natural_list_counts']=copy.deepcopy(policy.evidence(self.host));self.report['natural_timer_counts']=copy.deepcopy(policy.evidence(self.real_timer));self.test_list();self.owned_timer=self.create('timer');self.created_frame=frame();self.enter('experience')
    def test_list(self):
        self.report['selector_results']=[policy.one(self.probe.call_function('Select',self.host,value))==ue.load_class(policy.TILE) for value in (None,self.ps,self.host)]
        tiles=[w for w in ue.tobject_iterator(ue.load_class(policy.TILE)) if valid(w) and w.call_function('GetOwningPlayer')==self.controller and 'BombStat' in w.properties() and valid(w.get_property('BombStat')) and w.get_property('BombStat').get_property('Ability Target')==self.ps];before=[copy.deepcopy(tile_policy.evidence(w)) for w in tiles];self.probe.call_function('Configure',self.host,self.host,self.ps);self.probe.call_function('Configure',self.host,None,None);self.report['invalid_widget_no_tile_configures']=before==[copy.deepcopy(tile_policy.evidence(w)) for w in tiles]
        original=entries(self.host);counts=copy.deepcopy(self.traces(self.host));self.owned_component=self.ps.add_actor_component(self.classes['component'],'UEPArenaHUDIngress');added=entries(self.host);self.owned_component.destroy_component();self.owned_component=None;self.report['list_ingress']=dict(native_begin_end_component=True,entries_added=len(added)-len(original),entries_restored=entries(self.host)==original,native_select_delta=self.traces(self.host)['select']-counts['select'],native_configure_delta=self.traces(self.host)['configure']-counts['configure'])
    def experience(self):
        w=self.owned_timer
        if not valid(w.get_property('TopDownArenaMode')) or self.traces(w)['ready']<1:return
        self.report['owned_experience']=dict(ready_next_frame=self.traces(w)['ready_frame']>self.created_frame,mode_is_actual_component=w.get_property('TopDownArenaMode')==self.real_mode);self.owned_mode=ue.new_object(self.classes['mode'],self.game_state);self.root(self.owned_mode);w.set_property('TopDownArenaMode',self.owned_mode);self.original_pause=bool(policy.lib('GameplayStatics').call_function('IsGamePaused',self.world));self.real_before=self.actual_state();policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,True);self.freeze_time=game(self.world);self.start_case()
    def start_case(self):
        _,seconds,playing,_=CASES[self.index];self.owned_mode.set_property('IsPlaying',playing);server=float(self.game_state.call_function('GetServerWorldTimeSeconds'));self.owned_mode.set_property('ServerWorld_GameEndTime',server+seconds);self.before_tick=self.traces(self.owned_timer)['tick'];self.enter('clock')
    def clock(self):
        w=self.owned_timer;delta=self.traces(w)['tick']-self.before_tick
        if delta<2:return
        name,seconds,playing,_=CASES[self.index];self.report['clock_cases'].append(dict(name=name,input=seconds,playing=playing,text=label(w),native_tick_delta=delta,native_frame_delta=frame()-self.start_frame,world_time_frozen=abs(game(self.world)-self.freeze_time)<.0001));self.index+=1
        if self.index<len(CASES):self.start_case();return
        self.last_label=label(w);w.set_property('TopDownArenaMode',None);self.before_tick=self.traces(w)['tick'];self.enter('invalid')
    def invalid(self):
        w=self.owned_timer;delta=self.traces(w)['tick']-self.before_tick
        if delta<2:return
        self.report['invalid_mode']=dict(text_unchanged=label(w)==self.last_label,native_tick_delta=delta);self.report['actual_round_properties_preserved']=self.actual_state()==self.real_before;policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,self.original_pause);self.before_remount=copy.deepcopy(self.traces(w));w.call_function('RemoveFromParent');w.call_function('AddToPlayerScreen',0);self.remount_frame=frame();self.enter('remount')
    def remount(self):
        w=self.owned_timer;counts=self.traces(w)
        if counts['ready']==self.before_remount['ready']:return
        self.report['remount']=dict(construct_delta=counts['construct']-self.before_remount['construct'],ready_delta=counts['ready']-self.before_remount['ready'],native_ready_next_frame=counts['ready_frame']>self.remount_frame,actual_component_restored=w.get_property('TopDownArenaMode')==self.real_mode);self.finish()
    def cleanup(self):
        if self.world is not None and hasattr(self,'original_pause'):policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,self.original_pause)
        if valid(self.owned_component):self.owned_component.destroy_component();self.owned_component=None
        for w in self.widgets:w.call_function('RemoveFromParent')
        for key in ('list','timer'):
            if self.mode=='Baseline':ue.unregister_mixin(self.classes[key])
            else:
                for name,source in self.sources(key).items():ue.register_mixin_profile(self.classes[key],name,source)
                self.classes[key].get_cdo().set_property('PythonMixinProfile',self.selectors[key])
        self.report['pause_restored']=not hasattr(self,'original_pause') or bool(policy.lib('GameplayStatics').call_function('IsGamePaused',self.world))==self.original_pause
        for o in reversed(self.roots):o.remove_from_root()
        self.report['cleanup_complete']=self.report['pause_restored'] and all(not w.call_function('IsInViewport') for w in self.widgets) and all(not o.is_rooted() for o in self.roots) and self.owned_component is None
    def tick(self,delta):
        if self.finished:return False
        try:
            if time.monotonic()-self.started>150.:raise RuntimeError('Arena HUD native timeout: '+self.phase)
            {'natural':self.discover,'experience':self.experience,'clock':self.clock,'invalid':self.invalid,'remount':self.remount}[self.phase]();self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ARENA_HUD_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_HUD_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaHUDResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
