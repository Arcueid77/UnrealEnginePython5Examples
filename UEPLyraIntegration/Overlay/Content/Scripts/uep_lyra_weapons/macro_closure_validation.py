"""Run exact original macro VM and Python helpers on the same native objects."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid
from .hero_burst_cue_validation import Validation as Ready
from .hero_burst_cue_mixin import lib
from . import macro_policies as policy
from .macro_closure_contract import FALSE_FIELDS,require,validate


def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,weapon_cases=[],ammo_cases=[],tag_cases=[],specific_cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.actors=[];self.spawn_before=None;self.mag_before=None
    def pawn_actor(self):
        actor=self.world.actor_spawn(ue.find_class('Pawn'));self.actors.append(actor);return actor
    def actor(self):
        actor=self.world.actor_spawn(ue.find_class('Actor'));self.actors.append(actor);actor.add_actor_root_component(ue.find_class('SceneComponent'),'UEPMacroRoot');return actor
    def begin(self):
        self.report['native_mode']=str(lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.probe=self.world.actor_spawn(ue.load_class('/Game/UEPValidation/BP_MacroClosureProbe.BP_MacroClosureProbe_C'));self.actors.append(self.probe);manager=self.pawn.get_component_by_type(ue.find_class('LyraEquipmentManagerComponent'));instances=manager.call_function('GetEquipmentInstancesOfType',ue.find_class('LyraWeaponInstance'));require(instances and valid(instances[0]),'real equipped weapon instance required');self.equipped=instances[0];self.spawn_before=list(self.equipped.call_function('GetSpawnedActors'));require(self.spawn_before and valid(self.spawn_before[0]),'real native spawned weapon required');self.weapon=self.spawn_before[0];self.wrong=self.actor()
        for name,actors in (('normal',self.spawn_before),('empty',[]),('wrong-first',[self.wrong]),('wrong-then-valid',[self.wrong,self.weapon]),('null-then-valid',[None,self.weapon]),('valid-then-wrong',[self.weapon,self.wrong])):
            self.equipped.set_property('SpawnedActors',actors);found,native=self.probe.call_function('Weapon',self.pawn);python=policy.weapon_for(self.pawn);same=bool(found)==valid(python) and native==python;self.report['weapon_cases'].append(dict(name=name,native_found=bool(found),python_found=valid(python),matches=same));require(same,'exact native weapon macro differs: '+name)
        self.equipped.set_property('SpawnedActors',self.spawn_before);bare=self.pawn_actor();found,native=self.probe.call_function('Weapon',bare);python=policy.weapon_for(bare);self.report['weapon_cases'].append(dict(name='no-equipment-manager',native_found=bool(found),python_found=valid(python),matches=not found and python is None));require(not found and python is None,'missing equipment macro path differs')
        echo=self.pawn_actor();self.echo=echo;quick=self.controller.get_component_by_type(ue.find_class('LyraQuickBarComponent'));self.item=quick.call_function('GetActiveSlotItem');require(valid(self.item),'real active slot item required');self.mag_before=int(self.item.call_function('GetStatTagStackCount',GameplayTag(TagName=policy.MAGAZINE)))
        for name,instigator,ammo in (('no-instigator',None,None),('no-controller',bare,None),('zero',self.pawn,0),('one',self.pawn,1),('many',self.pawn,17)):
            echo.set_property('Instigator',instigator)
            if ammo is not None:self.set_mag(ammo)
            completed,value=self.probe.call_function('Ammo',echo);py_done,py_value,diagnostic=policy.weapon_ammo(echo);same=bool(completed)==py_done and (not completed or int(value)==py_value) and not diagnostic;self.report['ammo_cases'].append(dict(name=name,native_completed=bool(completed),native_ammo=int(value),python_completed=py_done,python_ammo=py_value,matches=same));require(same,'exact native ammo macro differs: '+name)
        self.set_mag(self.mag_before);owner=self.actor();mesh=owner.add_actor_component(ue.find_class('SkeletalMeshComponent'),'UEPMacroMesh',owner.get_property('RootComponent'));self.mesh=mesh
        for tags in ([],['ignore'],['IGNORE'],['ignored']):
            mesh.set_property('ComponentTags',tags);native=bool(one(self.probe.call_function('Tag',mesh)));python=policy.ignore_tag(mesh);self.report['tag_cases'].append(dict(tags=tags,native=native,python=python));require(native==python,'exact native component tag macro differs')
        asset=self.pawn.get_property('Mesh').call_function('GetSkeletalMeshAsset');invisible=ue.load_object(ue.find_class('SkeletalMesh'),policy.INVISIBLE)
        for name,value in (('none',None),('visible',asset),('invisible',invisible)):
            mesh.call_function('SetSkeletalMeshAsset',value);native=bool(one(self.probe.call_function('Specific',mesh)));python=policy.ignore_specific(mesh);self.report['specific_cases'].append(dict(name=name,native=native,python=python));require(native==python,'exact native specific mesh macro differs')
        self.report.update(exact_native_weapon_macro_matches=True,exact_native_ammo_completion_and_values_match=True,exact_native_tag_macro_matches=True,exact_native_specific_mesh_macro_matches=True);self.finish()
    def set_mag(self,value):
        tag=GameplayTag(TagName=policy.MAGAZINE);current=int(self.item.call_function('GetStatTagStackCount',tag))
        if current:self.item.call_function('RemoveStatTagStack',tag,current)
        if value:self.item.call_function('AddStatTagStack',tag,int(value))
    def cleanup(self):
        if self.spawn_before is not None:self.equipped.set_property('SpawnedActors',self.spawn_before)
        if self.mag_before is not None:self.set_mag(self.mag_before)
        self.report['original_equipment_spawn_array_and_magazine_restored']=self.spawn_before is not None and list(self.equipped.call_function('GetSpawnedActors'))==self.spawn_before and int(self.item.call_function('GetStatTagStackCount',GameplayTag(TagName=policy.MAGAZINE)))==self.mag_before
        for actor in reversed(self.actors):
            if valid(actor):actor.actor_destroy()
        self.report['all_probe_actors_and_roots_removed']=all(not valid(a) or a.call_function('IsActorBeingDestroyed') for a in self.actors);self.report['original_live_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native macro closure timeout')
            if self.phase=='ready':self.ready()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_MACRO_CLOSURE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_MACRO_CLOSURE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPMacroClosureResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
