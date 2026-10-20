"""Original Explorer delegates, native GAS/AI sense and native lifecycle producers."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import LyraCharacterPart,GameplayTag,GameplayEventData
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .explorer_helpers_validation import Validation as Helpers
from .parts_changed_observation import DelegateObserver,component,parts,part_actors,query
from .team_cosmetics_validation import DeviceObserver
from .health_changed_observation import OwnedAI,Context,apply,health
from .health_changed_contract import NAMES
from . import parts_changed_mixin as part_policy,lifecycle_mixin as life_policy,inventory_clear_mixin as clear_policy
from .explorer_callbacks_contract import FALSE_FIELDS,require,validate

def path(obj):return obj.get_path_name() if valid(obj) else None
def part_count(actor):return sum(part_policy.evidence(actor)[n] for n in ('python_calls','fallback_calls'))

class Validation(Helpers):
    def __init__(self,result):
        super().__init__(result);self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerCallbacksProfile=')),'Python');self.report=dict(status='running',error=None,profile=self.profile,characters=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.bot=None;self.context=None;self.delegates=None;self.device_observer=None;self.owned_part=None;self.bot_cleanups=[];self.health_cleanups=[]
    def begin(self):
        phases=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraGamePhaseSubsystem'))
        if not valid(phases) or not phases.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.Playing')):return
        asc=ability_system(self.pawn)
        if not valid(asc) or asc.get_property('AvatarActor')!=self.pawn:return
        super().begin()
    def start_matrix(self):
        self.row.update(parts=[],health=[]);self.parts_before=parts(self.subject);self.part_actors_before=[path(a) for a in part_actors(self.subject)];self.delegates=DelegateObserver((self.subject,));self.device_observer=DeviceObserver();self.part_operation=0;self.operate_part()
    def operate_part(self):
        operation=('add','remove','remove-again')[self.part_operation];before=self.delegates.count(self.subject);count_before=part_count(self.subject);marker=self.device_observer.marker();native_query=query(self.subject);user=self.subject.call_function('GetPlatformUserId');user_valid=bool(lib('InputDeviceLibrary').call_function('IsValidPlatformId',user))
        if operation=='add':self.owned_part=component(self.subject).call_function('AddCharacterPart',LyraCharacterPart(PartClass=ue.find_class('Actor'))).clone()
        else:component(self.subject).call_function('RemoveCharacterPart',self.owned_part)
        callbacks=self.delegates.count(self.subject)-before;props=self.device_observer.collect(marker);expected=int(operation!='remove-again');self.part_row=dict(operation=operation,native_callback_count=callbacks,selected_receiver_calls=part_count(self.subject)-count_before,native_delegate_payload_matches=all(v['component_matches'] and v['owner_matches'] for v in self.delegates.since(self.subject,before)),native_device_count_matches=len(props)==int(expected and native_query['part_of_team'] and user_valid),native_devices_retired=False);self.pending_device_props=props;self.row['parts'].append(self.part_row);require(callbacks==expected,'native Add/RemoveCharacterPart delivery count differs');self.enter('parts-device')
    def observe(self):
        if self.bot is not None:self.bot.ready()
        self.silence_owned_ui();require(time.monotonic()-self.phase_started<45.,'Explorer callback phase timeout: '+self.phase)
        if self.phase=='startup':
            asc=ability_system(self.subject)
            if not valid(asc) or asc.get_property('AvatarActor')!=self.subject:return
            super().observe()
        elif self.phase=='parts-device':
            if not self.device_observer.observed(self.pending_device_props):return
            self.part_row['native_devices_retired']=True;self.part_operation+=1
            if self.part_operation<3:self.operate_part();return
            self.row['parts_original_entries_and_actors_restored']=parts(self.subject)==self.parts_before and [path(a) for a in part_actors(self.subject)]==self.part_actors_before;self.owned_part=None;self.delegates.close();self.delegates=None;self.device_observer.close();self.device_observer=None
            try:self.pawndata.set_property('PawnClass',self.classes[self.kind]);self.bot=OwnedAI(self.world)
            finally:self.pawndata.set_property('PawnClass',self.pawnclass)
            require(self.bot.pawn.get_class()==self.classes[self.kind],'native bot did not use the exact Explorer class');self.enter('bot-ready')
        elif self.phase=='bot-ready':
            local_immune=ability_system(self.subject).call_function('HasMatchingGameplayTag',GameplayTag(TagName='Gameplay.DamageImmunity'));self.row['local_damage_immunity_before_health']=bool(local_immune)
            if not self.bot.ready() or local_immune:return
            self.context=Context(dict(A=self.subject,AI=self.bot.pawn),dict(A=self.owner),self.bot);self.health_index=0;self.produce_health()
        elif self.phase=='health':
            if not self.context.seen() or time.monotonic()-self.phase_started<.35:return
            self.row['health'].append(copy.deepcopy(self.context.row()));self.context.restore();require(self.context.restored(),'native GAS health restore failed');self.enter('health-settle')
        elif self.phase=='health-settle':
            if time.monotonic()-self.phase_started<.2:return
            self.health_index+=1
            if self.health_index<len(NAMES):self.produce_health();return
            cleanup=self.context.cleanup();self.health_cleanups.append(cleanup);self.context=None;self.row['health_cleanup_restored']=all(cleanup[n] for n in ('health_restored','original_profiles_restored','original_inventory_restored','cdo_profile_restored')) and cleanup['observer']['active']==0;self.bot_cleanups.append(self.bot.close());self.bot=None;self.begin_reset()
        elif self.phase=='reset':
            if not self.lifecycle_seen('reset'):return
            self.row['reset']=self.lifecycle_row('reset');self.remove_local_player();old=self.row;super().spawn_character();self.report['characters'].pop();self.row=old;self.enter('death-ready')
        elif self.phase=='death-ready':
            asc=ability_system(self.subject)
            if not valid(asc):return
            self.cancel_owned_abilities(asc,spawn_only=True)
            if asc.call_function('HasMatchingGameplayTag',GameplayTag(TagName='Gameplay.DamageImmunity')):return
            self.arm_lifecycle('death');apply(asc,self.subject,health(self.subject)+100.);self.subject=None;self.enter('death')
        elif self.phase=='death':
            if not self.lifecycle_seen('death'):return
            self.row['death']=self.lifecycle_row('death');self.enter('death-drain')
        elif self.phase=='death-drain':
            if any(valid(a) and a.get_path_name()==self.old_actor for a in self.world.all_actors()):return
            self.remove_local_player();self.index+=1
            if self.index<2:super().spawn_character()
            else:self.finish()
    def produce_health(self):
        name=NAMES[self.health_index];self.context.prepare(name);require(self.context.prepared(name),'native health prepare differs');self.context.arm(name,self.profile)
        target=self.context.actors[self.context.target_key];asc=ability_system(target);diagnostic=dict(name=name,before=health(target),immune=bool(asc.call_function('HasMatchingGameplayTag',GameplayTag(TagName='Gameplay.DamageImmunity'))),godmode=bool(asc.call_function('HasMatchingGameplayTag',GameplayTag(TagName='Cheat.GodMode'))),unlimited=bool(asc.call_function('HasMatchingGameplayTag',GameplayTag(TagName='Cheat.UnlimitedHealth'))))
        diagnostic.update(asc=path(asc),avatar=path(asc.get_property('AvatarActor')),owner=path(asc.get_property('OwnerActor')),target=path(target),health_asc=path(target.get_component_by_type(ue.find_class('LyraHealthComponent')).get_property('AbilitySystemComponent')))
        try:self.context.produce()
        finally:diagnostic['after']=health(target);diagnostic['raw_health_events']=copy.deepcopy(self.context.raw[self.context.target_key][-4:]);self.row['last_health_producer_diagnostic']=diagnostic
        self.enter('health')
    def arm_lifecycle(self,name):
        ue.set_mixin_profile(self.subject,self.profile);self.subject.set_property('InitialInventoryItems',[self.definition]);self.probe.call_function('Grant',self.subject);self.old_actor=self.subject.get_path_name();self.old_actor_exact=self.subject.get_class()==self.classes[self.kind];self.life=life_policy.evidence(self.subject);self.life_before=copy.deepcopy(self.life);self.clear=clear_policy.evidence(self.subject);self.clear_before=copy.deepcopy(self.clear)
    def begin_reset(self):
        self.arm_lifecycle('reset');asc=ability_system(self.subject);specs=[s for s in asc.get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.get_class().get_path_name()=='/Script/LyraGame.LyraGameplayAbility_Reset'];require(len(specs)==1,'one originally granted native Reset ability required');tag=GameplayTag(TagName='GameplayEvent.RequestReset');state=self.owner.get_property('PlayerState');lib('AbilitySystemBlueprintLibrary').call_function('SendGameplayEventToActor',state,tag,GameplayEventData(EventTag=tag,Instigator=state,Target=state));self.subject=None;self.enter('reset')
    def lifecycle_seen(self,name):return self.life[name+('_python' if self.profile=='Python' else '_fallback')]-self.life_before[name+('_python' if self.profile=='Python' else '_fallback')]==1
    def lifecycle_row(self,name):
        after=self.clear['last_call'];calls=sum(self.clear[n]-self.clear_before[n] for n in ('python_calls','fallback_calls'));matches=after is not None and (not after['authority'] or not after['after']['controller_valid'] or (not after['after']['items'] and all(v is None for v in after['after']['slots'])));return dict(native_producer_called=True,selected_event_calls=1,native_clear_calls=calls,clear_after_matches_original_guard=bool(matches),old_actor_was_original_explorer=self.old_actor_exact,old_actor=self.old_actor)
    def remove_local_player(self):
        if valid(self.owner):self.statics.call_function('RemovePlayer',self.owner,True);require(not valid(self.owner),'native extra player removal failed')
        self.owner=None;self.subject=None
    def cleanup(self):
        if self.context is not None:
            self.context.restore();self.health_cleanups.append(self.context.cleanup());self.context=None
        if self.bot is not None:self.bot_cleanups.append(self.bot.close());self.bot=None
        if self.owned_part is not None and valid(getattr(self,'subject',None)):component(self.subject).call_function('RemoveCharacterPart',self.owned_part);self.owned_part=None
        if self.delegates is not None:self.delegates.close();self.delegates=None
        if self.device_observer is not None:self.device_observer.close();self.device_observer=None
        self.report['owned_native_bot_producers_and_observers_closed']=len(self.bot_cleanups)==2 and all(c['owned_pawn_controller_playerstate_producer_destroyed'] and c['original_bot_producer_list_preserved'] for c in self.bot_cleanups) and all(c['observer']['active']==0 for c in self.health_cleanups)
        super().cleanup()
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<360.,'Explorer callback validation timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_CALLBACKS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_CALLBACKS_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerCallbacksResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
