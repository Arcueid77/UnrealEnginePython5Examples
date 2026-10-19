"""Real scoring proxies/broadcasts, native warmup cleanup and actual player resets."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,LyraVerbMessage,GameplayTagContainer
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import scoring_base_mixin as policy
from .scoring_base_contract import CASES,PROFILES,require,validate

TDM='/ShooterCore/Elimination/B_TeamDeathMatchScoring.B_TeamDeathMatchScoring_C'
FIXTURE='/Game/UEPValidation/BP_ScoringBaseFixture.BP_ScoringBaseFixture_C'


def path(value):return value.get_path_name() if valid(value) else None
def count(component,name):return sum(policy.evidence(component)[p+'_'+name] for p in ('python','fallback'))


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,message_cases=[],lifetime_cases=[],warmup_cases=[],reset_cases=[],spawning_skip_cases=[]);self.components=[];self.proxies=[];self.index=0;self.units=[];self.pending=None
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','python_subscription_roots_added','native_proxy_cancelled_by_fixture','health_properties_written'):self.report[k]=False
    def all_proxies(self):return {path(p):p for p in ue.tobject_iterator(ue.find_class('AsyncAction_ListenForGameplayMessage')) if valid(p)}
    def gi(self):return {path(p) for p in self.game.get_property('ReferencedObjects') if valid(p) and p.is_a(ue.find_class('AsyncAction_ListenForGameplayMessage'))}
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.game=self.statics.call_function('GetGameInstance',self.world);self.state=self.statics.call_function('GetGameState',self.world)
        self.base=ue.load_class(policy.CLASS);self.cls=ue.load_class(FIXTURE);ue.register_declared_mixin(self.base)
        self.fixture_class_root=not self.cls.is_rooted()
        if self.fixture_class_root:self.cls.add_to_root()
        self.real=self.state.get_component_by_type(ue.load_class(TDM));require(valid(self.real),'actual TDM component absent');self.report['natural_child_begin_python']=policy.evidence(self.real)['python_begin'];self.report['natural_child_warmup_python']=policy.evidence(self.real)['python_warmup'];self.target_score=self.real.get_property('TargetScore');self.real.set_property('TargetScore',2000000000)
        self.team=policy.teams(self.state);self.team_ids=sorted(native_outputs('LyraTeamSubsystem','GetTeamIDs',self.team.call_function('GetTeamIDs'))['ReturnValue']);require(len(self.team_ids)>=2,'actual two-team world required')
        self.router=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'));self.sender=ue.load_class('/Game/UEPValidation/BP_MusicListenerProbe.BP_MusicListenerProbe_C').get_cdo();self.sender_root=not self.sender.is_rooted()
        if self.sender_root:self.sender.add_to_root()
        self.units=[self.unit(i) for i in (0,1)];self.start_messages()
    def unit(self,index):
        controller=self.world.actor_spawn(ue.find_class('LyraPlayerController'));state=controller.get_property('PlayerState');pawn=self.world.actor_spawn(ue.find_class('LyraCharacter'),ue.FVector(250000.+index*10000.,250000.,3000.));self.actors.extend((controller,state,pawn));controller.call_function('Possess',pawn)
        manager=ue.new_object(ue.find_class('CheatManager'),controller);cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager);cheats.call_function('SetTeam',self.team_ids[index]);return dict(controller=controller,state=state,pawn=pawn,manager=manager,cheats=cheats)
    def component(self,profile):
        before=set(self.all_proxies());component=ue.new_object(self.cls,self.state);self.components.append(component);ue.set_mixin_profile(component,profile);component.register_component();component.call_function('SetComponentTickEnabled',False)
        added=[p for name,p in self.all_proxies().items() if name not in before];self.proxies.extend(added);require(count(component,'begin')==1 and len(added)==2,'natural base BeginPlay must create exactly two native proxies');return component,added
    def values(self):
        tags=('ShooterGame.Score.Eliminations','ShooterGame.Score.Deaths','ShooterGame.Score.Assists')
        return [int(u['state'].call_function('GetStatTagStackCount',policy.tag(t))) for u in self.units for t in tags]+[int(self.team.call_function('GetTeamTagStackCount',i,policy.tag(tags[0]))) for i in self.team_ids[:2]]
    def restore_scores(self,before):
        after=self.values();tags=('ShooterGame.Score.Eliminations','ShooterGame.Score.Deaths','ShooterGame.Score.Assists')
        for i,u in enumerate(self.units):
            for j,t in enumerate(tags):
                n=after[i*3+j]-before[i*3+j]
                if n:u['state'].call_function('RemoveStatTagStack' if n>0 else 'AddStatTagStack',policy.tag(t),abs(n))
        for j,team in enumerate(self.team_ids[:2]):
            n=after[6+j]-before[6+j]
            if n:self.team.call_function('RemoveTeamTagStack' if n>0 else 'AddTeamTagStack',team,policy.tag(tags[0]),abs(n))
        require(self.values()==before,'owned score deltas not restored')
    def broadcast(self,channel,source,target):self.sender.call_function('BroadcastVerb',self.router,policy.tag(channel),LyraVerbMessage(Instigator=source,Target=target,Magnitude=-17.))
    def start_messages(self):
        self.profile=PROFILES[self.index];self.current,self.added=self.component(self.profile)
        sources=dict(ps0=self.units[0]['state'],ps1=self.units[1]['state'],pawn0=self.units[0]['pawn'],pawn1=self.units[1]['pawn'],null=None)
        for name,channel,a,b in CASES:
            before=self.values();counts={k:count(self.current,k) for k in ('elimination','assist')};real={k:count(self.real,k) for k in counts}
            self.broadcast(channel,sources[a],sources[b]);after=self.values();delta=[x-y for x,y in zip(after,before)]
            self.report['message_cases'].append(dict(name=name,profile=self.profile,delta=delta,fixture_callbacks={k:count(self.current,k)-v for k,v in counts.items()},real_child_callbacks={k:count(self.real,k)-v for k,v in real.items()}));self.restore_scores(before)
        keys={path(p) for p in self.added};self.current.call_function('K2_DestroyComponent',self.state);self.pending=dict(profile=self.profile,native_proxies=2,keys=keys);self.gc_frames=0;policy.lib('KismetSystemLibrary').call_function('CollectGarbage');self.enter('gc')
    def after_gc(self):
        self.gc_frames+=1
        if self.gc_frames<3:return
        self.broadcast('Lyra.Elimination.Message',None,None);self.broadcast('Lyra.Assist.Message',None,None)
        released=not self.pending['keys'].intersection(self.gi());require(released,'destroyed scoring proxies still GI-referenced after GC/matching broadcasts')
        self.report['lifetime_cases'].append(dict(profile=self.profile,native_proxies=2,gi_refs_released=True,engine_gc_frames=self.gc_frames));self.pending=None;self.index+=1
        if self.index<len(PROFILES):self.start_messages()
        else:
            for u in self.units:
                for key in ('pawn','controller','state'):
                    if not dead(u[key]):u[key].actor_destroy()
            self.units=[];self.index=0;self.start_warmup()
    def start_warmup(self):
        profile=PROFILES[self.index];self.control,self.control_proxies=self.component(profile)
        transform=ue.FTransform();transform.translation=ue.FVector(250000.,250000.,3000.)
        spawner=self.statics.call_function('BeginDeferredActorSpawnFromClass',self.world,ue.load_class(policy.SPAWNER),transform,1,None);self.actors.append(spawner)
        definition=ue.load_object(ue.find_class('LyraWeaponPickupDefinition'),'/ShooterCore/Weapons/Rifle/WeaponPickupData_Rifle.WeaponPickupData_Rifle');spawner.set_property('WeaponDefinition',definition);self.statics.call_function('FinishSpawningActor',spawner,transform);spawner.set_property('bIsWeaponAvailable',False)
        grenade=self.world.actor_spawn(ue.load_class(policy.GRENADE),ue.FVector(250000.,250000.,3000.));self.actors.append(grenade);self.control.call_function('PostWarmup')
        self.report['warmup_cases'].append(dict(profile=profile,spawner_available=bool(spawner.get_property('bIsWeaponAvailable')),grenade_destroyed=dead(grenade),callback_entries=count(self.control,'warmup')))
        spawner.actor_destroy();self.eligibility_started=time.monotonic();self.skip_checked=False;self.enter('reset-eligible')
    def reset_eligible(self):
        require(time.monotonic()-self.eligibility_started<40.,'scoring reset eligibility did not return')
        pawn=self.controller.get_controlled_pawn();asc=ability_system(pawn) if valid(pawn) else None
        if not valid(asc):return
        spawning=bool(asc.call_function('HasMatchingGameplayTag',policy.tag('Status.SpawningIn')))
        self.report['pending_reset_eligibility']=dict(profile=PROFILES[self.index],pawn=path(pawn),spawning=spawning)
        if spawning:
            if not self.skip_checked:
                before=path(pawn);self.control.call_function('ResetAllActivePlayers');self.report['spawning_skip_cases'].append(dict(profile=PROFILES[self.index],tag_present=True,same_pawn=path(self.controller.get_controlled_pawn())==before));self.skip_checked=True
            return
        self.reset_old=path(pawn);self.reset_started=time.monotonic();self.control.call_function('ResetAllActivePlayers');self.enter('reset')
    def observe_reset(self):
        require(time.monotonic()-self.reset_started<40.,'scoring reset did not produce a ready new native Pawn')
        pawn=self.controller.get_controlled_pawn()
        if not valid(pawn) or path(pawn)==self.reset_old:return
        health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'));asc=ability_system(pawn)
        if not valid(health) or not valid(asc) or health.call_function('IsDeadOrDying') or health.call_function('GetHealth')<=0:return
        bridge=policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world);snapshot=bridge.call_function('CaptureSnapshot')
        if not (snapshot.bAbilitySystemReady and snapshot.bHealthReady):return
        self.report['reset_cases'].append(dict(profile=PROFILES[self.index],old_pawn=self.reset_old,new_pawn=path(pawn),health=float(health.call_function('GetHealth')),death=int(health.call_function('GetDeathState')),native_asc_bound=True,callback_entries=count(self.control,'reset'),spawning_skip_calls=int(self.skip_checked)))
        self.control.call_function('K2_DestroyComponent',self.state);self.index+=1
        if self.index<len(PROFILES):self.start_warmup()
        else:self.enter('final-gc');self.gc_frames=0;policy.lib('KismetSystemLibrary').call_function('CollectGarbage')
    def final_gc(self):
        self.gc_frames+=1
        if self.gc_frames<3:return
        self.broadcast('Lyra.Elimination.Message',None,None);self.broadcast('Lyra.Assist.Message',None,None);self.report['owned_native_proxy_gi_refs_released']=not {path(p) for p in self.proxies if valid(p)}.intersection(self.gi());self.finish()
    def cleanup(self):
        for c in self.components:
            if valid(c):c.call_function('K2_DestroyComponent',self.state)
        for actor in self.actors:
            if not dead(actor):actor.actor_destroy()
        if hasattr(self,'real') and valid(self.real):self.real.set_property('TargetScore',self.target_score)
        if getattr(self,'sender_root',False) and valid(self.sender):self.sender.remove_from_root();self.sender_root=False
        if getattr(self,'fixture_class_root',False) and valid(self.cls):self.cls.remove_from_root();self.fixture_class_root=False
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),owned_components_destroyed=all(not valid(c) for c in self.components),diagnostic_sender_root_removed=not getattr(self,'sender_root',False),actual_tdm_target_score_restored=hasattr(self,'real') and valid(self.real) and self.real.get_property('TargetScore')==self.target_score)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'native scoring total timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='gc':self.after_gc()
            elif self.phase=='reset-eligible':self.reset_eligible()
            elif self.phase=='reset':self.observe_reset()
            elif self.phase=='final-gc':self.final_gc()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SCORING_BASE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SCORING_BASE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPScoringBaseResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
