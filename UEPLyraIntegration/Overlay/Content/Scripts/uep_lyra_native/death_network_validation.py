"""Native lethal death sequencing and Jump cancellation/new-Avatar crosschecks."""
import atexit
import copy
import time
import sys
import unreal_engine as ue
from uep_lyra_abilities import death_network_validation as original
from uep_lyra_abilities import death_damage
from uep_lyra_abilities.jump_mixin import CLASS as JUMP
from . import ability_lifecycle as policy

ORDER=('NativeLifecycleFallback','Python')
SELF_DESTRUCT='-UEPNativeDeathScenario=selfdestruct' in sys.argv
if SELF_DESTRUCT:
    from uep_lyra_abilities import death_validation as base_death
    original.PLAN=base_death.PLAN=('native-self-destruct',);original.TOTAL=4


def jump(pawn):
    values=original.instances(original.ability_system(pawn),ue.load_class(JUMP));return values[0] if len(values)==1 else None
def values(owner,before):
    m=policy.metrics(owner);return {k:m[k]-before[k] for k in m if k!='trace'}


class Client(original.Client):
    def __init__(self,*args):
        super().__init__(*args);self.held_jump=False;self.cross_position=-1;self.post_jump=None;self.report['previous_blueprint_policy_fixed']='Python'
    def inject(self,pressed):self.controller.inject_enhanced_input_for_action(self.jump_action,bool(pressed))
    def before_arm_ready(self,command,pawn):
        if command['name']!='native-auto-respawn' or command['target']!=self.peer:return True
        if command['position']!=self.cross_position:
            candidate=jump(pawn)
            if candidate is None:return False
            self.cross_position=command['position'];self.cross_started=time.monotonic();self.jump_pawn=pawn;self.jump_ability=candidate;self.jump_start_z=float(pawn.get_actor_location().z);self.jump_action=ue.load_object(ue.find_class('InputAction'),'/Game/Input/Actions/IA_Jump.IA_Jump');ue.set_mixin_profile(candidate,command['profile']);self.held_jump=True;self.post_jump=None
        self.inject(True);original.require(time.monotonic()-self.cross_started<8.,'native Jump did not activate before lethal death')
        return bool(self.jump_ability.get_property('bIsActive')) and float(pawn.get_actor_location().z)-self.jump_start_z>20.
    def before_respawn_ack(self,pawn):
        if not self.is_owner or self.command['name']!='native-auto-respawn':return True
        if self.post_jump is None:
            ability=jump(pawn)
            if ability is None:return False
            ue.set_mixin_profile(ability,self.command['profile']);self.post_jump=dict(pawn=pawn,ability=ability,start_z=float(pawn.get_actor_location().z),peak=0.,stage='press',started=time.monotonic());self.inject(True);return False
        p=self.post_jump;original.require(time.monotonic()-p['started']<12.,'new Avatar native Jump did not finish/land');p['peak']=max(p['peak'],float(pawn.get_actor_location().z)-p['start_z']);active=bool(p['ability'].get_property('bIsActive'))
        if p['stage']=='press':
            if not (active and p['peak']>20.):self.inject(True);return False
            self.inject(False);p['stage']='land';return False
        if active or int(pawn.CharacterMovement.MovementMode)!=1:return False
        self.row['post_respawn_jump']=dict(peak=p['peak'],landed=True,inactive=True,pressed_after=bool(pawn.get_property('bPressedJump')),native_avatar_matches=original.ability_system(pawn).get_property('AvatarActor')==pawn)
        return True
    def tick(self,seconds):
        if self.held_jump:
            if not original.valid(self.jump_pawn) or original.health(self.jump_pawn).call_function('GetHealth')<=0:
                self.inject(False);self.held_jump=False
                if hasattr(self,'row') and self.is_owner:self.row['surviving_respawn_still_active']=bool(self.respawn_owner.get_property('bIsActive'))
            else:self.inject(True)
        return super().tick(seconds)
    def finalize(self):
        super().finalize();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_DEATH_NETWORK_SHUTDOWN_'+self.report['status'].upper())


class Server(original.Server):
    def __init__(self,*args):super().__init__(*args);self.profile_order=ORDER;self.report['previous_blueprint_policy_fixed']='Python'
    def prepare(self):
        peer=original.PEERS[self.position//(len(original.PLAN)*2)];index=self.position%(len(original.PLAN)*2);candidate=jump(self.fixture.owners[peer]['controller'].get_controlled_pawn())
        if candidate is not None:ue.set_mixin_profile(candidate,ORDER[index%2])
        super().prepare()
    def begin(self):
        candidate=jump(self.controller.get_controlled_pawn());cross=original.PLAN[self.index//2]=='native-auto-respawn'
        if cross:original.require(candidate is not None and candidate.get_property('bIsActive'),'native authority did not receive the pre-death predicted Jump')
        if SELF_DESTRUCT:
            self.protection=ue.find_class('UEPNativeProtectionFixture').get_cdo();self.witness_asc=self.asc;self.witnesses=[self.protection.call_function('GrantActive',self.asc,value) for value in (False,True)]
            original.require(all(self.protection.call_function('WitnessActive',self.asc,h) for h in self.witnesses),'native cancellation witnesses did not activate')
        self.native_before=copy.deepcopy(policy.metrics(self.ability));super().begin()
        if SELF_DESTRUCT:
            self.row.update(native_self_destruct=True,ordinary_cancelled=not bool(self.protection.call_function('WitnessActive',self.asc,self.witnesses[0])),protected_survived_death=bool(self.protection.call_function('WitnessActive',self.asc,self.witnesses[1])),fixture_witness_abilities_activated=True,damage_effect='Native LyraHealthComponent::DamageSelfDestruct')
        if cross:self.row['jump_cancelled_by_death']=not bool(candidate.get_property('bIsActive'))
        self.ability.call_function('StartDeath');self.ability.call_function('StartDeath');self.row['duplicate_start_state']=int(self.health.call_function('GetDeathState'))
    def observe(self):
        super().observe()
        if self.phase=='respawn':
            self.ability.call_function('FinishDeath');self.ability.call_function('FinishDeath');self.row['native_lifecycle_counts']=values(self.ability,self.native_before)
    def respawn(self):
        super().respawn()
        if self.phase=='ack':
            pawn=self.controller.get_controlled_pawn();self.new_jump_start=float(pawn.get_actor_location().z);self.row.update(post_jump_authority_active=False,post_jump_authority_peak=0.)
            if SELF_DESTRUCT:
                self.row['protected_survived_respawn']=bool(self.protection.call_function('WitnessActive',self.witness_asc,self.witnesses[1]));self.row['witnesses_removed']=all(self.protection.call_function('RemoveWitness',self.witness_asc,h) for h in self.witnesses);self.witnesses=[]
    def apply_lethal_damage(self,asc,amount):
        if SELF_DESTRUCT:original.require(self.protection.call_function('SelfDestruct',self.pawn),'native health self-destruct fixture failed')
        else:death_damage.apply(asc,amount)
    def finish(self,error=None):
        if getattr(self,'witnesses',None):
            for handle in self.witnesses:self.protection.call_function('RemoveWitness',self.witness_asc,handle)
            self.witnesses=[]
        super().finish(error)
    def tick(self,seconds):
        if self.phase=='ack' and self.name=='native-auto-respawn':
            pawn=self.controller.get_controlled_pawn();candidate=jump(pawn)
            if candidate is not None:
                self.row['post_jump_authority_active']|=bool(candidate.get_property('bIsActive'));self.row['post_jump_authority_peak']=max(self.row['post_jump_authority_peak'],float(pawn.get_actor_location().z)-self.new_jump_start)
        return super().tick(seconds)
    def finalize(self):
        super().finalize();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_DEATH_NETWORK_SHUTDOWN_'+self.report['status'].upper())


result,peer,run=original.arg('-UEPDeathNetworkResult='),original.arg('-UEPJumpPeer='),original.arg('-UEPJumpRun=')
validation=Server(result,run) if peer=='server' else Client(result,peer,run);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
