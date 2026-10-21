"""Real EquipItem/GetSpawnedActors/UnequipItem through direct/inherited parent."""
import atexit,hashlib,json,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from .hero_default_stencil_validation import CLASSES
from . import hero_default_equipment_mixin as policy,equipment_hide_mixin as hiding
from .hero_default_equipment_contract import FALSE_FIELDS,KINDS,require,validate
def path(obj):return obj.get_path_name() if valid(obj) else None
def count(a):return hiding.evidence(a)['python_calls']+hiding.evidence(a)['fallback_calls']
def manager(a):return a.get_component_by_type(ue.find_class('LyraEquipmentManagerComponent'))
def all_instances(m):return list(m.call_function('GetEquipmentInstancesOfType',ue.find_class('LyraEquipmentInstance'))) if valid(m) else []
def equipment_identity(m):return [(path(i),[path(a) for a in i.call_function('GetSpawnedActors')]) for i in all_instances(m)]
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.actors=[];self.spawned=[];self.instance_refs=[];self.selector=None;self.roots=[]
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.primary_equipment=equipment_identity(manager(self.pawn));self.primary_visibility={path(a):bool(a.get_property('bHidden')) for i in all_instances(manager(self.pawn)) for a in i.call_function('GetSpawnedActors') if valid(a)};self.shooter_owner_before=ue.describe_function(self.pawn.get_class(),'HideEquippedWeapons')['owner'];self.cls=ue.load_class(policy.CLASS);self.selector=self.cls.get_cdo().get_property(policy.SELECTOR);ue.register_declared_mixin(self.cls);self.caller=ue.load_class('/Game/UEPValidation/BP_HeroDefaultEquipmentCaller.BP_HeroDefaultEquipmentCaller_C').get_cdo();self.defs={key:ue.load_class('/Game/UEPValidation/BP_ParentHide'+key+'Definition.BP_ParentHide'+key+'Definition_C') for key in ('Weapon','Other','EmptyWeapon')}
        for obj in [self.cls,self.caller]+list(self.defs.values()):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        self.classes={key:ue.load_class(value) for key,value in CLASSES.items()};self.queue=[(p,k) for p in ('BlueprintFallback','Python') for k in KINDS];self.case_index=0;self.enter('cases')
    def run_scenario(self,actor,row,name,calls=1):
        m=manager(actor);instances=all_instances(m);weapons=[i for i in instances if i.is_a(ue.find_class('LyraWeaponInstance'))];weapon_actors=[a for i in weapons for a in i.call_function('GetSpawnedActors') if valid(a)];others=[a for i in instances if not i.is_a(ue.find_class('LyraWeaponInstance')) for a in i.call_function('GetSpawnedActors') if valid(a)];before_other={path(a):bool(a.get_property('bHidden')) for a in others};before_identity=equipment_identity(m);before_hidden=bool(actor.get_property('bHidden'));before=count(actor)
        for _ in range(calls):self.caller.call_function('Hide',actor)
        row['scenarios'].append(dict(name=name,calls=calls,route_delta=count(actor)-before,all_weapon_actors_hidden=all(a.get_property('bHidden') for a in weapon_actors),nonweapon_actor_visibility_unchanged=all(bool(a.get_property('bHidden'))==before_other[path(a)] for a in others),pawn_visibility_and_equipment_identity_unchanged=bool(actor.get_property('bHidden'))==before_hidden and equipment_identity(manager(actor))==before_identity))
    def observe(self):
        require(time.monotonic()-self.phase_started<90.,'parent equipment case timeout')
        if self.case_index>=len(self.queue):self.finish();return
        profile,kind=self.queue[self.case_index];actor=self.world.actor_spawn(self.classes[kind],ue.FVector(200000.+self.case_index*1000.,200000.,2000.));self.actors.append(actor);actor.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);ue.set_mixin_profile(actor,profile);m=manager(actor)
        if not valid(m):m=actor.add_actor_component(ue.find_class('LyraEquipmentManagerComponent'),'UEPParentHideEquipmentManager')
        require(not all_instances(m),'new native equipment fixture is not empty');row=dict(profile=profile,kind=kind,target_function_is_parent_router=actor.find_function('HideEquippedWeapons').get_class().get_name()=='PythonFunction' and ue.describe_function(actor.get_class(),'HideEquippedWeapons')['owner']==policy.CLASS,scenarios=[]);self.report['cases'].append(row);self.run_scenario(actor,row,'empty-manager');weapon=m.call_function('EquipItem',self.defs['Weapon']);other=m.call_function('EquipItem',self.defs['Other']);self.instance_refs.extend([weapon,other]);weapon_actors=list(weapon.call_function('GetSpawnedActors'));other_actors=list(other.call_function('GetSpawnedActors'));self.spawned.extend(weapon_actors+other_actors);row['native_manager_equipped_real_instances_and_actors']=len(weapon_actors)==2 and len(other_actors)==1 and weapon.is_a(ue.find_class('LyraWeaponInstance')) and not other.is_a(ue.find_class('LyraWeaponInstance'))
        for a in weapon_actors+other_actors:a.call_function('SetActorHiddenInGame',False)
        self.run_scenario(actor,row,'equipped-types');self.run_scenario(actor,row,'repeat',2);self.run_scenario(actor,row,'already-hidden');empty=m.call_function('EquipItem',self.defs['EmptyWeapon']);self.instance_refs.append(empty);require(not empty.call_function('GetSpawnedActors'),'empty weapon definition spawned an actor');self.run_scenario(actor,row,'empty-weapon-instance')
        for i in all_instances(m):m.call_function('UnequipItem',i)
        row['native_unequip_destroyed_all_fixture_spawned_actors']=all(not valid(a) for a in weapon_actors+other_actors);m.destroy_component();self.run_scenario(actor,row,'missing-manager');ue.clear_mixin_profile(actor);actor.actor_destroy();self.case_index+=1
    def cleanup(self):
        for actor in self.actors:
            if valid(actor):
                m=manager(actor)
                for i in all_instances(m):m.call_function('UnequipItem',i)
                ue.clear_mixin_profile(actor);actor.actor_destroy()
        for actor in self.spawned:
            if valid(actor):actor.actor_destroy()
        if self.selector is not None:self.cls.get_cdo().set_property(policy.SELECTOR,self.selector)
        for obj in self.roots:obj.remove_from_root()
        self.report['existing_shooter_child_router_owner_preserved']=ue.describe_function(self.pawn.get_class(),'HideEquippedWeapons')['owner']==self.shooter_owner_before;self.report['primary_player_inventory_health_and_equipment_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before and equipment_identity(manager(self.pawn))==self.primary_equipment and {path(a):bool(a.get_property('bHidden')) for i in all_instances(manager(self.pawn)) for a in i.call_function('GetSpawnedActors') if valid(a)}==self.primary_visibility;self.report['owned_actors_equipment_instances_profiles_roots_and_selectors_restored']=all(not valid(a) for a in self.actors+self.spawned) and all(not obj.is_rooted() for obj in self.roots) and self.cls.get_cdo().get_property(policy.SELECTOR)==self.selector
        file=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroEquipmentDescendantHashes=')));hashes=json.loads(file.read_text(encoding='utf-8-sig'));self.report['original_descendant_file_hashes_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()==v.upper() for p,v in hashes.items())
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'parent equipment readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_HERO_PARENT_EQUIPMENT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HERO_PARENT_EQUIPMENT_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroParentEquipmentResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
