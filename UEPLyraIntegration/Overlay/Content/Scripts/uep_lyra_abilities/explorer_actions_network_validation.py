"""Two real clients: original native input, local prediction, pickup and UI."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_hud import ability_progress_mixin as progress
from . import explorer_actions_mixin as actions,explorer_interact_mixin as interact
from .explorer_actions_network_contract import PEERS,CASES,TARGETS,FALSE_FIELDS,PROFILES,require,expected_inventory

def path(obj):return obj.get_path_name() if valid(obj) else None
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def instances(asc,cls):
    return [a for s in asc.get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.get_class()==cls for a in list(s.NonReplicatedInstances)+list(s.ReplicatedInstances) if valid(a)]
def counts(obj,policy):return {k:v for k,v in policy.evidence(obj).items() if isinstance(v,(int,float))}
def delta(obj,policy,before):return {k:v-before.get(k,0) for k,v in counts(obj,policy).items()}
def model(widget):
    return dict(duration=float(widget.Duration),start=float(widget.StartTime),visibility=int(widget.call_function('GetVisibility')),
        text=str(widget.ProgressText.call_function('GetText')),percent=float(widget.ProgressBorder.call_function('GetDynamicMaterial').call_function('K2_GetScalarParameterValue','Percent')))

class Validation:
    def __init__(self,result):
        self.path=Path(result);self.root=self.path.parent;self.started=time.monotonic();self.phase_started=self.started;self.ready=False;self.finished=False;self.index=-1
        self.peer=next(a.split('=',1)[1] for a in sys.argv if a.startswith('-UEPExplorerActionsPeer='))
        self.profile=next(a.split('=',1)[1] for a in sys.argv if a.startswith('-UEPExplorerActionsProfile='));require(self.profile in PROFILES,'supported profile required')
        self.report=dict(status='running',error=None,peer=self.peer,profile=self.profile,cases=[],test_owned_ui_pair=True,selectors_restored=False,observers_restored=False,duration_scope_closed=False,actual_exit_finalizer=False,poses_restored=False)
        self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.saved_profiles={};self.bindings=[];self.events=[];self.durations=[];self.widgets=[];self.saved={};self.scope=None
        self.action_classes={k:ue.load_class(v) for k,v in actions.CLASSES.items()};self.interact_class=ue.load_class(interact.CLASS)
        for kind,cls in self.action_classes.items():
            ue.register_declared_mixin(cls);binding,=[r for r in ue.get_registered_mixins() if r['target_class']==cls]
            base=binding['profiles'][self.profile]['python_class'];values={k:v for k,v in vars(base).items() if not k.startswith('__') and callable(v)}
            original=values['K2_ActivateAbilityFromEvent']
            values['K2_ActivateAbilityFromEvent']=self.observe_entry(kind,original)
            ue.register_mixin_profile(cls,self.profile,type('ObservedNetworkExplorer'+kind.title()+self.profile,(),values));self.bindings.append((cls,base))
        atexit.register(self.finalize)
    def observe_entry(self,kind,original):
        def observed(actor,EventData):
            self.events.append(dict(kind=kind,instance=path(actor),authority=bool(actor.call_function('K2_HasAuthority')),instigator=path(EventData.Instigator),target=path(EventData.Target),native_start=self.native_action_state(actor)))
            return original(actor,EventData)
        return observed
    def native_action_state(self,actor):
        specs=[int(s.ActiveCount) for s in self.asc.get_property('ActivatableAbilities').Items
            if path(actor) in {path(a) for a in list(s.NonReplicatedInstances)+list(s.ReplicatedInstances)}]
        return dict(instance=path(actor),active=bool(actor.get_property('bIsActive')),
            active_tasks=len(actor.get_property('ActiveTasks')),spec_active_counts=specs)
    def write(self):atomic_write(self.path,self.report)
    def select(self,obj):
        if obj not in self.saved_profiles:self.saved_profiles[obj]=ue.get_mixin_profile(obj);ue.set_mixin_profile(obj,self.profile)
    def inventory(self,controller):
        component=controller.get_component_by_type(ue.find_class('LyraInventoryManagerComponent'));result={}
        require(valid(component),'native player inventory component missing')
        for entry in component.get_property('InventoryList').Entries:
            name=path(entry.Instance.get_property('ItemDef'));result[name]=result.get(name,0)+int(entry.StackCount)
        return result
    def setup(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or world.get_name()!='L_InteractionTestMap':continue
            self.world=world
            if self.scope is None:
                self.reader=ue.load_class('/Game/UEPValidation/BP_ExplorerActionDurationProbe.BP_ExplorerActionDurationProbe_C').get_cdo();self.scope=SubscriptionScope()
                def read(proxy):
                    payload,success=self.reader.call_function('ReadDuration',proxy);require(success,'native typed duration extraction failed');return payload
                self.scope.listen_gameplay_message(world,progress.CHANNEL,ue.find_struct('LyraInteractionDurationMessage'),read,lambda ch,p:self.durations.append(dict(instigator=path(p.Instigator),duration=float(p.Duration))))
            if self.peer=='server':
                identities={p:read_json(self.root/(p+'-ready.json')) for p in PEERS}
                if not all(isinstance(r,dict) and 'player_id' in r for r in identities.values()):return
                controllers,=lib('GameplayStatics').call_function('GetAllActorsOfClass',world,ue.find_class('LyraPlayerController'));self.owners={}
                for pc in controllers:
                    if not valid(pc.PlayerState):continue
                    for peer in PEERS:
                        if int(pc.PlayerState.PlayerId)==identities[peer]['player_id']:self.owners[peer]=pc
                if set(self.owners)!=set(PEERS) or not all(self.player_ready(pc) for pc in self.owners.values()):return
                self.targets={}
                for kind,target in TARGETS.items():
                    actors,=lib('GameplayStatics').call_function('GetAllActorsOfClass',world,ue.load_class(target));self.targets[kind]=sorted((a for a in actors if valid(a)),key=path)
                require(len(self.targets['collect'])>=2 and self.targets['sit'],'two original placed Rocks and a Chair required')
                for peer,pc in self.owners.items():
                    pawn=pc.get_controlled_pawn();movement=pawn.CharacterMovement
                    self.saved[peer]=dict(pawn=pawn,location=pawn.get_actor_location(),movement=movement,mode=int(movement.MovementMode),custom=int(movement.CustomMovementMode))
                self.ready=True;self.prepare(0);return
            pc=lib('GameplayStatics').call_function('GetPlayerController',world,0)
            if not valid(pc) or not self.player_ready(pc):return
            self.pc=pc;self.pawn=pc.get_controlled_pawn();self.asc=ability_system(self.pawn);self.interactors=instances(self.asc,self.interact_class)
            if not self.interactors:return
            self.aim_before=pc.call_function('GetControlRotation')
            for a in self.interactors:self.select(a)
            cls=ue.load_class(progress.CLASS);self.candidate=pc.create_widget(cls);self.baseline=pc.create_widget(cls);ue.set_mixin_profile(self.baseline,'BlueprintFallback')
            self.widgets=[self.candidate,self.baseline]
            for i,w in enumerate(self.widgets):w.add_to_root();w.AddToViewport(500+i)
            self.baseline.call_function('SetRenderOpacity',0.)
            self.report.update(player_id=int(pc.PlayerState.PlayerId),pawn=path(self.pawn),role=int(self.pawn.call_function('GetLocalRole')),natural_interactors=len(self.interactors))
            atomic_write(self.root/(self.peer+'-ready.json'),dict(player_id=self.report['player_id']));self.ready=True;return
    def player_ready(self,pc):
        pawn=pc.get_controlled_pawn();asc=ability_system(pawn) if valid(pawn) else None
        if not valid(asc) or asc.get_property('AvatarActor')!=pawn or pawn.get_property('bHidden'):return False
        return not any(s.ActiveCount and valid(s.Ability) and s.Ability.get_class().get_name()=='GA_SpawnEffect_C' for s in asc.get_property('ActivatableAbilities').Items)
    def prepare(self,index):
        self.index=index;owner,kind=CASES[index];self.owner=owner;self.kind=kind;self.target=self.targets[kind][PEERS.index(owner) if kind=='collect' else 0]
        origin=self.target.get_actor_location();self.current=self.owners[owner];self.pawn=self.current.get_controlled_pawn();self.asc=ability_system(self.pawn)
        self.before={p:self.inventory(pc) for p,pc in self.owners.items()};self.events_before=len(self.events);self.messages_before=len(self.durations);self.server_selected=False
        for peer,s in self.saved.items():
            s['movement'].call_function('SetMovementMode',0,0);s['pawn'].set_actor_location(ue.FVector(origin.x-150.,origin.y+(-90. if peer==owner else 500.),origin.z+95.))
        templates=[]
        if kind=='collect':templates=[dict(definition=path(t.ItemDef),count=int(t.StackCount)) for t in self.target.get_property('StaticInventory').Templates]
        self.packet=dict(index=index,owner=owner,kind=kind,target=path(self.target),target_class=TARGETS[kind],pickup_templates=templates)
        atomic_write(self.root/'phase.json',self.packet);self.phase_started=time.monotonic()
    def server(self):
        if self.index==len(CASES):
            if all((self.root/(p+'-exited.json')).is_file() for p in PEERS):self.finish()
            return
        if not self.server_selected:
            self.action_instances=instances(self.asc,self.action_classes[self.kind])
            if not self.action_instances:return
            for a in instances(self.asc,self.interact_class)+self.action_instances:self.select(a)
            self.before_actions={path(a):counts(a,actions) for a in self.action_instances};self.server_selected=True
            atomic_write(self.root/('server-ready-'+str(self.index)+'.json'),dict(ready=True))
        acks={p:read_json(self.root/(p+'-case-'+str(self.index)+'.json')) for p in PEERS}
        if not all(isinstance(r,dict) for r in acks.values()):return
        require(all(r['passed'] for r in acks.values()),'native client case failed')
        active=[a for a in self.action_instances if sum(delta(a,actions,self.before_actions[path(a)])[p+'_activate'] for p in ('python','fallback'))]
        if not active or any(a.get_property('bIsActive') or a.get_property('ActiveTasks') for a in active):return
        completion=[self.native_action_state(a) for a in active]
        if any(row['spec_active_counts']!=[0] for row in completion):return
        if self.kind=='collect' and valid(self.target):return
        foreign=PEERS[1-PEERS.index(self.owner)]
        row=dict(self.packet,role=int(self.pawn.call_function('GetLocalRole')),pawn=path(self.pawn),events=copy.deepcopy(self.events[self.events_before:]),native_completion=completion,action_deltas=[delta(a,actions,self.before_actions[path(a)]) for a in active],
            native_tasks_closed=True,inventory_before=self.before[self.owner],inventory_after=self.inventory(self.current),other_inventory_before=self.before[foreign],other_inventory_after=self.inventory(self.owners[foreign]),duration_delta=len(self.durations)-self.messages_before,
            target_expired=not valid(self.target),target_preserved=valid(self.target) and self.target.call_function('GetActorEnableCollision') and self.target.call_function('GetLifeSpan')==0.)
        self.report['cases'].append(row)
        if self.index+1<len(CASES):self.prepare(self.index+1)
        else:
            for s in self.saved.values():s['pawn'].set_actor_location(s['location']);s['movement'].call_function('SetMovementMode',s['mode'],s['custom'])
            self.report['poses_restored']=all(vec(s['pawn'].get_actor_location())==vec(s['location']) for s in self.saved.values())
            atomic_write(self.root/'release.json',dict(ready=True));self.index=len(CASES);self.phase_started=time.monotonic()
        self.write()
    def client(self):
        if (self.root/'release.json').is_file():self.finish();return
        packet=read_json(self.root/'phase.json')
        if not isinstance(packet,dict):return
        if packet['index']!=self.index:
            self.index=packet['index'];self.packet=packet;self.phase_started=time.monotonic();self.requested=False;self.released=False;self.completed=False;self.matched=False;self.progress_completed=False
            self.before_inventory=self.inventory(self.pc);self.messages_before=len(self.durations);self.events_before=len(self.events)
            self.before_progress=self.candidate._uep_progress_messages
            atomic_write(self.root/(self.peer+'-phase-'+str(self.index)+'.json'),dict(ready=True))
        if self.completed:return
        owner=packet['owner']==self.peer;kind=packet['kind'];elapsed=time.monotonic()-self.phase_started
        if not owner:
            require(len(self.durations)==self.messages_before,'foreign interaction duration delivered in this client process')
            if elapsed<4.:return
            row=dict(packet,passed=True,inventory_before=self.before_inventory,inventory_after=self.inventory(self.pc),duration_delta=0,own_activation_delta=len(self.events)-self.events_before)
        else:
            target=ue.find_object(packet['target'])
            if not self.requested:
                if not valid(target):return
                origin,_=target.call_function('GetActorBounds',True);camera=self.pc.PlayerCameraManager.call_function('GetCameraLocation')
                self.pc.call_function('SetControlRotation',lib('KismetMathLibrary').call_function('FindLookAtRotation',camera,origin))
                if elapsed<1. or not all((self.root/(p+'-phase-'+str(self.index)+'.json')).is_file() for p in PEERS) or not (self.root/('server-ready-'+str(self.index)+'.json')).is_file():return
                selected=[a for a in self.interactors if any(valid(o.InteractionAbilityToGrant) and path(o.InteractionAbilityToGrant)==actions.CLASSES[kind] for o in a.get_property('CurrentOptions'))]
                self.action_instances=instances(self.asc,self.action_classes[kind])
                self.report['scan_diagnostics']=dict(index=self.index,selected=len(selected),actions=len(self.action_instances),options=[[path(o.InteractionAbilityToGrant) for o in a.get_property('CurrentOptions')] for a in self.interactors],location=vec(self.pawn.get_actor_location()))
                if len(selected)!=len(self.interactors) or not self.action_instances:return
                for a in self.action_instances:self.select(a)
                self.before_actions={path(a):counts(a,actions) for a in self.action_instances};self.before_interact={path(a):counts(a,interact) for a in self.interactors}
                self.input=lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubsystem',self.pc,ue.find_class('EnhancedInputLocalPlayerSubsystem'))
                self.input_asset=ue.load_object(ue.find_class('InputAction'),'/ShooterExplorer/Input/Actions/IA_Interact.IA_Interact');self.input.call_function('InjectInputVectorForAction',self.input_asset,ue.FVector(1.,0.,0.));self.requested=True;self.press_time=time.monotonic();return
            if not self.released:self.input.call_function('InjectInputVectorForAction',self.input_asset,ue.FVector());self.released=True
            if self.candidate._uep_progress_messages>self.before_progress:
                left,right=model(self.candidate),model(self.baseline)
                require(all(abs(left[k]-right[k])<.00001 if k in ('start','duration','percent') else left[k]==right[k] for k in left),'native duration UI original/Python presentation differs')
                self.matched=True
                if left['visibility']==1 and time.monotonic()-self.press_time>.8:self.progress_completed=True
            if time.monotonic()-self.press_time<3.5 or not self.progress_completed:return
            active=[a for a in self.action_instances if sum(delta(a,actions,self.before_actions[path(a)])[p+'_activate'] for p in ('python','fallback'))]
            if not active or any(a.get_property('bIsActive') or a.get_property('ActiveTasks') for a in active):return
            completion=[self.native_action_state(a) for a in active]
            if any(row['spec_active_counts']!=[0] for row in completion):return
            expected=expected_inventory(self.before_inventory,packet['pickup_templates']) if kind=='collect' else self.before_inventory
            if self.inventory(self.pc)!=expected:return
            row=dict(packet,passed=True,pawn=path(self.pawn),role=int(self.pawn.call_function('GetLocalRole')),events=copy.deepcopy(self.events[self.events_before:]),native_completion=completion,
                action_deltas=[delta(a,actions,self.before_actions[path(a)]) for a in active],native_tasks_closed=True,input_asset=path(self.input_asset),
                interactor_press_deltas=[delta(a,interact,self.before_interact[path(a)]) for a in self.interactors],duration_delta=len(self.durations)-self.messages_before,durations=copy.deepcopy(self.durations[self.messages_before:]),
                inventory_before=self.before_inventory,inventory_after=self.inventory(self.pc),progress_matched_original=self.matched,progress_completed=self.progress_completed)
        self.report['cases'].append(row);self.completed=True;atomic_write(self.root/(self.peer+'-case-'+str(self.index)+'.json'),row);self.write()
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:
            if self.peer!='server' and hasattr(self,'pc'):
                if getattr(self,'requested',False) and not getattr(self,'released',False):self.input.call_function('InjectInputVectorForAction',self.input_asset,ue.FVector())
                self.pc.call_function('SetControlRotation',self.aim_before);self.report['poses_restored']=True
            if self.peer=='server' and error:
                for s in self.saved.values():
                    if valid(s['pawn']):s['pawn'].set_actor_location(s['location']);s['movement'].call_function('SetMovementMode',s['mode'],s['custom'])
            for obj,profile in self.saved_profiles.items():
                if valid(obj):ue.set_mixin_profile(obj,profile)
            self.report['selectors_restored']=True
            for cls,base in self.bindings:ue.register_mixin_profile(cls,self.profile,base)
            self.report['observers_restored']=True
            if self.scope is not None:self.scope.close()
            self.report['duration_scope_closed']=True
            for w in self.widgets:w.RemoveFromParent();w.remove_from_root()
            self.widgets=[]
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)(error or 'UEP_EXPLORER_ACTIONS_NETWORK_READY');ue.request_exit()
    def tick(self,dt):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<250.,'Explorer network total timeout');require(time.monotonic()-self.phase_started<70.,'Explorer network phase timeout: '+str(self.index))
            if not self.ready:self.setup()
            elif self.peer=='server':self.server()
            else:self.client()
            self.report['diagnostics']=dict(ready=self.ready,index=self.index,elapsed=round(time.monotonic()-self.phase_started,3),requested=getattr(self,'requested',False),events=len(self.events),duration_messages=len(self.durations))
            if not self.finished:self.write()
            return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finalize(self):
        self.report['actual_exit_finalizer']=True;self.report['shutdown_active_progress']=progress.snapshot()['active_count']
        if self.report['status']=='awaiting_shutdown':self.report['status']='passed'
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_ACTIONS_NETWORK_'+self.report['status'].upper())

prefix='-UEPExplorerActionsNetworkResult='
validation=Validation(next(a[len(prefix):] for a in sys.argv if a.startswith(prefix)))
ticker=ue.add_ticker(validation.tick)
