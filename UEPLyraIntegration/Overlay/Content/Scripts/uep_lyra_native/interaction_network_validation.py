"""Two actual owners: native scan/grant, local GAS input and predicted/server events."""
import atexit
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_hud.notification_relays_network_validation import Network as Ready,identity
from uep_lyra_abilities.auto_respawn_helpers_validation import instances
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture
from .message_validation import arg
from . import interactions as policy
from .interaction_network_contract import require,validate

INPUT=7128


class Network(Ready):
    def __init__(self):
        super().__init__(arg('UEPNativeInteractionNetworkResult'),arg('UEPNativeInteractionNetworkPeer'),arg('UEPNativeInteractionNetworkRun'))
        self.profile=arg('UEPNativeInteractionNetworkProfile');self.cls=ue.load_class(policy.CLASS);self.was_rooted=self.cls.is_rooted()
        if not self.was_rooted:self.cls.add_to_root()
        ue.register_declared_mixin(self.cls);self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');self.cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.fixture_cls=ue.find_class('UEPNativeInteractionFixture');self.witness_cls=ue.find_class('UEPNativeInteractionWitness');self.owners={};self.fixtures=[];self.isolation_at=0.;self.cleaned=False;self.cleanup_started=False
        self.report=dict(status='running',error=None,peer=self.peer,run_id=self.run,profile=self.profile,synthetic_target_events=False,target_counter_replication=False,health_writes=False,inventory_writes=False,native_interface_replaced=False,server_waited_for_client_process_exit=False)
        atexit.register(self.finalize)

    def write_token(self,name,**values):atomic_write(self.root/name,dict(run_id=self.run,**values))
    def enter(self,phase):self.stage=phase;self.phase_started=time.monotonic()
    def world_ready(self):
        if self.peer=='server' and time.monotonic()>=self.isolation_at:
            self.isolation_at=time.monotonic()+.5
            for world in ue.all_worlds():
                if world.get_world_type() in (1,3,5) and 'L_Expanse' in world.get_name():isolate_bots(self.statics,world,ue.find_class('AIController'))
        return super().world_ready()

    def setup(self):
        if self.peer!='server':
            self.controller=self.statics.call_function('GetPlayerController',self.world,0);self.pawn=self.controller.get_controlled_pawn();self.asc=ability_system(self.pawn)
            self.before_inventory=capture(self.controller);self.before_health=self.health();self.write_token(self.peer+'-ready.json',player_id=int(self.controller.PlayerState.call_function('GetPlayerId')))
        self.ready=True;self.enter('roster')

    def health(self):return float(ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').Health)
    def move(self,actor,x,y):actor.call_function('K2_SetActorLocation',NewLocation=ue.FVector(x,y,2025.),bSweep=False,bTeleport=True)
    def ability(self,asc):
        values=instances(asc,self.cls);return values[0] if len(values)==1 and values[0].get_property('bIsActive') else None
    def found(self,ability,target):return valid(ability) and len(ability.get_property('CurrentOptions'))==1 and ability.call_function('UEPGetInteractionTargetActor',ability.get_property('CurrentOptions')[0])==target
    def payload(self,target,retarget,pawn):
        event=target.LastEvent
        asc=ability_system(pawn)
        return str(event.EventTag.TagName)=='Ability.Interaction.Activate' and event.Instigator==pawn and event.Target==retarget and event.OptionalObject==target and float(event.EventMagnitude)==37. and target.SeenOwner==asc.get_property('OwnerActor') and target.SeenAvatar==pawn
    def result(self,row):return dict(trigger_count=int(row['target'].TriggerCount),customize_count=int(row['target'].CustomizeCount),foreign_trigger_count=int(row['retarget'].TriggerCount),payload_and_actor_info_match=self.payload(row['target'],row['retarget'],row['pawn']),empty_input_ignored=row['empty_ignored'],scan_found_target=True,metrics=copy.deepcopy(policy.metrics(row['ability'])))
    def input_dispatches(self,row):return policy.metrics(row['ability'])[('python_' if self.profile=='Python' else 'native_')+'trigger']

    def server_tick(self):
        if self.stage=='roster':
            tokens={p:self.token(p+'-ready.json') for p in ('A','B0')}
            if not all(tokens.values()):return
            for index,peer in enumerate(('A','B0')):
                player_id=tokens[peer]['player_id'];states=[s for s in ue.tobject_iterator(ue.find_class('LyraPlayerState')) if valid(s) and int(s.call_function('GetPlayerId'))==player_id]
                require(len(states)==1,'one native owner PlayerState required');controller=states[0].call_function('GetOwner');pawn=controller.get_controlled_pawn();asc=ability_system(pawn);require(valid(asc),'native owner ASC missing')
                x=200000.+index*10000.;y=200000.;pawn.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0)
                pawn.call_function('K2_SetActorLocation',NewLocation=ue.FVector(x,y,2000.),bSweep=False,bTeleport=True);controller.call_function('SetControlRotation',ue.FRotator())
                target=self.world.actor_spawn(self.fixture_cls);retarget=self.world.actor_spawn(self.fixture_cls);self.fixtures.extend((target,retarget));self.move(target,x+150.,y);self.move(retarget,x+150.,y+300.)
                target.set_property('Retarget',retarget);target.set_property('bCustomizePayload',True)
                baseline={int(s.Handle.Handle) for s in asc.get_property('ActivatableAbilities').Items};handle=asc.call_function('K2_GiveAbility',self.cls,1,INPUT)
                self.owners[peer]=dict(controller=controller,pawn=pawn,asc=asc,target=target,retarget=retarget,baseline=baseline,handle=handle,x=x,y=y,empty_ignored=False)
            self.enter('spawned')
        elif self.stage=='spawned':
            rows={p:dict(target=identity(r['target']),retarget=identity(r['retarget']),x=r['x'],y=r['y']) for p,r in self.owners.items()}
            if any(not r['target'] or not r['retarget'] for r in rows.values()):return
            self.write_token('fixtures.json',owners=rows);self.enter('scan')
        elif self.stage=='scan':
            for row in self.owners.values():
                row['ability']=self.ability(row['asc'])
                if not self.found(row['ability'],row['target']):return
            if not all(self.token(p+'-scan-ready.json') for p in ('A','B0')):return
            self.write_token('press-go.json');self.enter('first')
        elif self.stage=='first':
            if not all(int(r['target'].TriggerCount)==1 for r in self.owners.values()) or not all(self.token(p+'-first.json') for p in ('A','B0')):return
            if not all(self.input_dispatches(r)>=1 for r in self.owners.values()):return
            for row in self.owners.values():require(self.payload(row['target'],row['retarget'],row['pawn']),'authority customized native payload differs');self.move(row['target'],row['x']+350.,row['y'])
            self.write_token('moving-out.json');self.enter('empty-scan')
        elif self.stage=='empty-scan':
            if any(r['ability'].get_property('CurrentOptions') for r in self.owners.values()) or not all(self.token(p+'-empty-ready.json') for p in ('A','B0')):return
            self.write_token('empty-go.json');self.enter('empty-input')
        elif self.stage=='empty-input':
            if not all(self.token(p+'-empty-observed.json') for p in ('A','B0')):return
            if not all(self.input_dispatches(r)>=2 for r in self.owners.values()):return
            for row in self.owners.values():row['empty_ignored']=int(row['target'].TriggerCount)==1;require(row['empty_ignored'],'empty authority native input triggered target');self.move(row['target'],row['x']+150.,row['y'])
            self.write_token('returning.json');self.enter('return-scan')
        elif self.stage=='return-scan':
            if not all(self.found(r['ability'],r['target']) for r in self.owners.values()) or not all(self.token(p+'-return-ready.json') for p in ('A','B0')):return
            self.write_token('return-go.json');self.enter('second')
        elif self.stage=='second':
            if not all(int(r['target'].TriggerCount)==2 for r in self.owners.values()) or not all(self.token(p+'-done.json') for p in ('A','B0')):return
            if not all(self.input_dispatches(r)==3 for r in self.owners.values()):return
            self.report['owners']={p:self.result(r) for p,r in self.owners.items()}
            for row in self.owners.values():
                row['ability'].call_function('K2_CancelAbility')
                handles=[s.Handle.clone() for s in row['asc'].get_property('ActivatableAbilities').Items if int(s.Handle.Handle) not in row['baseline']]
                for handle in handles:row['asc'].call_function('ClearAbility',handle)
            for actor in self.fixtures:actor.actor_destroy()
            self.write_token('cleanup-done.json');self.enter('cleanup')
        elif self.stage=='cleanup':
            if not all(self.token(p+'-cleanup-ready.json') for p in ('A','B0')):return
            self.report['fixture_cleanup_complete']=all(not valid(a) for a in self.fixtures) and all(not instances(r['asc'],self.cls) and {int(s.Handle.Handle) for s in r['asc'].get_property('ActivatableAbilities').Items}==r['baseline'] for r in self.owners.values())
            self.cleanup();self.report['status']='awaiting_release';self.write_token('ready-server.json');self.enter('release')
        elif self.stage=='release':
            token=self.token('server-release.json')
            if token:
                require(token['client_exit_codes']==dict(A=0,B0=0),'client process exits required');self.report['server_waited_for_client_process_exit']=True;self.finish()

    def press(self):
        for pressed in (True,False):self.fixture_cls.get_cdo().call_function('UEPRouteInteractionInput',self.asc,self.input_handle,pressed)
        self.report['native_local_input_events']=self.report.get('native_local_input_events',0)+1
    def client_tick(self):
        if self.stage=='roster':
            token=self.token('fixtures.json')
            if not token:return
            config=token['owners'][self.peer];actors={tuple(identity(a) or ()):a for a in ue.tobject_iterator(self.fixture_cls) if valid(a) and not a.get_name().startswith('Default__')}
            if tuple(config['target']) not in actors or tuple(config['retarget']) not in actors:return
            self.target=actors[tuple(config['target'])];self.retarget=actors[tuple(config['retarget'])];self.target.set_property('Retarget',self.retarget);self.target.set_property('bCustomizePayload',True)
            self.controller.call_function('SetControlRotation',ue.FRotator());self.pawn.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0)
            self.pawn.call_function('K2_SetActorLocation',NewLocation=ue.FVector(config['x'],config['y'],2000.),bSweep=False,bTeleport=True);self.enter('scan')
        elif self.stage=='scan':
            self.subject=self.ability(self.asc)
            if not self.found(self.subject,self.target):return
            spec,=[s for s in self.asc.get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.get_class()==self.cls];self.input_handle=spec.Handle.clone()
            self.write_token(self.peer+'-scan-ready.json');self.enter('press')
        elif self.stage=='press' and self.token('press-go.json'):self.press();self.enter('first')
        elif self.stage=='first':
            if int(self.target.TriggerCount)!=1:return
            require(self.payload(self.target,self.retarget,self.pawn),'local predicted customized payload differs');self.write_token(self.peer+'-first.json');self.enter('empty-scan')
        elif self.stage=='empty-scan':
            if not self.token('moving-out.json') or self.subject.get_property('CurrentOptions'):return
            self.write_token(self.peer+'-empty-ready.json');self.enter('empty-press')
        elif self.stage=='empty-press' and self.token('empty-go.json'):self.press();self.enter('empty-observe')
        elif self.stage=='empty-observe':
            if time.monotonic()-self.phase_started<.2:return
            self.empty_ignored=int(self.target.TriggerCount)==1;require(self.empty_ignored,'empty local native input triggered target');self.write_token(self.peer+'-empty-observed.json');self.enter('return-scan')
        elif self.stage=='return-scan':
            if not self.token('returning.json') or not self.found(self.subject,self.target):return
            self.write_token(self.peer+'-return-ready.json');self.enter('return-press')
        elif self.stage=='return-press' and self.token('return-go.json'):self.press();self.enter('second')
        elif self.stage=='second':
            if int(self.target.TriggerCount)!=2:return
            self.report['owner_result']=self.result(dict(target=self.target,retarget=self.retarget,pawn=self.pawn,ability=self.subject,empty_ignored=self.empty_ignored));self.write_token(self.peer+'-done.json');self.enter('cleanup')
        elif self.stage=='cleanup':
            if not self.token('cleanup-done.json') or valid(self.target) or valid(self.retarget) or instances(self.asc,self.cls):return
            self.report['fixture_cleanup_complete']=True;self.report['inventory_and_health_unchanged']=capture(self.controller)==self.before_inventory and self.health()==self.before_health
            self.cleanup();self.write_token(self.peer+'-cleanup-ready.json');self.report['status']='awaiting_release';self.write_token('ready-'+self.peer+'.json');self.enter('release')
        elif self.stage=='release' and self.token('release.json'):self.finish()

    def cleanup(self):
        if self.cleaned:return
        self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        if not self.was_rooted:self.cls.remove_from_root()
        self.report['selector_and_root_restored']=self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector and self.cls.is_rooted()==self.was_rooted;self.cleaned=True

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<420.,'native interaction network timed out')
            if not self.ready:
                if self.world_ready():self.setup()
            elif self.peer=='server':self.server_tick()
            else:self.client_tick()
            self.report['stage']=self.stage;atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report);(ue.log_error if error else ue.log)('UEP_NATIVE_INTERACTION_NETWORK_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_INTERACTION_SHUTDOWN_'+self.report['status'].upper())


network=Network();ticker=ue.add_ticker(network.tick)
