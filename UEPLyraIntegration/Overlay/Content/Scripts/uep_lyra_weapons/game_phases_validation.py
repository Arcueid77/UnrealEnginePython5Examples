"""Observe real phase activation, VM messages, global effects and server travel."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .hero_burst_cue_mixin import lib
from . import tdm_scoring_mixin as tdm
from . import game_phases_mixin as policy
from .game_phases_contract import FALSE_FIELDS,require,validate,travel_evidence

METHODS={'warmup':dict(Activate='warmup',End='warmupend',Sanitize='sanitize',Ready='ready',Step='step'),'playing':dict(Activate='playing',End='playingend'),'postgame':dict(Activate='postgame',Block='block',Restart='restart')}


def frame():return int(lib('KismetSystemLibrary').call_function('GetFrameCount'))
def game_time(context):return float(lib('GameplayStatics').call_function('GetTimeSeconds',context))
def global_has(context,path):return any(cls.get_path_name()==path for cls in policy.global_system(context).get_property('AppliedEffects'))
def tag(value):return GameplayTag(TagName=value)


class Validation:
    def __init__(self,path):
        self.path=Path(path);self.started=time.monotonic();self.finished=False;self.phase='boot';self.round=0;self.world=None;self.scope=None;self.probe=None;self.sources={};self.cdos={};self.classes={};self.sanitizing=False;self.waiting_travel=False;self.stable_since=None;self.report=dict(status='running',error=None,profile=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPGamePhasesProfile=')),trace=[],sanitize_cases=[],countdown_messages=[],runtime_fixture_durations=dict(wait=2.25,countdown=2,postgame=.25));self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.install()
    def write(self):atomic_write(self.path,self.report)
    def install(self):
        for label,path in policy.CLASSES.items():
            cls=ue.load_class(path);self.classes[label]=cls;ue.register_declared_mixin(cls);registry,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[label]={p:r['python_class'] for p,r in registry['profiles'].items()};cdo=cls.get_cdo();fields=['PythonMixinProfile']+(['WaitForPlayersDuration','CountdownDuration'] if label=='warmup' else ['NewGameTime'] if label=='postgame' else []);self.cdos[label]={n:cdo.get_property(n) for n in fields};cdo.set_property('PythonMixinProfile',self.report['profile'])
            for profile,base in self.sources[label].items():
                methods={}
                for name,key in METHODS[label].items():
                    def around(fn,label,key):
                        def invoke(a,*args):return self.call(label,key,fn,a,args)
                        invoke.override=policy.GATES[key];return invoke
                    methods[name]=around(getattr(base,name),label,key)
                ue.register_mixin_profile(cls,profile,type('ObservedGamePhase'+label+profile,(),methods))
        self.classes['warmup'].get_cdo().set_property('WaitForPlayersDuration',2.25);self.classes['warmup'].get_cdo().set_property('CountdownDuration',2);self.classes['postgame'].get_cdo().set_property('NewGameTime',.25);self.write()
    def sanitize_cases(self,a):
        self.sanitizing=True;old=(a.get_property('WaitForPlayersDuration'),a.get_property('CountdownDuration'))
        try:
            for wait,count in ((-2.5,-3),(2.75,8),(4.2,-1),(2147483648.,2)):
                a.set_property('WaitForPlayersDuration',wait);a.set_property('CountdownDuration',count);a.call_function('SanitizeDurations');self.report['sanitize_cases'].append(dict(wait=wait,count=count,actual_wait=float(a.get_property('WaitForPlayersDuration')),actual_count=int(a.get_property('CountdownDuration'))))
        finally:a.set_property('WaitForPlayersDuration',old[0]);a.set_property('CountdownDuration',old[1]);self.sanitizing=False
    def bind_messages(self,context):
        self.scope=SubscriptionScope();self.probe=ue.load_class('/Game/UEPValidation/BP_GamePhaseProbe.BP_GamePhaseProbe_C').get_cdo();self.probe_rooted=not self.probe.is_rooted()
        if self.probe_rooted:self.probe.add_to_root()
        def reader(proxy):
            payload,ok=self.probe.call_function('ReadVerb',proxy);require(ok,'typed native countdown extraction failed');return payload
        self.scope.listen_gameplay_message(context,policy.CHANNEL,ue.find_struct('LyraVerbMessage'),reader,self.on_message)
    def on_message(self,channel,payload):
        if self.round!=1:return
        self.report['countdown_messages'].append(dict(channel=str(channel.TagName),verb=str(payload.Verb.TagName),magnitude=float(payload.Magnitude),instigator_is_null=payload.Instigator is None,target_is_null=payload.Target is None,instigator_tags=[str(t.TagName) for t in payload.InstigatorTags.GameplayTags],target_tags=[str(t.TagName) for t in payload.TargetTags.GameplayTags],context_tags=[str(t.TagName) for t in payload.ContextTags.GameplayTags],lobby_active=global_has(self.world,policy.LOBBY),time=game_time(self.world),frame=frame()))
    def clear_world(self):
        if self.scope is not None:
            self.scope.close();self.report['probe_scope_closed_before_travel']=self.scope.closed;self.scope=None
        if self.probe is not None and self.probe_rooted:self.probe.remove_from_root()
        self.probe=None;self.world=None;self.stable_since=None
    def call(self,label,key,fn,a,args):
        row=dict(phase=label,event=key,round=self.round,time=game_time(a),frame=frame(),active=bool(a.get_property('bIsActive')),actor=a.get_path_name())
        if key in ('warmupend','playingend'):row['cancelled']=bool(args[0])
        if key in ('ready','step'):row['remaining_before']=int(a.get_property('CountdownSecsRemaining'))
        if key=='warmup':
            self.round+=1;row['round']=self.round;state=lib('GameplayStatics').call_function('GetGameState',a);self.world=state.get_world();self.report['native_mode']=str(lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode)
            if self.round==1:self.bind_messages(self.world);self.sanitize_cases(a)
            elif self.waiting_travel:self.report['second_warmup_time']=row['time'];self.report['second_warmup_frame']=row['frame'];self.phase='second-round'
        if key=='playing':
            row['lobby_active']=global_has(a,policy.LOBBY)
            if self.round==1:self.phase='playing';self.stable_since=None
            else:self.phase='second-playing';self.stable_since=None
        if key=='postgame':self.report['postgame_start_time']=row['time'];self.phase='postgame'
        if key=='block':row.update(immunity_active=global_has(a,policy.IMMUNITY),block_active=global_has(a,policy.BLOCK));self.report.update(block_time=row['time'],block_frame=row['frame'])
        if key=='restart':
            row.update(immunity_active=global_has(a,policy.IMMUNITY),block_active=global_has(a,policy.BLOCK));self.report.update(restart_time=row['time'],restart_frame=row['frame']);self.waiting_travel=True;self.phase='travel';self.clear_world()
        self.report['trace'].append(row);self.write();return fn(a,*args)
    def controller_ready(self):
        if not valid(self.world):return False
        statics=lib('GameplayStatics');isolate_bots(statics,self.world,ue.find_class('LyraPlayerBotController'));bridge=lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world);snapshot=bridge.call_function('CaptureSnapshot');self.report['readiness']=dict(experience=bool(snapshot.bExperienceLoaded),input=bool(snapshot.bHeroInputReady),asc=bool(snapshot.bAbilitySystemReady),health_ready=bool(snapshot.bHealthReady),immune=bool(snapshot.bDamageImmune),health=float(snapshot.Health))
        return snapshot.bExperienceLoaded and snapshot.bHeroInputReady and snapshot.bAbilitySystemReady and snapshot.bHealthReady and not snapshot.bDamageImmune and snapshot.Health>0
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native game phase/travel timeout')
            if valid(self.world):isolate_bots(lib('GameplayStatics'),self.world,ue.find_class('LyraPlayerBotController'))
            if self.phase in ('playing','second-playing') and self.controller_ready():
                if self.stable_since is None:self.stable_since=time.monotonic()
                elif time.monotonic()-self.stable_since>.2:
                    if self.phase=='playing':
                        phases=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraGamePhaseSubsystem'));require(phases.call_function('IsPhaseActive',tag('ShooterGame.GamePhase.Playing')),'native Playing phase tag absent');state=lib('GameplayStatics').call_function('GetGameState',self.world);scoring=state.get_component_by_type(ue.load_class(tdm.CLASS));require(valid(scoring),'actual TDM phase producer missing');scoring.call_function(tdm.POSTGAME)
                    else:self.complete()
            self.report['stage']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def complete(self):
        trace=self.report['trace'];first=lambda key:next(r for r in trace if r['event']==key);playing=first('playing');warmend=first('warmupend');playend=first('playingend');block=first('block');restart=first('restart');messages=self.report['countdown_messages'];cases=self.report['sanitize_cases'];expected=[(0.,0),(2.75,2),(4.2,0),(2147483648.,-2147483648)];self.report.update(natural_warmup_and_playing_observed=self.round>=2 and any(r['event']=='ready' for r in trace),sanitization_matches_source_rules=[(r['actual_wait'],r['actual_count']) for r in cases]==expected,countdown_payloads_and_inclusive_zero_match=[m['magnitude'] for m in messages]==[2.,1.,0.] and all(m['channel']==m['verb']==policy.CHANNEL and m['instigator_is_null'] and m['target_is_null'] and not m['instigator_tags'] and not m['target_tags'] and not m['context_tags'] and m['lobby_active'] for m in messages),pregame_effect_removed_before_playing=not playing['lobby_active'],native_phase_parent_tags_and_cancellation_observed=warmend['cancelled'] and playend['cancelled'] and playing['active'],postgame_immunity_then_block_then_next_tick=block['immunity_active'] and not block['block_active'] and restart['immunity_active'] and restart['block_active'] and restart['frame']>block['frame'],actual_server_travel_and_second_natural_round=self.waiting_travel and self.round>=2 and self.report['second_warmup_frame']>self.report['restart_frame'] ,postgame_wait_elapsed=self.report['block_time']-self.report['postgame_start_time']);self.report['native_travel_log_evidence']=travel_evidence((self.path.parent/'jump.log').read_text(encoding='utf-8-sig',errors='replace'));self.report['actual_server_travel_and_second_natural_round'] &= all(self.report['native_travel_log_evidence'].values());self.finish()
    def cleanup(self):
        self.clear_world();restored=True
        for label,cls in self.classes.items():
            for name,value in self.cdos[label].items():cls.get_cdo().set_property(name,value)
            for profile,base in self.sources[label].items():ue.register_mixin_profile(cls,profile,base)
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];restored &= all(cls.get_cdo().get_property(n)==v for n,v in self.cdos[label].items()) and all(row['profiles'][p]['python_class'] is base for p,base in self.sources[label].items())
        self.report.update(runtime_cdo_fields_and_profile_wrappers_restored=restored,no_fixture_roots_remaining=self.probe is None and self.scope is None)
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_GAME_PHASES_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_GAME_PHASES_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPGamePhasesResult=')),None)
if result:
    try:validation=Validation(result)
    except Exception:
        error=traceback.format_exc();atomic_write(Path(result),dict(status='failed',error=error));ue.log_error('UEP_GAME_PHASES_STARTUP_FAILED '+error);ue.request_exit()
    else:atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
