"""Default cycle first; then owned native Begin/message/getter/lifetime scenarios."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import LyraVerbMessage
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_weapons.scoring_base_contract import CASES
from .effect_pad_mixin import valid
from . import arena_mode_mixin as policy
from .arena_phases_validation import Validation as Cycle
from .arena_phases_contract import validate as validate_cycle
from .arena_mode_contract import CLOCK,validate
PROBE='/Game/UEPValidation/BP_ArenaModeProbe.BP_ArenaModeProbe_C'
FIXTURE='/Game/UEPValidation/BP_ArenaModeFixture.BP_ArenaModeFixture_C'
def arg(n):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+n+'='))
def path(o):return o.get_path_name() if valid(o) else None
class Validation(Cycle):
    def __init__(self,result):
        self.cycle_snapshot=None;self.tests_done=False;self.units=[];self.owned_component=None;self.own_roots=[];self.base_selectors={};self.own_stage='waiting';super().__init__(result);self.mode=arg('UEPArenaModeMode');self.report['mode']=self.mode
        self.base=ue.load_class(policy.BASE);self.fixture_class=ue.load_class(FIXTURE);self.probe_class=ue.load_class(PROBE)
        self.mode_classes=[self.base,ue.load_class(policy.LIVES),ue.load_class(policy.LOCAL),self.fixture_class]
        for cls in self.mode_classes+[self.probe_class]:
            if not cls.is_rooted():cls.add_to_root();self.own_roots.append(cls)
        self.probe=self.probe_class.get_cdo()
        if self.mode!='Baseline':
            for cls in self.mode_classes:self.base_selectors[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.mode)
            ue.register_declared_mixin(self.base)
        self.report.update(message_cases=[],clock_cases=[])
        for k in ('callbacks_replayed','begin_play_replayed','python_subscription_roots_added','native_proxy_cancelled_by_fixture','actual_round_properties_written'):self.report[k]=False
    def gi_refs(self):return {path(p) for p in self.gi.get_property('ReferencedObjects') if valid(p) and p.is_a(ue.find_class('AsyncAction_ListenForGameplayMessage'))}
    def finish(self,error=None):
        if not error and not self.tests_done:
            if self.cycle_snapshot is None:self.cycle_snapshot=copy.deepcopy(self.report);self.cycle_snapshot['mode']='Python';self.fixture_wait=time.monotonic();self.own_stage='setup'
            return
        super().finish(error)
    def setup(self):
        self.world=next(w for w in ue.all_worlds() if w.get_world_type() in (1,3) and 'TopDown' in w.get_name() and valid(policy.state(w)));self.gs=policy.state(self.world);self.gi=policy.lib('GameplayStatics').call_function('GetGameInstance',self.world);self.team=policy.teams(self.world);self.team_ids=list(native_outputs('LyraTeamSubsystem','GetTeamIDs',self.team.call_function('GetTeamIDs'))['ReturnValue']);self.router=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'))
        users=native_outputs('InputDeviceLibrary','GetAllActiveUsers',policy.lib('InputDeviceLibrary').call_function('GetAllActiveUsers'));self.report['natural_local_user_count']=int(users['ReturnValue']);self.report['natural_local_player_count']=len(self.gi.get_property('LocalPlayers'));self.before_proxies=self.gi_refs();self.owned_component=self.gs.add_actor_component(self.fixture_class,'UEPArenaModeOwned');self.owned_component.call_function('SetComponentTickEnabled',False);self.report['fixture_native_begin']=True;self.report['owned_fixture_started_phase_after_cycle_only']=self.cycle_snapshot is not None;self.wait_frames=0;self.own_stage='listeners'
    def listeners(self):
        self.wait_frames+=1
        if self.wait_frames<3:return
        self.owned_proxies=self.gi_refs()-self.before_proxies;self.report['fixture_native_message_proxies']=len(self.owned_proxies);self.report['scoring_recipients']=len(self.report['natural_components'])+1
        for index in (0,1):
            controller=self.world.actor_spawn(ue.find_class('LyraPlayerController'));state=controller.get_property('PlayerState');pawn=self.world.actor_spawn(ue.find_class('LyraCharacter'),ue.FVector(250000.+index*10000.,250000.,3000.));controller.call_function('Possess',pawn);manager=ue.new_object(ue.find_class('CheatManager'),controller);cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager);cheats.call_function('SetTeam',self.team_ids[index]);self.units.append(dict(controller=controller,state=state,pawn=pawn,manager=manager,cheats=cheats))
        sources=dict(ps0=self.units[0]['state'],ps1=self.units[1]['state'],pawn0=self.units[0]['pawn'],pawn1=self.units[1]['pawn'],null=None);self.score_start=self.values()
        for name,channel,a,b in CASES:
            before=self.values();self.broadcast(channel,sources[a],sources[b]);after=self.values();self.report['message_cases'].append(dict(name=name,delta=[x-y for x,y in zip(after,before)]));self.restore(before)
        self.report['scores_restored']=self.values()==self.score_start;self.original_pause=bool(policy.lib('GameplayStatics').call_function('IsGamePaused',self.world));policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,True)
        for playing,offset,_ in CLOCK:
            self.owned_component.set_property('IsPlaying',playing);self.owned_component.set_property('ServerWorld_GameEndTime',float(self.gs.call_function('GetServerWorldTimeSeconds'))+offset);result=float(policy.one(self.probe.call_function('Remaining',self.owned_component)));self.report['clock_cases'].append(dict(playing=playing,offset=offset,remaining=result))
        policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,self.original_pause);self.owned_component.destroy_component();self.owned_component=None;policy.lib('KismetSystemLibrary').call_function('CollectGarbage');self.wait_frames=0;self.own_stage='gc'
    def values(self):
        tags=('ShooterGame.Score.Eliminations','ShooterGame.Score.Deaths','ShooterGame.Score.Assists');return [int(u['state'].call_function('GetStatTagStackCount',policy.tag(t))) for u in self.units for t in tags]+[int(self.team.call_function('GetTeamTagStackCount',i,policy.tag(tags[0]))) for i in self.team_ids[:2]]
    def restore(self,before):
        after=self.values();tags=('ShooterGame.Score.Eliminations','ShooterGame.Score.Deaths','ShooterGame.Score.Assists')
        for i,u in enumerate(self.units):
            for j,t in enumerate(tags):
                n=after[i*3+j]-before[i*3+j]
                if n:u['state'].call_function('RemoveStatTagStack' if n>0 else 'AddStatTagStack',policy.tag(t),abs(n))
        for j,team in enumerate(self.team_ids[:2]):
            n=after[6+j]-before[6+j]
            if n:self.team.call_function('RemoveTeamTagStack' if n>0 else 'AddTeamTagStack',team,policy.tag(tags[0]),abs(n))
        if self.values()!=before:raise RuntimeError('owned score deltas not restored')
    def broadcast(self,channel,source,target):self.probe.call_function('BroadcastVerb',self.router,policy.tag(channel),LyraVerbMessage(Instigator=source,Target=target,Magnitude=-17.))
    def collect(self):
        self.wait_frames+=1
        if self.wait_frames<3:return
        self.broadcast('Lyra.Elimination.Message',None,None);self.broadcast('Lyra.Assist.Message',None,None);self.report['native_proxy_gi_refs_released']=not self.owned_proxies.intersection(self.gi_refs());self.report['engine_gc_frames']=self.wait_frames;self.tests_done=True;self.finish()
    def tick(self,delta):
        if self.finished:return False
        try:
            if self.cycle_snapshot is None:
                super().tick(delta)
                if 'natural_components' not in self.report and any(s['Playing'] for s in self.report['samples']):
                    world=next(w for w in ue.all_worlds() if w.get_world_type() in (1,3) and 'TopDown' in w.get_name() and valid(policy.state(w)));gs=policy.state(world);natural=[c for c in ue.tobject_iterator(self.base) if valid(c) and c.call_function('GetOwner')==gs];self.report['natural_components']=[{'class':c.get_class().get_path_name(),'counts':copy.deepcopy(policy.evidence(c))} for c in natural]
            elif self.own_stage=='setup' and time.monotonic()-self.fixture_wait>=.5:self.setup()
            elif self.own_stage=='listeners':self.listeners()
            elif self.own_stage=='gc':self.collect()
            self.write();return not self.finished
        except Exception:self.tests_done=True;self.finish(traceback.format_exc());return False
    def cleanup(self):
        if hasattr(self,'original_pause'):policy.lib('GameplayStatics').call_function('SetGamePaused',self.world,self.original_pause)
        if valid(self.owned_component):self.owned_component.destroy_component();self.owned_component=None
        for u in self.units:
            for k in ('pawn','controller','state'):
                if valid(u[k]):u[k].actor_destroy()
        self.report['owned_actors_destroyed']=all(not valid(u[k]) for u in self.units for k in ('pawn','controller','state'));self.report['owned_component_destroyed']=self.owned_component is None;self.report['pause_restored']=not hasattr(self,'original_pause') or bool(policy.lib('GameplayStatics').call_function('IsGamePaused',self.world))==self.original_pause
        for cls,value in self.base_selectors.items():cls.get_cdo().set_property('PythonMixinProfile',value)
        for cls in reversed(self.own_roots):cls.remove_from_root()
        mode=self.mode;self.mode='Python';super().cleanup();self.mode=mode
        if self.cycle_snapshot is not None:
            self.cycle_snapshot.update(status='passed',error=None,cleanup_complete=self.report['cleanup_complete'],selectors_restored=self.report['selectors_restored'],all_classes_unrooted=self.report['all_classes_unrooted']);self.report['cycle']=self.cycle_snapshot
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_MODE_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaModeResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
