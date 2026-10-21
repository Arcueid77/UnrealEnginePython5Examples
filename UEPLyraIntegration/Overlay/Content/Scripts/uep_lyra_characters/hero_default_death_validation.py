"""Native GameMode-owned characters and lethal GAS; never replay Health events."""
import atexit,copy,hashlib,json,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_abilities import death_damage
from .hero_default_stencil_validation import CLASSES,path
from .hero_default_ragdoll_validation import primary_state
from .hero_parent_test_profiles import defaults
from .health_changed_observation import health_component,health
from .inventory_wait_transitions import end_owned_respawn
from .death_started_observation import senses
from . import hero_default_death_mixin as policy,death_started_mixin as death,ragdoll_mixin as ragdoll,equipment_hide_mixin as hiding
from .hero_default_death_contract import KINDS,SCENARIOS,FALSE_FIELDS,require,validate

def entries(values):return values['python_calls']+values['fallback_calls']

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.contexts=[];self.actors=[];self.roots=[];self.selector=None;self.owner=None;self.actor=None;self.pawndata=None;self.original_montages=None;self.index=0
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.primary_before=primary_state(self.pawn);self.shooter_owner=ue.describe_function(self.pawn.get_class(),policy.BOUND_EVENT)['owner'];self.cls=ue.load_class(policy.CLASS);self.selector=self.cls.get_cdo().get_property(policy.SELECTOR);ue.register_declared_mixin(self.cls);self.classes={k:ue.load_class(v) for k,v in CLASSES.items()};self.pawndata=self.controller.PlayerState.get_property('PawnData');self.pawnclass=self.pawndata.get_property('PawnClass');self.mesh_asset=self.pawn.get_property('Mesh').call_function('GetSkeletalMeshAsset');self.anim_class=self.pawn.get_property('Mesh').call_function('GetAnimInstance').get_class();self.control=ue.load_object(ue.find_class('PhysicsAsset'),'/Game/UEPValidation/PA_HeroDefaultRagdollControl.PA_HeroDefaultRagdollControl');self.definition=ue.load_class('/Game/UEPValidation/BP_ParentHideWeaponDefinition.BP_ParentHideWeaponDefinition_C')
        for obj in (self.cls,self.mesh_asset,self.anim_class,self.control,self.definition,self.pawndata,self.pawnclass)+tuple(self.classes.values()):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        self.queue=[(p,k,n) for p in ('BlueprintFallback','Python') for k in KINDS for n in (SCENARIOS if k=='parent' else ('default',))];self.start_case()
    def silence_ui(self):
        for widget in ue.tobject_iterator(ue.find_class('CommonActivatableWidget')):
            if valid(widget) and widget.call_function('GetOwningPlayer')==self.owner:widget.call_function('DeactivateWidget')
    def start_case(self):
        self.profile,self.kind,self.name=self.queue[self.index]
        try:
            with defaults(self.classes[self.kind],self.profile):
                self.pawndata.set_property('PawnClass',self.classes[self.kind]);self.owner=self.statics.call_function('CreatePlayer',self.world,-1,True)
        finally:self.pawndata.set_property('PawnClass',self.pawnclass)
        require(valid(self.owner) and self.owner!=self.controller,'owned native local player missing');self.actor=self.owner.get_controlled_pawn();require(valid(self.actor) and self.actor.get_class()==self.classes[self.kind],'native GameMode did not spawn requested parent family class');self.contexts=[self.owner,self.owner.get_property('PlayerState')];self.actors=[self.actor];self.silence_ui();self.actor.set_actor_location(ue.FVector(200000.+self.index*1000.,200000.,5000.));self.mesh=self.actor.get_property('Mesh');self.mesh.call_function('SetPhysicsAsset',self.control,True);self.mesh.call_function('SetSkeletalMeshAsset',self.mesh_asset);self.mesh.call_function('SetAnimInstanceClass',self.anim_class);self.mesh.call_function('SetEnableGravity',False);self.mesh.call_function('SetLinearDamping',0.);self.mesh.call_function('SetAngularDamping',0.);self.actor.get_property('CharacterMovement').call_function('SetMovementMode',5,0);ue.set_mixin_profile(self.actor,self.profile);self.enter('startup')
    def prepare_death(self):
        self.original_montages=list(self.actor.get_property('Death Montages'));configured=self.original_montages[:1] if self.name=='single-montage' else [] if self.name=='empty-montages' else self.original_montages
        if self.name=='single-montage':require(configured,'original parent has no montage for single control')
        self.actor.set_property('Death Montages',configured);self.manager=self.actor.get_component_by_type(ue.find_class('LyraEquipmentManagerComponent'))
        if not valid(self.manager):self.manager=self.actor.add_actor_component(ue.find_class('LyraEquipmentManagerComponent'),'UEPParentDeathEquipment')
        self.instance=self.manager.call_function('EquipItem',self.definition);self.weapons=list(self.instance.call_function('GetSpawnedActors'));require(len(self.weapons)==2,'native owned death weapon producer missing');self.actors.extend(self.weapons)
        for a in self.weapons:a.call_function('SetActorHiddenInGame',False)
        self.before_senses=senses(self.actor);self.signals=[];scope=SubscriptionScope()
        def observe(owner):self.signals.append(dict(actor=path(owner),health=health(self.actor),montage=path(self.actor.call_function('GetCurrentMontage')),senses=senses(self.actor)))
        scope.bind_event(health_component(self.actor),'OnDeathStarted',observe);self.entry=self.game_time();self.max_delta=float(self.statics.call_function('GetWorldDeltaSeconds',self.world));self.counts_ref=death.evidence(self.actor);self.ragdoll_ref=ragdoll.evidence(self.actor);self.hide_ref=hiding.evidence(self.actor)
        try:death_damage.apply(self.asc,health(self.actor))
        finally:scope.close()
        require(len(self.signals)==1,'actual native Health delegate did not fire once');signal=self.signals[0];self.row=dict(profile=self.profile,kind=self.kind,name=self.name,actor_path=path(self.actor),native_lethal_gas_producer=True,native_health_after=signal['health'],native_delegate_callbacks=len(self.signals),native_delegate_payload_matches_actor=signal['actor']==path(self.actor),target_function_is_parent_router=self.actor.find_function(policy.BOUND_EVENT).get_class().get_name()=='PythonFunction' and ue.describe_function(self.actor.get_class(),policy.BOUND_EVENT)['owner']==policy.CLASS,configured_montages=[path(v) for v in configured],prefix_current_montage=signal['montage'],source_sight_removed='/Script/AIModule.AISense_Sight' in self.before_senses and '/Script/AIModule.AISense_Sight' not in signal['senses'],other_senses_unchanged=sorted(v for v in self.before_senses if v!='/Script/AIModule.AISense_Sight')==sorted(signal['senses']),owned_actor_not_rooted=not self.actor.is_rooted(),entry_game_seconds=self.entry,profile_before_resume=self.profile)
        self.report['cases'].append(self.row)
        if self.name=='switch-pending':self.row['profile_before_resume']='Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback';ue.set_mixin_profile(self.actor,self.row['profile_before_resume'])
        if self.name=='destroy-pending':
            self.restore_montages();self.snapshot=(copy.deepcopy(self.counts_ref),copy.deepcopy(self.ragdoll_ref),copy.deepcopy(self.hide_ref));self.close_context();self.enter('destroyed')
        else:self.enter('delay')
    def observe(self):
        self.silence_ui();require(time.monotonic()-self.phase_started<35.,'parent death phase timeout: '+self.phase);self.max_delta=max(getattr(self,'max_delta',0.),float(self.statics.call_function('GetWorldDeltaSeconds',self.world)))
        if self.phase=='startup':
            self.asc=ability_system(self.actor)
            if not valid(self.asc) or health(self.actor)<=0:return
            end_owned_respawn(self.actor)
            for spec in list(self.asc.get_property('ActivatableAbilities').Items):
                if valid(spec.Ability) and spec.Ability.get_class().get_name()=='GA_SpawnEffect_C':
                    for a in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances):
                        if valid(a) and a!=spec.Ability and a.get_property('bIsActive'):a.call_function('K2_CancelAbility')
            if self.asc.call_function('HasMatchingGameplayTag',ue.find_struct('GameplayTag')(TagName='Gameplay.DamageImmunity')):return
            if not valid(self.mesh.call_function('GetAnimInstance')):return
            self.prepare_death();return
        if self.phase=='destroyed':
            if self.game_time()-self.entry<.8:return
            self.row.update(observed_after_destroy_game_seconds=self.game_time()-self.entry,no_late_work_after_destroy=(self.counts_ref,self.ragdoll_ref,self.hide_ref)==self.snapshot);self.complete_case();return
        if entries(self.ragdoll_ref)<1 or entries(self.hide_ref)<1:return
        self.row.update(endpoint_game_seconds=self.game_time(),all_owned_weapon_actors_hidden=all(a.get_property('bHidden') for a in self.weapons),native_ragdoll_collision_and_simulation=str(self.mesh.call_function('GetCollisionProfileName'))=='Ragdoll' and bool(self.mesh.call_function('IsSimulatingPhysics',self.actor.get_property('RagdollImpulseBone'))),endpoint_profile_matches_switch=(self.ragdoll_ref['python_calls']==int(self.row['profile_before_resume']=='Python') and self.hide_ref['python_calls']==int(self.row['profile_before_resume']=='Python')));self.restore_montages();self.close_context();self.complete_case()
    def restore_montages(self):
        self.actor.set_property('Death Montages',self.original_montages);self.row['original_montages_restored']=list(self.actor.get_property('Death Montages'))==self.original_montages
    def close_context(self):
        if valid(self.actor):
            m=self.actor.get_component_by_type(ue.find_class('LyraEquipmentManagerComponent'))
            if valid(m):
                for i in list(m.call_function('GetEquipmentInstancesOfType',ue.find_class('LyraEquipmentInstance'))):m.call_function('UnequipItem',i)
            ue.clear_mixin_profile(self.actor)
        if valid(self.owner):self.statics.call_function('RemovePlayer',self.owner,True)
        if valid(self.actor):self.actor.actor_destroy()
        for c in self.contexts:
            if valid(c) and c!=self.controller:c.actor_destroy()
        closed=all(not valid(a) for a in self.actors+self.contexts)
        if hasattr(self,'row'):self.row['owned_context_destroyed']=closed
        require(closed,'owned parent death context cleanup incomplete');self.owner=None;self.contexts=[];self.actors=[]
    def complete_case(self):
        self.row.update(counts=copy.deepcopy(self.counts_ref),ragdoll_calls=entries(self.ragdoll_ref),hide_calls=entries(self.hide_ref),maximum_world_delta=self.max_delta);self.index+=1;self.original_montages=None
        if self.index<len(self.queue):self.start_case()
        else:self.finish()
    def cleanup(self):
        if valid(self.actor) and self.original_montages is not None and hasattr(self,'row'):self.restore_montages()
        self.close_context()
        for a in self.actors:
            if valid(a):a.actor_destroy()
        if valid(self.pawndata):self.pawndata.set_property('PawnClass',self.pawnclass)
        if self.selector is not None:self.cls.get_cdo().set_property(policy.SELECTOR,self.selector)
        for obj in self.roots:obj.remove_from_root()
        self.report.update(primary_player_inventory_health_and_physics_unchanged=capture(self.controller)==self.player_before and self.healths()==self.health_before and primary_state(self.pawn)==self.primary_before,existing_shooter_child_router_owner_preserved=ue.describe_function(self.pawn.get_class(),policy.BOUND_EVENT)['owner']==self.shooter_owner,owned_contexts_profiles_roots_and_selectors_restored=all(not valid(a) for a in self.actors+self.contexts) and all(not obj.is_rooted() for obj in self.roots) and self.cls.get_cdo().get_property(policy.SELECTOR)==self.selector,shared_pawn_data_class_restored=self.pawndata.get_property('PawnClass')==self.pawnclass)
        for flag,key in (('UEPHeroDeathDescendantHashes','original_descendant_file_hashes_unchanged'),('UEPHeroDeathPhysicsHashes','original_physics_source_hashes_unchanged')):
            hashes=json.loads(Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+flag+'='))).read_text(encoding='utf-8-sig'));self.report[key]=all(hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()==h.upper() for p,h in hashes.items())
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<420.,'parent death readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_HERO_PARENT_DEATH_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HERO_PARENT_DEATH_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroParentDeathResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
