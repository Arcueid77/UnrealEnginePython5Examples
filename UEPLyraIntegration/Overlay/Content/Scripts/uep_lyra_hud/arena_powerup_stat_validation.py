"""Observe original native retry quirks, soft load and real GAS value delegates."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayEffectContextHandle,GameplayModifierInfo,GameplayEffectModifierMagnitude,ScalableFloat
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from . import arena_powerup_stat_mixin as policy
from .arena_powerup_stat_contract import validate,FORMAT
PROBE='/Game/UEPValidation/BP_ArenaPowerupStatProbe.BP_ArenaPowerupStatProbe_C'
EFFECT='/Game/UEPValidation/GE_ArenaStatProbe.GE_ArenaStatProbe_C'
TEXTURE='/Game/UEPValidation/T_ArenaStatSoftProbe.T_ArenaStatSoftProbe'
def arg(n):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+n+'='))
def path(o):return o.get_path_name() if valid(o) else None
def active(o):return valid(o) and bool(o.call_function('IsActive'))
def proxy(w):return w.get_property('AsyncAttributeChanged')
def text(w):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',w.get_property('BonusText').call_function('GetText'))
def game(w):return float(policy.lib('GameplayStatics').call_function('GetTimeSeconds',w))

class Validation:
    def __init__(self,result):
        self.path=Path(result);self.mode=arg('UEPArenaPowerupStatMode');self.started=time.monotonic();self.finished=False;self.phase='natural';self.roots=[];self.widgets=[];self.actors=[];self.proxies=[];self.events=[];self.listens=[];self.selector=None;self.world=None;self.frames=0
        self.report=dict(status='running',error=None,mode=self.mode,natural_stats=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,callbacks_replayed=False,delegate_broadcast_by_fixture=False,python_retry_clock=False,new_production_cleanup_added=False,actor_attributes_written_directly=False,trace_only_forwarding=True,native_gameplay_effect_used=True,no_manual_animation_completion=True)
        self.cls=ue.load_class(policy.CLASS);self.probe_cls=ue.load_class(PROBE);self.effect_cls=ue.load_class(EFFECT)
        for o in (self.cls,self.probe_cls,self.effect_cls):self.root(o)
        self.probe=self.probe_cls.get_cdo();owner=self
        def listen(base):
            def call(w):owner.listens.append(dict(widget=path(w),game=game(w)));return base(w)
            return call
        def changed(base):
            def call(w,Attribute,NewValue:float,OldValue:float):owner.events.append(dict(widget=path(w),game=game(w),attribute=str(Attribute.AttributeName),new=float(NewValue),old=float(OldValue)));return base(w,Attribute,NewValue,OldValue)
            call.override=policy.BOUND;return call
        if self.mode=='Baseline':
            def original_listen(w):return w.call_mixin_original('ListenFor')
            def original_changed(w,a,n,o):return w.call_mixin_original(policy.BOUND,a,n,o)
            ue.register_mixin_profile(self.cls,'BaselineObserve',type('BaselineStatNativeTrace',(),dict(ListenFor=listen(original_listen),ObservedChanged=changed(original_changed))),make_default=True)
        else:
            self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');self.cls.get_cdo().set_property('PythonMixinProfile',self.mode);ue.register_declared_mixin(self.cls)
            for name,base in self.sources().items():ue.register_mixin_profile(self.cls,name,type('ObservedArenaStat'+name,(),dict(PrepareConfigure=base.__dict__['PrepareConfigure'],UpdateText=base.UpdateText,ListenFor=listen(base.ListenFor),ObservedChanged=changed(base.ObservedChanged))))
    def sources(self):return dict(Python=policy.LyraArenaPowerupStatPythonProfile,BlueprintFallback=policy.LyraArenaPowerupStatBlueprintFallbackProfile)
    def root(self,o):
        if not o.is_rooted():o.add_to_root();self.roots.append(o)
    def write(self):atomic_write(self.path,self.report)
    def enter(self,p):self.phase=p;self.since=time.monotonic();self.game_since=game(self.world)
    def count(self,rows,w):return [r for r in rows if r['widget']==path(w)]
    def create(self):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.cls,self.controller);self.root(w);self.widgets.append(w);w.call_function('AddToPlayerScreen',0);return w
    def actor(self):
        actor=self.world.actor_spawn(ue.find_class('AbilitySystemTestPawn'),ue.FVector(400000.+len(self.actors)*10000.,400000.,3000.));self.actors.append(actor);return actor
    def configure(self,w,target):self.probe.call_function('Configure',w,target)
    def apply(self,value):
        attribute=self.a.get_property('Attribute').clone();self.effect_cls.get_cdo().set_property('DurationPolicy',0);self.effect_cls.get_cdo().set_property('Modifiers',[GameplayModifierInfo(Attribute=attribute,ModifierOp=3,ModifierMagnitude=GameplayEffectModifierMagnitude(ScalableFloatMagnitude=ScalableFloat(Value=float(value))))]);self.asc.call_function('BP_ApplyGameplayEffectToSelf',self.effect_cls,1.,GameplayEffectContextHandle())
    def discover(self):
        for world in ue.all_worlds():
            if world.get_world_type() in (1,3) and 'TopDown' in world.get_name():self.world=world;break
        if self.world is None:return
        controller=policy.lib('GameplayStatics').call_function('GetPlayerController',self.world,0)
        if not valid(controller):return
        natural=[]
        for w in ue.tobject_iterator(self.cls):
            if not valid(w) or not valid(w.call_function('GetOwningPlayer')) or w.call_function('GetOwningPlayer').get_world()!=self.world or not active(proxy(w)):continue
            number,found=policy.query(w)
            if not found:continue
            expected=policy.lib('KismetTextLibrary').call_function('Conv_Int64ToText',policy.lib('KismetMathLibrary').call_function('Round64',number),False,True,1,324)
            natural.append(dict(attribute=str(w.get_property('Attribute').AttributeName),target=path(w.get_property('Ability Target')),active=True,text=text(w),expected_text=str(expected),counts=copy.deepcopy(policy.evidence(w))))
        if {r['attribute'] for r in natural}!={'BombsRemaining','BombRange','MovementSpeed'}:return
        self.frames+=1
        if self.frames<4:return
        self.report['natural_stats']=natural;self.controller=controller;self.a=self.create();self.bare=self.actor();self.asc=self.bare.get_property('AbilitySystemComponent');self.report['soft_texture_initially_unloaded']=not any(o.get_path_name()==TEXTURE for o in ue.tobject_iterator(ue.find_class('Texture2D')))
        self.configure(self.a,self.bare);self.configure(self.a,self.bare);_,found=policy.query(self.a);self.report['retry']=dict(initial_attribute_missing=not found,two_configures=True);self.pause_game=game(self.world);self.pause_listens=len(self.count(self.listens,self.a));self.original_pause=bool(policy.lib('GameplayStatics').call_function('IsGamePaused',self.world));policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,True);self.enter('paused')
    def paused(self):
        if time.monotonic()-self.since<.18:return
        self.report['retry'].update(paused_seconds=time.monotonic()-self.since,game_time_paused=abs(game(self.world)-self.pause_game)<.0001,native_listen_continues_while_paused=len(self.count(self.listens,self.a))>self.pause_listens)
        self.asc.call_function('K2_InitStats',ue.find_class('TopDownArenaAttributeSet'),None);_,found=policy.query(self.a);self.report['retry'].update(attribute_initialized_natively=found,no_proxy_after_init_while_paused=not active(proxy(self.a)));self.init_frame=int(policy.lib('KismetSystemLibrary').call_function('GetFrameCount'));self.enter('retry')
    def retry(self):
        if not active(proxy(self.a)):return
        p=proxy(self.a);self.proxies.append(p);self.report['retry'].update(resumed_without_manual_listen=True,native_resume_game_seconds=game(self.world)-self.game_since,native_resume_real_seconds=time.monotonic()-self.since,native_resume_frame_delta=int(policy.lib('KismetSystemLibrary').call_function('GetFrameCount'))-self.init_frame,resumed_while_world_paused=bool(policy.lib('GameplayStatics').call_function('IsGamePaused',self.world)),active=True,initial_text=text(self.a));self.report['soft_texture_resource']=path(self.a.get_property('CommonLazyImage_34').get_property('Brush').ResourceObject)
        if self.report['soft_texture_resource']!=TEXTURE:return
        policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,False)
        before=len(self.count(self.events,self.a));self.apply(.5);events=self.count(self.events,self.a)[before:];animation=self.a.get_property('AnimationUp');self.report['first_change']=dict(callbacks=len(events),new_value=events[-1]['new'],old_value=events[-1]['old'],text=text(self.a),native_animation_started=bool(self.a.call_function('IsAnimationPlaying',animation)));self.max_position=0.;self.animation_end=float(animation.call_function('GetEndTime'));self.enter('animation')
    def animation(self):
        animation=self.a.get_property('AnimationUp');position=float(self.a.call_function('GetAnimationCurrentTime',animation));self.max_position=max(self.max_position,position)
        if self.a.call_function('IsAnimationPlaying',animation):return
        if self.max_position<=.01:return
        self.report['animation']=dict(max_position=self.max_position,finished=True,end=self.animation_end);self.b=self.create();self.bare_b=self.actor();self.configure(self.b,self.bare_b);self.configure(self.b,self.bare);self.immediate=proxy(self.b);self.proxies.append(self.immediate);self.enter('pending')
    def pending(self):
        if game(self.world)-self.game_since<.15:return
        p=proxy(self.b);self.proxies.append(p);before=len(self.count(self.events,self.b));self.apply(.25);events=self.count(self.events,self.b)[before:];self.report['pending_reconfigure']=dict(immediate_active=active(self.immediate),replacement_distinct=p!=self.immediate,earlier_proxy_still_active=active(self.immediate),proxies_not_rooted=not p.is_rooted() and not self.immediate.is_rooted(),callbacks=len(events),new_value=events[-1]['new'],old_value=events[-1]['old'],text=text(self.b))
        self.configure(self.b,self.bare);self.proxies.append(proxy(self.b));before=len(self.count(self.events,self.b));self.apply(.75);events=self.count(self.events,self.b)[before:];self.report['repeat_configure']=dict(stored_previous_cancelled=not active(p),older_proxy_still_active=active(self.immediate),callbacks=len(events),text=text(self.b));self.report['format_cases']=[]
        for value,_ in FORMAT:self.probe.call_function('Update',self.b,value);self.report['format_cases'].append([value,text(self.b)])
        self.finish()
    def cleanup(self):
        if self.world is not None and hasattr(self,'original_pause'):policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,self.original_pause)
        for p in self.proxies:
            if valid(p):p.call_function('Cancel')
        for w in self.widgets:
            if active(proxy(w)):proxy(w).call_function('Cancel')
            w.call_function('RemoveFromParent')
        for actor in self.actors:
            if valid(actor):actor.actor_destroy()
        if self.mode=='Baseline':ue.unregister_mixin(self.cls)
        else:
            for name,source in self.sources().items():ue.register_mixin_profile(self.cls,name,source)
            self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        self.report['owned_proxies_cancelled']=all(not active(p) for p in self.proxies);self.report['owned_widgets_removed']=all(not w.call_function('IsInViewport') for w in self.widgets);self.report['pause_restored']=not hasattr(self,'original_pause') or bool(policy.lib('GameplayStatics').call_function('IsGamePaused',self.world))==self.original_pause
        for o in reversed(self.roots):o.remove_from_root()
        self.report['cleanup_complete']=self.report['owned_proxies_cancelled'] and self.report['owned_widgets_removed'] and self.report['pause_restored'] and all(not o.is_rooted() for o in self.roots)
    def tick(self,delta):
        if self.finished:return False
        try:
            if time.monotonic()-self.started>150.:raise RuntimeError('Arena stat native timeout: '+self.phase)
            {'natural':self.discover,'paused':self.paused,'retry':self.retry,'animation':self.animation,'pending':self.pending}[self.phase]();self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ARENA_POWERUP_STAT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_POWERUP_STAT_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaPowerupStatResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
