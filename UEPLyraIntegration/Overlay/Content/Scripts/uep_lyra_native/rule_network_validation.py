"""Authority damage/real client health or native GameMode spawn/owner validation."""
import atexit
import copy
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities.death_damage import DAMAGE
from . import reset_network_validation as reset,rule_policies

original=reset.original
FAMILY=original.arg('-UEPNativeRuleNetworkFamily=')
reset.ORDER=(FAMILY+'Native',FAMILY+'Python');original.PLAN=('native-reset-live',);original.TRIALS=2;original.TOTAL=4


def array(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value
def health(pawn):return float(pawn.get_component_by_type(ue.find_class('LyraHealthComponent')).call_function('GetHealth'))
def pawn_class(pawn):return pawn.get_class().get_path_name()
def find_pawn(value,player_id):
    pawns=array(value.statics.call_function('GetAllActorsOfClass',value.world,ue.find_class('LyraCharacter')))
    matches=[p for p in pawns if original.valid(p) and original.valid(p.PlayerState) and int(p.PlayerState.PlayerId)==player_id]
    return matches[0] if len(matches)==1 else None


class Client(reset.Client):
    def __init__(self,*args):super().__init__(*args);self.report.update(rule_family=FAMILY,rule_views=[],damage_views=[])
    def arm(self,command):
        expected=original.token(self.root,'rule-expected.json',self.run,command['position'])
        if expected is None:return
        pawn=find_pawn(self,expected['player_id'])
        if not original.valid(pawn):return
        before=self.position;self.rule_expected=expected;self.rule_old=pawn.get_path_name();super().arm(command)
        if self.position!=before:self.report['rule_views'].append(dict(position=self.position,profile=reset.ORDER[self.index%2],old_pawn=self.rule_old))
    def after_view(self):
        pawn=find_pawn(self,self.rule_expected['player_id'])
        if not original.valid(pawn) or pawn.get_path_name()==self.rule_old:return False
        self.report['rule_views'][-1].update(new_pawn=pawn.get_path_name(),new_class=pawn_class(pawn));return True
    def complete_reset(self):
        if not self.after_view():return
        super().complete_reset()
    def before_foreign_ack(self):return self.after_view()
    def tick(self,delta):
        if FAMILY=='Damage' and self.position>=0 and getattr(self,'damage_seen',-1)!=self.position:
            message=original.token(self.root,'damage-applied.json',self.run,self.position)
            if message is not None:
                pawn=find_pawn(self,message['player_id'])
                if original.valid(pawn) and abs(health(pawn)-message['health'])<.0001:
                    self.report['damage_views'].append(dict(position=self.position,target_pawn=pawn.get_path_name(),health=health(pawn),native_client_state=True))
                    self.damage_seen=self.position;atomic_write(self.root/(self.peer+'-damage-ack.json'),dict(run_id=self.run,position=self.position))
        return super().tick(delta)
    def finalize(self):
        super().finalize();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_RULE_NETWORK_SHUTDOWN_'+self.report['status'].upper())


class Server(reset.Server):
    def __init__(self,*args):super().__init__(*args);self.report.update(rule_family=FAMILY,rule_cases=[])
    def prepare(self):
        super().prepare()
        if self.phase!='armed':return
        self.pawn_rule_before=copy.deepcopy(rule_policies.metrics(self.policy_host))
        fixture=ue.find_class('UEPNativeRuleFixture').get_cdo();mode=self.statics.call_function('GetGameMode',self.world)
        selected=fixture.call_function('PawnData',mode,self.controller);expected_class=selected.get_property('PawnClass').get_path_name()
        self.rule_record=dict(position=self.position,profile=reset.ORDER[self.index%2],expected_class=expected_class,pawn_data_matches_state=selected==self.controller.PlayerState.get_property('PawnData'),null_controller_rejected=not fixture.call_function('RestartAllowed',mode,None))
        atomic_write(self.root/'rule-expected.json',dict(run_id=self.run,position=self.position,player_id=int(self.controller.PlayerState.PlayerId),expected_class=expected_class))
    def team(self,actor):return int(ue.find_class('LyraTeamStatics').get_cdo().call_function('FindTeamFromObject',actor,False)[1])
    def set_team(self,team_id):
        manager=ue.new_object(ue.find_class('CheatManager'),self.controller);cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager);cheats.call_function('SetTeam',team_id)
        original.require(self.team(self.controller.PlayerState)==team_id,'native scoped team change failed')
    def apply_damage(self,source,target):
        asc=original.ability_system(source);context=asc.call_function('MakeEffectContext');spec=asc.call_function('MakeOutgoingSpec',ue.load_class(DAMAGE),1.,context)
        spec=ue.find_class('AbilitySystemBlueprintLibrary').get_cdo().call_function('AssignTagSetByCallerMagnitude',spec,GameplayTag(TagName='SetByCaller.Damage'),10.)
        asc.call_function('BP_ApplyGameplayEffectSpecToTarget',spec,original.ability_system(target))
    def begin_reset(self):
        if FAMILY!='Damage':super().begin_reset();return
        self.rule_before=copy.deepcopy(rule_policies.metrics(self.policy_host))
        source=self.other.get_controlled_pawn();target=self.controller.get_controlled_pawn();before=health(target)
        teams=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'))
        fixture=ue.find_class('UEPNativeRuleFixture').get_cdo();original_team=self.team(self.controller.PlayerState);source_team=self.team(self.other.PlayerState)
        ids=list(teams.call_function('GetTeamIDs'));enemy_team=next(int(t) for t in ids if int(t)!=source_team)
        try:
            self.set_team(source_team);friendly=bool(fixture.call_function('DamageAllowed',teams,source,target,False));self.apply_damage(source,target);friendly_after=health(target)
            self.set_team(enemy_team);enemy=bool(fixture.call_function('DamageAllowed',teams,source,target,False));self.apply_damage(source,target);enemy_after=health(target)
        finally:self.set_team(original_team)
        original.require(not friendly and enemy and friendly_after==before and abs(before-enemy_after-10.)<.0001,'real native friendly/enemy damage rule differs')
        self.rule_record['damage']=dict(before=before,friendly_after=friendly_after,enemy_after=enemy_after,friendly_allowed=friendly,enemy_allowed=enemy,team_restored=self.team(self.controller.PlayerState)==original_team)
        atomic_write(self.root/'damage-applied.json',dict(run_id=self.run,position=self.position,player_id=int(self.controller.PlayerState.PlayerId),health=enemy_after));self.enter('damage-wait')
    def complete_reset(self):
        pawn=self.controller.get_controlled_pawn();self.rule_record['new_class']=pawn_class(pawn)
        if FAMILY=='Damage':
            after=rule_policies.metrics(self.policy_host);self.rule_record['damage_policy_calls']=after['applied'].get('Damage.CanCause',0)-self.rule_before['applied'].get('Damage.CanCause',0)
        after=rule_policies.metrics(self.policy_host);self.rule_record['pawn_policy_calls']=sum(v-self.pawn_rule_before['applied'].get(k,0) for k,v in after['applied'].items() if k.startswith('Pawn.'))
        self.report['rule_cases'].append(copy.deepcopy(self.rule_record));super().complete_reset()
    def tick(self,delta):
        try:
            if self.phase=='damage-wait':
                original.require(original.time.monotonic()-self.phase_started<15.,'independent client health replication was not observed')
                if all(original.token(self.root,p+'-damage-ack.json',self.run,self.position) is not None for p in original.PEERS):super().begin_reset()
            return super().tick(delta)
        except Exception:self.finish(traceback.format_exc());return False
    def finalize(self):
        super().finalize();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_RULE_NETWORK_SHUTDOWN_'+self.report['status'].upper())


result,peer,run=(original.arg(flag) for flag in ('-UEPAutoRespawnResetNetworkResult=','-UEPJumpPeer=','-UEPJumpRun='))
validation=Server(result,run) if peer=='server' else Client(result,peer,run)
atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
