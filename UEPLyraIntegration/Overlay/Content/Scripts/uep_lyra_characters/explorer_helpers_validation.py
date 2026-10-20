"""Real owned Lyra spawns, inventory/quickbar/GAS and native Blueprint callers."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.explorer_state_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from . import explorer_helpers_mixin as policy
from .inventory_clear_mixin import inventory_state,components
from .explorer_helpers_contract import FALSE_FIELDS,CASES,require,validate

UNARMED='/Game/Characters/Heroes/Mannequin/Animations/Locomotion/Unarmed/ABP_UnarmedAnimLayers.ABP_UnarmedAnimLayers_C'

def path(obj):return obj.get_path_name() if valid(obj) else None
def one(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value
def natural(actor):return sum(policy.evidence(actor)[name] for name in ('python_grants','fallback_grants'))

class Validation(Ready):
    def __init__(self,result):
        # Reuse world readiness only; StateTree installation never runs in this fixture.
        super().__init__(result);self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerHelpersProfile=')),'Python')
        self.report=dict(status='running',error=None,profile=self.profile,characters=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.roots=[];self.owned=[];self.actions=[];self.index=0;self.pawndata=None
    def begin(self):
        _,ready_inventory=components(self.controller)
        if not valid(ready_inventory) or not list(ready_inventory.call_function('GetAllItems')):return
        self.health_before=self.healths();self.player_inventory_before=inventory_state(self.controller)
        self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()}
        for cls in self.classes.values():
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
            self.cdos[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.profile);ue.register_declared_mixin(cls)
        self.pawndata=self.controller.PlayerState.get_property('PawnData');require(valid(self.pawndata),'original player PawnData missing');self.pawnclass=self.pawndata.get_property('PawnClass')
        self.mode=self.statics.call_function('GetGameMode',self.world);self.unarmed=ue.load_class(UNARMED)
        _,inventory=components(self.controller);items=list(inventory.call_function('GetAllItems'));require(items,'original real inventory definition required');self.definition=items[0].get_property('ItemDef');self.spawn_character()
    def spawn_character(self):
        self.kind=('hero','pawn')[self.index]
        try:
            self.pawndata.set_property('PawnClass',self.classes[self.kind]);self.owner=self.statics.call_function('CreatePlayer',self.world,-1,True)
        finally:self.pawndata.set_property('PawnClass',self.pawnclass)
        require(valid(self.owner) and self.owner!=self.controller,'native extra local player creation failed')
        self.silence_owned_ui()
        self.subject=self.owner.get_controlled_pawn()
        require(valid(self.subject) and self.subject.get_class()==self.classes[self.kind] and self.pawndata.get_property('PawnClass')==self.pawnclass,'native local-player Explorer spawn/class restoration failed')
        self.subject.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0)
        self.probe=self.world.actor_spawn(ue.load_class('/Game/UEPValidation/BP_Explorer'+self.kind.title()+'HelpersCallProbe.BP_Explorer'+self.kind.title()+'HelpersCallProbe_C'));self.owned.append(self.probe)
        self.row=dict(kind=self.kind,cases=[],native_class=self.subject.get_class().get_path_name());self.report['characters'].append(self.row);self.enter('startup')
    def silence_owned_ui(self):
        for widget in ue.tobject_iterator(ue.find_class('CommonActivatableWidget')):
            if valid(widget) and widget.call_function('GetOwningPlayer')==self.owner:widget.call_function('DeactivateWidget')
        self.report['secondary_owned_ui_deactivated_for_helper_fixture']=True
    def observe(self):
        self.silence_owned_ui()
        require(time.monotonic()-self.phase_started<40.,'Explorer helper phase timeout: '+self.phase)
        if self.phase=='startup':
            quick,inventory=components(self.owner);asc=ability_system(self.subject)
            self.report['startup_diagnostics']=dict(kind=self.kind,quickbar=path(quick),inventory=path(inventory),asc=path(asc),natural_grants=natural(self.subject),player_state=path(self.owner.get_property('PlayerState')))
            if not (valid(quick) and valid(inventory) and valid(asc) and natural(self.subject)>=1):return
            spawn_active=sum(int(spec.ActiveCount) for spec in asc.get_property('ActivatableAbilities').Items if valid(spec.Ability) and spec.Ability.get_class().get_name()=='GA_SpawnEffect_C')
            self.report['startup_diagnostics']['spawn_effect_active']=spawn_active
            if spawn_active:
                self.cancel_owned_abilities(asc,spawn_only=True);return
            self.quick,self.inventory,self.asc=quick,inventory,asc;self.row.update(natural_grant_calls=natural(self.subject),native_asc_ready=True);self.report.update(native_gamemode_spawned_exact_explorer_classes=True,scoped_pawnclass_override_restored=True,native_owned_controller_inventory_quickbar_and_asc_ready=True,native_blueprint_callers_used=True);self.start_matrix()
        elif self.phase=='layer':
            animation=self.subject.get_property('Mesh').call_function('GetAnimInstance')
            if not valid(animation):return
            linked=animation.call_function('GetLinkedAnimLayerInstanceByClass',self.unarmed)
            if not valid(linked):return
            self.row['unarmed_unlinked_before_and_relinked_after']=True;self.report['native_empty_loadout_links_actual_unarmed_layer']=True;self.finish_case();self.next_case()
        elif self.phase=='next_case':self.run_case()
    def clear(self):
        self.probe.call_function('Clear',self.subject);state=inventory_state(self.owner)
        require(not state['items'] and all(v is None for v in state['slots']),'native Explorer ClearInventory left items/slots')
        return True
    def start_matrix(self):
        self.events=[];self.tag=GameplayTag(TagName='UEP.Test.Explorer.Helpers.Slot')
        action=lib('AbilityAsync_WaitGameplayEvent').call_function('WaitGameplayEventToActor',self.subject,self.tag,False,True);require(valid(action),'owned native GAS event listener missing');action.add_to_root()
        def receive(payload):self.events.append(dict(tag=str(payload.EventTag.TagName),magnitude=float(payload.EventMagnitude),instigator_null=payload.Instigator is None,target_null=payload.Target is None))
        action.bind_event('EventReceived',receive);action.call_function('Activate');self.actions.append((action,receive));self.case_index=0;self.run_case()
    def run_case(self):
        self.clear();name=CASES[self.case_index];count={'empty':0,'one':1,'duplicates':2,'over-capacity':4,'occupied':2}[name];self.seed=None
        if name=='occupied':
            self.seed=self.inventory.call_function('AddItemDefinition',self.definition,1);self.quick.call_function('AddItemToSlot',0,self.seed)
        self.subject.set_property('InitialInventoryItems',[self.definition]*count)
        if name=='empty':
            self.subject.get_property('Mesh').call_function('UnlinkAnimClassLayers',self.unarmed);animation=self.subject.get_property('Mesh').call_function('GetAnimInstance');require(valid(animation) and not valid(animation.call_function('GetLinkedAnimLayerInstanceByClass',self.unarmed)),'native unarmed fixture failed to unlink initial layer')
        self.probe.call_function('Grant',self.subject);items=list(self.inventory.call_function('GetAllItems'));slots=list(self.quick.call_function('GetSlots'));active=int(self.quick.call_function('GetActiveSlotIndex'));expected=count+(1 if self.seed is not None else 0);occupied=sum(valid(v) for v in slots)
        self.case=dict(name=name,definition_count=count,item_count=len(items),occupied_slots=occupied,active_slot=active,expected_shape_matches=len(items)==expected and occupied==min(count,len(slots)) and (count==0 or active==0) and (self.seed is None or slots[0]==self.seed),clear_verified=False,slot_events_match=False)
        require(self.case['expected_shape_matches'],'native original helper grant/duplicate/capacity/occupied behavior differs');self.row['cases'].append(self.case)
        if name=='empty':self.enter('layer')
        else:self.finish_case();self.next_case()
    def finish_case(self):
        slots=list(self.quick.call_function('GetSlots'));before=len(self.events);indexes=[-1,0,1,len(slots)]
        for index in indexes:self.probe.call_function('Slot',self.subject,index,self.tag)
        events=self.events[before:];expected=[float(i) for i in indexes if 0<=i<len(slots) and valid(slots[i])]
        self.case['slot_events_match']=[e['magnitude'] for e in events]==expected and all(e['tag']==str(self.tag.TagName) and e['instigator_null'] and e['target_null'] for e in events);require(self.case['slot_events_match'],'native helper GAS slot payload/count differs');self.case['clear_verified']=self.clear()
    def next_case(self):
        self.case_index+=1
        if self.case_index<len(CASES):self.enter('next_case');return
        audio=self.subject.add_actor_component(ue.find_class('AudioComponent'),'UEPExplorerHelperAudio');self.probe.call_function('SetAudio',self.subject,audio);require(one(self.probe.call_function('GetAudio',self.subject))==audio,'native interface audio instance roundtrip differs');self.probe.call_function('SetAudio',self.subject,None);require(one(self.probe.call_function('GetAudio',self.subject)) is None,'native interface audio null roundtrip differs');self.row['audio_roundtrip']=True
        self.subject.set_property('InitialInventoryItems',[]);self.quick.call_function('K2_DestroyComponent',self.owner);self.probe.call_function('Grant',self.subject);self.probe.call_function('Slot',self.subject,0,self.tag);self.inventory.call_function('K2_DestroyComponent',self.owner);self.probe.call_function('Grant',self.subject);self.probe.call_function('Clear',self.subject);self.row['missing_component_cases']=True
        self.owner.call_function('UnPossess');self.probe.call_function('Grant',self.subject);self.probe.call_function('Clear',self.subject);self.probe.call_function('Slot',self.subject,0,self.tag);self.row['unpossessed_noops']=True
        self.end_actions();self.statics.call_function('RemovePlayer',self.owner,True);self.subject.actor_destroy();require(not valid(self.owner) and not valid(self.subject),'native extra local player removal incomplete');self.owner=None;self.subject=None;self.index+=1
        if self.index<2:self.spawn_character()
        else:
            self.report.update(native_audio_null_and_instance_roundtrip=True,native_slot_events_match_valid_occupied_indexes=True,native_clear_removes_owned_items_and_slots=True,native_missing_components_and_unpossessed_noops=True);self.finish()
    def cancel_owned_abilities(self,asc,spawn_only=False):
        for spec in list(asc.get_property('ActivatableAbilities').Items):
            if spawn_only and (not valid(spec.Ability) or spec.Ability.get_class().get_name()!='GA_SpawnEffect_C'):continue
            for ability in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances):
                if valid(ability) and ability!=spec.Ability and ability.get_property('bIsActive'):
                    ability.call_function('K2_CancelAbility');self.report['owned_native_ability_cancel_requests']=self.report.get('owned_native_ability_cancel_requests',0)+1
    def end_actions(self):
        for action,handler in self.actions:
            if valid(action):action.call_function('EndAction');action.unbind_event('EventReceived',handler);action.remove_from_root()
        self.actions=[]
    def cleanup(self):
        self.end_actions()
        if hasattr(self,'owner') and valid(self.owner):
            self.statics.call_function('RemovePlayer',self.owner,True);require(not valid(self.owner),'native local player cleanup failed')
        if hasattr(self,'subject') and valid(self.subject):self.subject.actor_destroy()
        for actor in reversed(self.owned):
            if valid(actor):actor.actor_destroy()
        if valid(self.pawndata):self.pawndata.set_property('PawnClass',self.pawnclass)
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        self.report['owned_objects_profiles_roots_and_tasks_restored']=all(not valid(a) for a in self.owned) and all(cls.get_cdo().get_property('PythonMixinProfile')==p for cls,p in self.cdos.items())
        for cls in self.roots:cls.remove_from_root()
        if hasattr(self,'health_before'):self.report['original_player_inventory_and_health_unchanged']=self.healths()==self.health_before and inventory_state(self.controller)==self.player_inventory_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<210.,'Explorer helpers validation timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_HELPERS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_HELPERS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerHelpersResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
