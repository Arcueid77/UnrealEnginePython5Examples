"""Actual Interact/nearby grant/GAS payload -> native pickup and montage paths."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_characters.explorer_helpers_validation import Validation as Helpers
from .auto_respawn_helpers_validation import instances
from . import explorer_actions_mixin as policy,explorer_interact_mixin as interact
from uep_lyra_weapons import collect_cue_lifecycle_mixin as cue
from .explorer_actions_contract import FALSE_FIELDS,MODES,require,validate

def path(obj):return obj.get_path_name() if valid(obj) else None
def calls(a,key):return sum(policy.evidence(a)[p+'_'+key] for p in ('python','fallback'))
class Validation(Ready):
    silence_owned_ui=Helpers.silence_owned_ui
    cancel_owned_abilities=Helpers.cancel_owned_abilities
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[],cue_pool_profiles=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.owner=None;self.subject=None;self.state=None;self.target=None;self.action=None;self.interaction=None;self.roots=[];self.selectors={};self.scopes=[];self.profile_index=0;self.case_index=0;self.duration_events=[];self.cues=[]
    def inventory_rows(self):return [(path(e.Instance),int(e.StackCount)) for e in self.inventory.get_property('InventoryList').Entries]
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.interact_cls=ue.load_class(interact.CLASS);self.target_cls=ue.load_class('/Game/UEPValidation/BP_ExplorerInteractTarget.BP_ExplorerInteractTarget_C');self.reader=ue.load_class('/Game/UEPValidation/BP_ExplorerActionDurationProbe.BP_ExplorerActionDurationProbe_C').get_cdo();self.definition=ue.load_class('/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C')
        self.cue_cls=ue.load_class(cue.CLASS)
        self.report['native_cue_recycling_enabled']=lib('KismetSystemLibrary').call_function('GetConsoleVariableIntValue','AbilitySystem.GameplayCueActorRecycle')>0
        self.report['native_cue_timer_cleanup_enabled']=lib('KismetSystemLibrary').call_function('GetConsoleVariableIntValue','AbilitySystem.ClearCueNotifyTimers')>0
        for cls in list(self.classes.values())+[self.interact_cls,self.cue_cls]:self.selectors[cls]=cls.get_cdo().get_property('PythonMixinProfile');ue.register_declared_mixin(cls)
        for obj in list(self.classes.values())+[self.interact_cls,self.target_cls,self.reader,self.cue_cls]:
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        scope=SubscriptionScope()
        def read(proxy):
            payload,success=self.reader.call_function('ReadDuration',proxy);require(success,'native duration payload extraction failed');return payload
        scope.listen_gameplay_message(self.world,'Ability.Interaction.Duration.Message',ue.find_struct('LyraInteractionDurationMessage'),read,lambda channel,payload:self.duration_events.append(dict(instigator=path(payload.Instigator),duration=float(payload.Duration))));self.scopes.append(scope);self.start_profile()
    def start_profile(self):
        self.profile=('BlueprintFallback','Python')[self.profile_index]
        for cls in self.classes.values():cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.cue_cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.profile_cues=[];self.cue_before={}
        self.owner=self.statics.call_function('CreatePlayer',self.world,-1,True);self.silence_owned_ui();self.subject=self.owner.get_controlled_pawn();self.state=self.owner.get_property('PlayerState');require(valid(self.subject),'owned native local player missing');self.subject.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);self.subject.call_function('K2_SetActorLocation',NewLocation=ue.FVector(200000.,200000.,2000.),bSweep=False,bTeleport=True);self.owner.call_function('SetControlRotation',ue.FRotator());self.owner.call_function('SetViewTargetWithBlend',self.subject,0.,0,0.,False);self.case_index=0;self.enter('owned-ready')
    def next_action(self):
        if valid(self.target):self.target.actor_destroy()
        self.kind=('collect','sit')[self.case_index//len(MODES)];self.mode=MODES[self.case_index%len(MODES)];self.target=self.world.actor_spawn(self.target_cls);box=self.target.add_actor_root_component(ue.find_class('BoxComponent'),'UEPActionCollision');box.call_function('SetBoxExtent',ue.FVector(45.,65.,80.),True);box.call_function('SetCollisionProfileName','Interactable_BlockDynamic',True);box.call_function('SetCollisionEnabled',1);self.target.set_property('Option',ue.find_struct('InteractionOption')(InteractionAbilityToGrant=self.classes[self.kind]));self.target.set_property('StaticInventory',ue.find_struct('InventoryPickup')(Templates=[ue.find_struct('PickupTemplate')(StackCount=2,ItemDef=self.definition)]));self.target.call_function('K2_SetActorLocation',NewLocation=ue.FVector(200150.,200000.,2025.),bSweep=False,bTeleport=True);self.row=dict(profile=self.profile,kind=self.kind,mode=self.mode);self.report['cases'].append(self.row);self.enter('options')
    def observe(self):
        self.silence_owned_ui();require(time.monotonic()-self.phase_started<25.,'Explorer actions phase timeout: '+self.phase)
        if self.phase=='owned-ready':
            asc=ability_system(self.subject)
            if not valid(asc) or asc.get_property('AvatarActor')!=self.subject:return
            if any(spec.ActiveCount and valid(spec.Ability) and spec.Ability.get_class().get_name()=='GA_SpawnEffect_C' for spec in asc.get_property('ActivatableAbilities').Items):self.cancel_owned_abilities(asc,True);return
            self.asc=asc;self.inventory=self.owner.get_component_by_type(ue.find_class('LyraInventoryManagerComponent'));self.handle=self.asc.call_function('K2_GiveAbility',self.interact_cls,1,-1);self.next_action()
        elif self.phase=='options':
            if time.monotonic()-self.phase_started<.25:return
            found=instances(self.asc,self.interact_cls)
            if len(found)!=1 or not found[0].get_property('bIsActive'):return
            self.interaction=found[0];options=self.interaction.get_property('CurrentOptions');actions=instances(self.asc,self.classes[self.kind])
            if len(options)!=1 or len(actions)!=1:return
            # Wait for the new target after replacing the previous native actor.
            if options[0].InteractionAbilityToGrant!=self.classes[self.kind]:return
            self.action=actions[0]
            if self.action.get_property('bIsActive'):return
            ue.set_mixin_profile(self.action,self.profile);self.before=copy.deepcopy(policy.evidence(self.action));self.before_items=self.inventory_rows();self.messages_before=len(self.duration_events);self.press_time=self.game_time();self.target_path=path(self.target);self.asc.call_function('ServerSetInputPressed',self.handle);self.anim=self.subject.get_property('Mesh').call_function('GetAnimInstance');self.montage=self.action.get_property('Montage to Play');self.row['native_interact_trace_and_nearby_grant']=True;self.enter('montage')
        elif self.phase=='montage':
            values=policy.evidence(self.action);activated=calls(self.action,'activate')-sum(self.before[p+'_activate'] for p in ('python','fallback'))
            if activated!=1:return
            event=self.action.get_property('CurrentEventData');self.row['native_gas_event_activation']=True;self.row['original_event_target_and_instigator_received']=event.Instigator==self.subject and event.Target==self.target;self.row['native_montage_playing_observed']=bool(self.anim.call_function('Montage_IsPlaying',self.montage));require(self.row['native_montage_playing_observed'],'original native montage did not start')
            after=self.inventory_rows();new=[(name,count) for name,count in after if name not in {v[0] for v in self.before_items}];self.row.update(new_item_count=len(new),new_stack_counts=[v[1] for v in new],inventory_effect_matches_source=(len(new)==1 and new[0][1]==2) if self.kind=='collect' else after==self.before_items,collect_collision_lifespan_or_sit_target_preserved=(not self.target.call_function('GetActorEnableCollision') and 0.<float(self.target.call_function('GetLifeSpan'))<=3.) if self.kind=='collect' else self.target.call_function('GetActorEnableCollision') and float(self.target.call_function('GetLifeSpan'))==0.,no_authority_duration_message=len(self.duration_events)==self.messages_before)
            self.completion_profile=self.profile
            if self.kind=='collect':
                found=[a for a in ue.tobject_iterator(self.cue_cls) if valid(a) and a.call_function('GetOwner')==self.subject];require(found,'real native collect Cue missing')
                for a in found:
                    ue.set_mixin_profile(a,self.profile)
                    if a not in self.profile_cues:self.profile_cues.append(a);self.cue_before[path(a)]=sum(cue.evidence(a)[p+'_release'] for p in ('python','fallback'))
                    if a not in self.cues:self.cues.append(a)
            if self.mode=='switch':self.completion_profile='Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback';ue.set_mixin_profile(self.action,self.completion_profile)
            elif self.mode=='interrupt':self.anim.call_function('Montage_Stop',0.,self.montage)
            elif self.mode=='cancel':self.action.call_function('K2_CancelAbility')
            self.enter('ended')
        elif self.phase=='ended':
            if self.action.get_property('bIsActive') or self.anim.call_function('Montage_IsPlaying',self.montage):return
            delta={key:policy.evidence(self.action)[key]-self.before[key] for key in ('python_end','fallback_end')};self.row['native_montage_end_callbacks']=sum(delta.values());self.row['current_completion_profile_matches']=delta['python_end' if self.completion_profile=='Python' else 'fallback_end']==sum(delta.values());self.row['native_tasks_and_montage_closed']=not self.action.get_property('ActiveTasks');before=len(self.duration_events);self.action.call_function(policy.DURATION,self.subject);self.row['native_duration_transport_half_second_verified']=len(self.duration_events)==before+1 and self.duration_events[-1]==dict(instigator=path(self.subject),duration=.5)
            if self.kind=='collect' and self.mode=='normal':self.enter('lifespan')
            else:self.advance()
        elif self.phase=='lifespan':
            if valid(self.target):return
            self.row['native_target_expired_after_three_seconds']=self.game_time()-self.press_time>=2.9;self.advance()
        elif self.phase=='cue-retire':
            if any(not valid(a) for a in self.profile_cues):raise RuntimeError('managed collect Cue was destroyed instead of recycled')
            if any(a.call_function('GetOwner') is not None or not a.get_property('bHidden') for a in self.profile_cues):return
            rows=[]
            for a in self.profile_cues:
                splines=lib('LyraSystemStatics').call_function('FindComponentsByClass',a,ue.find_class('SplineComponent'),False);values=cue.evidence(a);delta=values['python_release']+values['fallback_release']-self.cue_before[path(a)];require(not splines and delta>=1 and float(a.call_function('GetLifeSpan'))==0.,'native collect Cue recycle did not clear owned spline/lifespan resources');rows.append(dict(actor=path(a),alive=True,hidden=True,owner_cleared=True,splines=0,lifespan=0.,release_delta=delta,lifecycle=copy.deepcopy(values)))
            self.report['cue_pool_profiles'].append(dict(profile=self.profile,cues=rows));self.close_context();self.profile_index+=1
            if self.profile_index<2:self.start_profile()
            else:self.finish()
    def advance(self):
        self.case_index+=1
        if self.case_index<len(self.classes)*len(MODES):self.next_action()
        else:self.enter('cue-retire')
    def close_context(self):
        for ability in (self.action,self.interaction):
            if valid(ability):
                if ability.get_property('bIsActive'):ability.call_function('K2_CancelAbility')
                ue.clear_mixin_profile(ability)
        if valid(self.target):self.target.actor_destroy()
        if valid(self.owner):self.statics.call_function('RemovePlayer',self.owner,True)
        for actor in (self.subject,self.state):
            if valid(actor):actor.actor_destroy()
    def cleanup(self):
        self.close_context()
        for a in self.cues:
            if valid(a):ue.clear_mixin_profile(a)
        for scope in self.scopes:scope.close()
        for cls,profile in self.selectors.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        for obj in self.roots:obj.remove_from_root()
        self.report['owned_contexts_tasks_roots_and_selectors_restored']=all(not valid(v) for v in (self.owner,self.subject,self.state,self.target)) and all(not obj.is_rooted() for obj in self.roots) and all(cls.get_cdo().get_property('PythonMixinProfile')==p for cls,p in self.selectors.items());self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<360.,'Explorer actions readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_ACTIONS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_ACTIONS_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerActionsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
