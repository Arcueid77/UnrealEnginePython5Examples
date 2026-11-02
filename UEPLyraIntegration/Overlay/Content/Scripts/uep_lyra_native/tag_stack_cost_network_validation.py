"""Original predicted weapon firing plus a temporary native player-cost consumer."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons import weapon_ability_fire_network_validation as firing
from . import tag_stack_costs as policy
from .message_validation_contract import require

firing.PLAN=tuple((owner,profile) for owner in firing.PEERS for profile in ('NativeCostFallback','Python'))
TAG=GameplayTag(TagName='Lyra.ShooterGame.Weapon.MagazineAmmo')


def count(state):return int(state.call_function('GetStatTagStackCount',TAG))
def set_count(state,value):
    old=count(state)
    if old!=value:state.call_function('AddStatTagStack' if value>old else 'RemoveStatTagStack',TAG,abs(value-old))


class Costs:
    def init_witness(self,*args):
        super().init_witness(*args);self.cost_edits=[];self.cost_before={};self.player_originals={};self.original_player=None;self.lifecycle_required='-UEPNativeCostLifecycle' in sys.argv;self.lifecycle=None
        self.report.update(previous_weapon_policy_fixed='Python',player_cost_capability_fixture=True,original_player_consumer_claimed=False,client_player_stacks_written=False,cost_arrays_restored=False,player_stacks_restored=False)
        self.report.update(player_cost_lifecycle_required=self.lifecycle_required,native_player_cost_lifecycle=[],lifecycle_avatar_changed=False,lifecycle_player_state_preserved=False)
        if self.lifecycle_required:require(self.weapon=='pistol','bounded native cost lifecycle fixture requires the original pistol inventory')

    def select_profile(self,ability,profile):
        if not any(value[0]==ability for value in self.cost_edits):
            original=ability.get_property('AdditionalCosts');require(len(original)==1 and original[0].is_a(ue.find_class('LyraAbilityCost_ItemTagStack')),'original configured weapon cost differs')
            player=ue.new_object(ue.find_class('LyraAbilityCost_PlayerTagStack'),ability);player.set_property('Tag',TAG)
            ability.set_property('AdditionalCosts',original+[player]);require(len(ability.get_property('AdditionalCosts'))==2,'temporary native player-cost attachment failed');self.cost_edits.append((ability,original))
        self.cost_before=copy.deepcopy(policy.metrics(ability));super().select_profile(ability,profile)

    def snapshot(self):
        row=super().snapshot();ability=firing.ability_for(self.source,ue.load_class(firing.WEAPONS[self.weapon])) if self.peer in ('server',self.command['owner']) else None
        if ability is not None:
            values=policy.metrics(ability);row['cost_metrics']={k:values[k]-self.cost_before[k] for k in ('python_routes','native_routes','checks','applications')};row['cost_contexts']=copy.deepcopy(values['contexts'][len(self.cost_before['contexts']):])
        else:row.update(cost_metrics=None,cost_contexts=[])
        if self.peer=='server':row.update(player_counts_before=self.command['player_counts_before'],player_counts_after={p:count(v['controller'].PlayerState) for p,v in self.owners.items()})
        else:row.update(own_player_before=self.command['player_counts_before'][self.peer],own_player_after=count(self.controller.PlayerState))
        return row

    def close_observers(self):
        restored=True
        for ability,original in self.cost_edits:
            if valid(ability):ability.set_property('AdditionalCosts',original);restored&=ability.get_property('AdditionalCosts')==original
        self.report['cost_arrays_restored']=restored
        self.report['player_stacks_restored']=all(count(self.owners[p]['controller'].PlayerState)==n for p,n in self.player_originals.items()) if self.peer=='server' else self.original_player is not None and count(self.controller.PlayerState)==self.original_player
        if self.lifecycle_required:
            if self.peer=='server' and self.setup_done:self.report['post_lifecycle_native_inventory_final']={p:firing.capture(v['controller']) for p,v in self.owners.items()}
            elif self.peer!='server':self.report['post_lifecycle_native_inventory_final']=firing.capture(self.controller)
        super().close_observers()

    def finalize(self):
        super().finalize()
        if self.report['status']=='passed' and not (self.report['cost_arrays_restored'] and self.report['player_stacks_restored']):self.report.update(status='failed',error='cost array/player stat cleanup failed')
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_COST_NETWORK_SHUTDOWN_'+self.report['status'].upper())


class Client(Costs,firing.Client):
    def begin(self):
        self.original_player=count(self.controller.PlayerState);self.initial_player_state=self.controller.PlayerState;self.initial_pawn_path=self.controller.get_controlled_pawn().get_path_name();super().begin()
    def prepare(self):
        if count(self.controller.PlayerState)!=self.command['player_counts_before'][self.peer]:return False
        if self.lifecycle_required:
            pawn=self.controller.get_controlled_pawn()
            if not firing.binding_ready(pawn):return False
            self.report['lifecycle_player_state_preserved']=self.controller.PlayerState==self.initial_player_state
            # Comparison expectation from the native post-lifecycle baseline;
            # this is never applied to any game object.
            self.original_model=copy.deepcopy(self.command['post_lifecycle_inventory_baselines'][self.peer])
            self.report['post_lifecycle_inventory_baseline']=copy.deepcopy(self.original_model)
            if pawn.get_path_name()!=self.initial_pawn_path:
                # Keep the original native full-magazine baseline. The firing
                # trial has already arranged a half-magazine at this point.
                self.pawn=pawn;self.report['lifecycle_avatar_changed']=True
        return super().prepare()
    def collect(self):
        require(time.monotonic()-self.prepare_started<30.,'native player tag replication timed out')
        expected=self.command['player_counts_before'][self.peer]-(self.peer==self.command['owner'])
        if count(self.controller.PlayerState)!=expected:return
        super().collect()
    def tick(self,seconds):
        if self.original_player is not None and not self.finished:
            command=firing.token(self.root,'fire-command.json',self.run)
            if command is not None and command['stage']=='complete' and count(self.controller.PlayerState)!=self.original_player:
                if time.monotonic()-self.started>500.:self.finish('native player stack restoration timed out');return False
                return True
        return super().tick(seconds)


class Server(Costs,firing.Server):
    def lifecycle_ready(self):
        marker=GameplayTag(TagName='Lyra.ShooterGame.Weapon.SpareAmmo')
        def get(state):return int(state.call_function('GetStatTagStackCount',marker))
        if self.lifecycle is None:
            ready={p:firing.token(self.root,p+'-ready.json',self.run) for p in firing.PEERS}
            if not all(ready.values()):return False
            first=self.report['native_playing_gate']['stable_authority_pawns'][0][1];world=ue.find_object(first).get_world();controllers,=self.statics.call_function('GetAllActorsOfClass',world,ue.find_class('LyraPlayerController'))
            owners={p:next((c for c in controllers if valid(c.PlayerState) and int(c.PlayerState.PlayerId)==r['player_id']),None) for p,r in ready.items()}
            if not all(owners.values()) or not all(firing.binding_ready(c.get_controlled_pawn()) for c in owners.values()):return False
            peer=next(p for p,c in owners.items() if c.get_controlled_pawn().get_path_name()!=first);controller=owners[peer];state=controller.PlayerState
            self.lifecycle=dict(peer=peer,controller=controller,state=state,marker_before=get(state),stage='death_start',started=time.monotonic());state.call_function('AddStatTagStack',marker,3)
        life=self.lifecycle;require(time.monotonic()-life['started']<90.,'native cost respawn/avatar transition timed out: '+life['stage'])
        controller,state=life['controller'],life['state'];pawn=controller.get_controlled_pawn()
        if life['stage']=='complete':return True
        if life['stage'] in ('death_start','avatar_start'):
            if not firing.binding_ready(pawn):return False
            life['old_pawn']=pawn.get_path_name();life['kind']='lethal_death' if life['stage']=='death_start' else 'forced_avatar_endplay'
            if life['stage']=='death_start':
                from uep_lyra_abilities import death_damage
                death_damage.apply(firing.ability_system(pawn),firing.health_value(pawn));require(firing.health_value(pawn)==0.,'native lethal GAS damage did not execute')
                life['stage']='death_wait'
            else:pawn.call_function('K2_DestroyActor');life['stage']='avatar_wait'
            return False
        if not valid(pawn) or pawn.get_path_name()==life['old_pawn'] or not firing.binding_ready(pawn):return False
        require(controller.PlayerState==state and get(state)==life['marker_before']+3,'native PlayerState/stat identity changed across Pawn replacement')
        recovery=[]
        if life['stage']=='avatar_wait' and not life.get('recovered'):
            quickbar=firing.services(controller)[1];active=int(quickbar.call_function('GetActiveSlotIndex'));empty=int(quickbar.call_function('GetNextFreeItemSlot'));slots=quickbar.call_function('GetSlots')
            if firing.ability_for(pawn,ue.load_class(firing.WEAPONS[self.weapon])) is None:
                require(0<=active<len(slots) and slots[active] is not None and 0<=empty<len(slots) and empty!=active and slots[empty] is None,'original forced-avatar equipment recovery requires an occupied and empty slot')
                quickbar.call_function('SetActiveSlotIndex',empty);quickbar.call_function('SetActiveSlotIndex',active);recovery=[empty,active];require(slots==quickbar.call_function('GetSlots'),'native avatar equipment recovery changed inventory')
            life['recovered']=True;life['recovery']=recovery
        if firing.capture(controller) is None or firing.ability_for(pawn,ue.load_class(firing.WEAPONS[self.weapon])) is None:return False
        self.report['native_player_cost_lifecycle'].append(dict(kind=life['kind'],peer=life['peer'],old_pawn=life['old_pawn'],new_pawn=pawn.get_path_name(),player_state_preserved=True,marker_stacks_preserved=True,native_avatar_binding=True,native_quickbar_recovery=life.get('recovery',[]),asc_binding_repaired=False))
        if life['stage']=='death_wait':life['stage']='avatar_start';return False
        state.call_function('RemoveStatTagStack',marker,3);require(get(state)==life['marker_before'],'native lifecycle marker not restored');life['stage']='complete';return True

    def setup(self):
        if self.lifecycle_required and not self.lifecycle_ready():return
        done=self.setup_done;super().setup()
        if self.setup_done and not done:
            self.player_originals={p:count(v['controller'].PlayerState) for p,v in self.owners.items()}
            for value in self.owners.values():set_count(value['controller'].PlayerState,5)
    def publish(self,stage):
        if stage=='prepare':
            self.command['player_counts_before']={p:count(v['controller'].PlayerState) for p,v in self.owners.items()}
            if self.lifecycle_required:
                self.command['post_lifecycle_inventory_baselines']=copy.deepcopy(self.original_models)
                self.report['post_lifecycle_inventory_baselines']=copy.deepcopy(self.original_models)
        super().publish(stage)
    def restore(self):
        for peer,n in self.player_originals.items():set_count(self.owners[peer]['controller'].PlayerState,n)
        super().restore()


result,peer,run=firing.arg('-UEPWeaponAbilityFireNetworkResult='),firing.arg('-UEPJumpPeer='),firing.arg('-UEPJumpRun=')
validation=Server(result,run) if peer=='server' else Client(result,peer,run)
atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
