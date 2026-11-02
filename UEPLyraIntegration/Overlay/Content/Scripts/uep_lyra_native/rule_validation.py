"""Original callbacks, memory replay streamer, audio calls and native game queries."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system,valid
from uep_lyra_abilities.death_damage import DAMAGE
from . import global_policy,rule_policies


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def array(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value
def path(value):return value.get_path_name() if valid(value) else None
def require(value,message):
    if not value:raise AssertionError(message)


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeRuleResult'));self.family=arg('UEPNativeRuleFamily');self.profile=arg('UEPNativeRuleProfile');self.started=time.monotonic();self.finished=False;self.phase='ready';self.actors=[]
        self.cls=ue.load_class(global_policy.CLASS);ue.register_declared_mixin(self.cls);self.cdo=self.cls.get_cdo();self.original_profile=self.cdo.get_property('PythonMixinProfile');self.cdo.set_property('PythonMixinProfile',self.profile)
        self.statics=ue.find_class('GameplayStatics').get_cdo();self.fixture=ue.find_class('UEPNativeRuleFixture').get_cdo()
        self.report=dict(status='running',error=None,family=self.family,profile=self.profile,physical_input_tested=False,online_service_tested=False,network_acceptance=False,audio_playback_tested=False)
    def enter(self,phase):self.phase=phase;self.since=time.monotonic()
    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
            bridge=ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot')
            if not(snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
            self.world=world;self.controller=self.statics.call_function('GetPlayerController',world,0);self.pawn=self.controller.get_controlled_pawn();self.bridge=bridge
            self.host=ue.find_class('UEPNativeGameplayPolicySubsystem').get_cdo().call_function('GetPolicyForContext',world)
            require(str(ue.get_mixin_profile(self.host))==self.profile,'rule startup profile did not select')
            isolate_bots(self.statics,world,ue.find_class('AIController'))
            getattr(self,'test_'+self.family.lower())();return
    def test_device(self):
        layouts=[w for w in ue.tobject_iterator(ue.find_class('LyraHUDLayout')) if valid(w) and w.call_function('GetOwningPlayer')==self.controller]
        if not layouts:return
        self.layout=layouts[0];self.device_tags=self.fixture.call_function('EnableDeviceFixture',self.layout)
        self.report['device_callback_inputs_supplied_by_fixture']=True
        self.report['unrelated_connection_ignored']=not self.fixture.call_function('DeviceEvent',self.layout,1)
        self.report['owner_connection_scheduled']=bool(self.fixture.call_function('DeviceEvent',self.layout,0))
        self.report['duplicate_notification_coalesced']=bool(self.fixture.call_function('DeviceEvent',self.layout,0))
        self.enter('device-owner')
    def device_step(self):
        if self.fixture.call_function('DevicePending',self.layout):return
        if self.phase=='device-owner':
            self.report['native_process_tick_finished']=True
            self.report['unrelated_pairing_ignored']=not self.fixture.call_function('DeviceEvent',self.layout,4)
            self.report['new_owner_pairing_scheduled']=bool(self.fixture.call_function('DeviceEvent',self.layout,2));self.enter('device-new')
        elif self.phase=='device-new':
            self.report['old_owner_pairing_scheduled']=bool(self.fixture.call_function('DeviceEvent',self.layout,3));self.enter('device-old')
        else:
            self.fixture.call_function('RestoreDeviceFixture',self.layout,self.device_tags);self.device_tags=None;self.report['device_traits_restored']=True;self.finish()
    def test_replay(self):
        self.report['replays']=[]
        for keep in (0,1,2,5):
            result=self.fixture.call_function('ReplayRetention',self.world,keep)
            self.report['replays'].append(dict(keep=keep,created=int(result.Created),remaining=int(result.Remaining),failure_stopped=bool(result.bNativeFailureStopped),temporary_memory_only=bool(result.bTemporaryMemoryStreamsOnly),cleaned=bool(result.bCleaned)))
        self.finish()
    def test_audio(self):
        audio=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',self.world,ue.find_class('LyraAudioMixEffectsSubsystem'))
        require(valid(audio),'original audio mix subsystem missing')
        self.report['audio_range_calls']=[True,False,True,False]
        for hdr in self.report['audio_range_calls']:self.fixture.call_function('AudioRange',audio,hdr)
        self.report['audio_loading_calls']=[False,True,True,False,False]
        for wanted in self.report['audio_loading_calls']:self.fixture.call_function('AudioLoading',audio,wanted)
        self.report['native_audio_state_and_readonly_chain_guards_passed']=True;self.finish()
    def damage(self,source,target,value):
        asc=ability_system(source);context=asc.call_function('MakeEffectContext');spec=asc.call_function('MakeOutgoingSpec',ue.load_class(DAMAGE),1.,context)
        spec=ue.find_class('AbilitySystemBlueprintLibrary').get_cdo().call_function('AssignTagSetByCallerMagnitude',spec,GameplayTag(TagName='SetByCaller.Damage'),float(value))
        asc.call_function('BP_ApplyGameplayEffectSpecToTarget',spec,ability_system(target))
    def team(self,actor):return int(ue.find_class('LyraTeamStatics').get_cdo().call_function('FindTeamFromObject',actor,False)[1])
    def health(self,pawn):return float(pawn.get_component_by_type(ue.find_class('LyraHealthComponent')).call_function('GetHealth'))
    def test_damage(self):
        teams=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'))
        pawns=array(self.statics.call_function('GetAllActorsOfClass',self.world,ue.find_class('LyraCharacter')))
        candidates=[p for p in pawns if valid(p) and valid(p.PlayerState) and p!=self.pawn and self.health(p)>20. and not ability_system(p).call_function('HasMatchingGameplayTag',GameplayTag(TagName='Gameplay.DamageImmunity'))]
        own_team=self.team(self.pawn);ally=next((p for p in candidates if self.team(p)==own_team),None);enemy=next((p for p in candidates if self.team(p)!=own_team and self.team(p)>=0),None)
        if not valid(ally) or not valid(enemy):return
        dummy=self.world.actor_spawn(ue.find_class('AbilitySystemTestPawn'),ue.FVector(250000.,250000.,3000.));plain=self.world.actor_spawn(ue.find_class('Actor'));self.actors += [dummy,plain]
        inputs=((self.pawn,self.pawn,False,False),(self.pawn,self.pawn,True,True),(self.pawn,ally,False,False),(self.pawn,enemy,False,True),(self.pawn,dummy,False,True),(self.pawn,plain,False,False),(None,None,False,False),(None,None,True,True))
        self.report['damage_queries']=[bool(self.fixture.call_function('DamageAllowed',teams,source,target,allow)) for source,target,allow,expected in inputs]
        require(self.report['damage_queries']==[expected for _,_,_,expected in inputs],'native team/self/ASC damage query differs')
        before_enemy,before_ally=self.health(enemy),self.health(ally)
        self.damage(self.pawn,ally,10.);self.damage(self.pawn,enemy,10.)
        self.report['actual_damage']=dict(enemy_before=before_enemy,enemy_after=self.health(enemy),ally_before=before_ally,ally_after=self.health(ally),original_gameplay_effect=DAMAGE)
        self.finish()
    def test_pawn(self):
        mode=self.statics.call_function('GetGameMode',self.world);state=self.controller.PlayerState
        selected=self.fixture.call_function('PawnData',mode,self.controller);fallback=self.fixture.call_function('PawnData',mode,None)
        bots=[c for c in ue.tobject_iterator(ue.find_class('LyraPlayerBotController')) if valid(c) and valid(c.PlayerState) and c.get_world()==self.world]
        self.report['pawn']=dict(player_state_priority=selected==state.get_property('PawnData'),selected=path(selected),experience_fallback=path(fallback),human_permission=bool(self.fixture.call_function('RestartAllowed',mode,self.controller)),bot_permissions=[bool(self.fixture.call_function('RestartAllowed',mode,b)) for b in bots],null_controller_rejected=not self.fixture.call_function('RestartAllowed',mode,None),actual_pawn_class=path(self.pawn.get_class()),selected_pawn_class=path(selected.get_property('PawnClass')))
        self.finish()
    def cleanup(self):
        if getattr(self,'device_tags',None) is not None:
            if self.fixture.call_function('DevicePending',self.layout):raise RuntimeError('cannot restore device traits while native ticker is pending')
            self.fixture.call_function('RestoreDeviceFixture',self.layout,self.device_tags)
        for actor in reversed(self.actors):
            if valid(actor):actor.actor_destroy()
        self.cdo.set_property('PythonMixinProfile',self.original_profile);self.report['selector_restored']=self.cdo.get_property('PythonMixinProfile')==self.original_profile
        self.report['owned_actors_destroyed']=all(not valid(actor) for actor in self.actors)
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        if hasattr(self,'host'):self.report['rule_metrics']=copy.deepcopy(rule_policies.metrics(self.host))
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_RULE_'+('FAILED '+error if error else 'READY'));ue.request_exit()
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<180.,'native rule runtime timeout: '+self.phase)
            if self.phase=='ready':self.ready()
            else:self.device_step()
            atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            self.report['status']='passed'
            try:
                from .rule_validation_contract import validate
                validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report)
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_RULE_SHUTDOWN_'+self.report['status'].upper())


validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
