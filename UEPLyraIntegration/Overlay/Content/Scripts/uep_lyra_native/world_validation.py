"""Actual frontend callbacks, possessed cosmetic actors and ability camera cleanup."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import LyraCharacterPart,GameplayAbilitySpecHandle,GameplayTag,GameplayEventData
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system,valid
from . import global_policy,world_policies


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def path(value):return value.get_path_name() if valid(value) else None
def require(value,message):
    if not value:raise AssertionError(message)
def output_array(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeWorldPolicyResult'));self.kind=arg('UEPNativeWorldPolicyKind');self.profile=arg('UEPNativeWorldPolicyProfile')
        self.started=time.monotonic();self.finished=False;self.phase='ready';self.actors=[];self.handles=[]
        self.cls=ue.load_class(global_policy.CLASS);ue.register_declared_mixin(self.cls);self.cdo=self.cls.get_cdo()
        self.original_profile=self.cdo.get_property('PythonMixinProfile');self.cdo.set_property('PythonMixinProfile',self.profile)
        self.fixture=ue.find_class('UEPNativeWorldPolicyFixture').get_cdo();self.statics=ue.find_class('GameplayStatics').get_cdo()
        self.report=dict(status='running',error=None,kind=self.kind,profile=self.profile,online_service_tested=False,physical_input_tested=False,network_replication_tested=False,callbacks_replayed=self.kind=='frontend')
    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3):continue
            if self.kind=='frontend':
                if 'L_LyraFrontEnd' not in world.get_name():continue
                components=[c for c in ue.tobject_iterator(ue.find_class('LyraFrontendStateComponent')) if valid(c) and c.get_world()==world]
                if len(components)!=1 or self.fixture.call_function('FrontendLoading',components[0]):continue
                self.world=world;self.frontend=components[0]
            else:
                if 'L_Expanse' not in world.get_name():continue
                bridge=ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',world)
                if not valid(bridge):continue
                snap=bridge.call_function('CaptureSnapshot')
                if not(snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
                self.world=world;self.controller=self.statics.call_function('GetPlayerController',world,0);self.pawn=self.controller.get_controlled_pawn()
                isolate_bots(self.statics,world,ue.find_class('AIController'))
            self.host=ue.find_class('UEPNativeGameplayPolicySubsystem').get_cdo().call_function('GetPolicyForContext',self.world)
            require(str(ue.get_mixin_profile(self.host))==self.profile,'world policy did not use the selected startup profile')
            if self.kind=='frontend':self.test_frontend()
            elif self.kind=='camera':self.test_camera()
            else:self.start_parts()
            return
    def test_frontend(self):
        self.report['actual_offline_frontend_completed']=not self.fixture.call_function('FrontendLoading',self.frontend)
        self.report['native_initialization_callback_results']=[dict(success=success,continued_and_unbound=bool(self.fixture.call_function('UserInitializationCallback',self.frontend,success))) for success in (True,False)]
        self.report['initialization_callback_results_supplied_by_fixture']=True
        self.finish()
    def test_camera(self):
        self.hero=self.pawn.get_component_by_type(ue.find_class('LyraHeroComponent'));asc=ability_system(self.pawn)
        initial=self.fixture.call_function('CameraChoice',self.hero);require(valid(initial),'native PawnData camera missing')
        death=ue.load_class('/Game/Characters/Heroes/Abilities/GA_Hero_Death.GA_Hero_Death_C').get_cdo()
        mode=death.get_property('Camera Mode');require(valid(mode) and mode!=initial,'distinct original concrete ability camera required')
        self.protection=ue.find_class('UEPNativeProtectionFixture').get_cdo();self.asc=asc
        handle=self.protection.call_function('GrantActive',asc,False);self.handles.append(handle)
        spec=next(s for s in asc.get_property('ActivatableAbilities').Items if int(s.Handle.Handle)==int(handle.Handle))
        ability=next(a for a in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(a))
        ability.call_function('SetCameraMode',mode)
        active=self.fixture.call_function('CameraChoice',self.hero)
        self.fixture.call_function('ClearCamera',self.hero,GameplayAbilitySpecHandle())
        wrong_handle=self.fixture.call_function('CameraChoice',self.hero)
        require(self.protection.call_function('RemoveWitness',asc,handle),'camera ability cleanup failed');self.handles=[]
        restored=self.fixture.call_function('CameraChoice',self.hero)
        missing=[]
        for index,owner_class in enumerate(('Actor','LyraCharacter')):
            owner=self.world.actor_spawn(ue.find_class(owner_class),ue.FVector(250000.+index*1000.,250000.,3000.));self.actors.append(owner)
            hero=ue.new_object(ue.find_class('LyraHeroComponent'),owner)
            missing.append(self.fixture.call_function('CameraChoice',hero) is None)
        self.report['camera']=dict(default=path(initial),ability_mode=path(mode),ability_priority=active==mode,foreign_handle_preserves=wrong_handle==mode,actual_ability_end_restores=restored==initial,missing_pawn_and_data_return_null=missing,native_ability_camera_methods=True)
        self.finish()
    def start_parts(self):
        self.owner=self.controller;self.old=self.pawn
        self.parts=self.owner.get_component_by_type(ue.find_class('LyraControllerComponent_CharacterParts'))
        require(valid(self.parts),'original controller parts component missing')
        self.saved_parts=list(self.parts.get_property('CharacterParts'))
        self.saved_sources=[int(row.Source) for row in output_array(self.fixture.call_function('PartRows',self.parts))]
        self.parts.call_function('RemoveAllCharacterParts');self.part=LyraCharacterPart(PartClass=ue.find_class('Actor'))
        for source in (0,0,2,3):self.fixture.call_function('AddSourcePart',self.parts,self.part,source)
        self.report['parts']=dict(sources_before=self.rows(),actors_before=self.part_actors(self.old));self.phase='parts-suppress';self.since=time.monotonic()
    def rows(self):return [dict(source=int(r.Source),valid=bool(r.bHandleValid)) for r in output_array(self.fixture.call_function('PartRows',self.parts))]
    def part_actors(self,pawn):
        component=pawn.get_component_by_type(ue.find_class('LyraPawnComponent_CharacterParts'))
        return [path(a) for a in output_array(component.call_function('GetCharacterPartActors')) if valid(a)]
    def parts_step(self):
        if time.monotonic()-self.since<.1:return
        if self.phase=='parts-settle':
            asc=ability_system(self.owner.PlayerState)
            active=[a for spec in asc.get_property('ActivatableAbilities').Items
                if valid(spec.Ability) and 'GA_SpawnEffect' in spec.Ability.get_class().get_name()
                for a in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances)
                if valid(a) and a.get_property('bIsActive')]
            if active:return
            self.report['parts']['original_spawn_effect_completed_before_owned_state_cleanup']=True
            self.finish();return
        if self.phase=='parts-reset-wait':
            pawn=self.owner.get_controlled_pawn()
            if not valid(pawn) or pawn==self.old:return
            health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
            if not valid(health) or health.call_function('GetHealth')<=0:return
            self.new=pawn;self.phase='parts-attach';self.since=time.monotonic();return
        row=self.report['parts']
        if self.phase=='parts-suppress':
            self.fixture.call_function('SuppressParts',self.parts,True);row['suppressed']=self.rows();row['actors_suppressed']=self.part_actors(self.old)
            self.fixture.call_function('SuppressParts',self.parts,False);row['unsuppressed']=self.rows()
            self.parts.call_function('RemoveCharacterPart',self.part);row['remove_first_equivalent']=self.rows()
            state=self.owner.PlayerState;tag=GameplayTag(TagName='GameplayEvent.RequestReset')
            ue.find_class('AbilitySystemBlueprintLibrary').get_cdo().call_function('SendGameplayEventToActor',state,tag,GameplayEventData(EventTag=tag,Instigator=state,Target=state))
            row['detached']=self.rows();row['old_actor_count_after_detach']=len(self.part_actors(self.old)) if valid(self.old) else 0
            row['pawn_replacement_entry']='original native Reset request'
            self.phase='parts-reset-wait';self.since=time.monotonic()
        else:
            row['attached']=self.rows();before=self.part_actors(self.new)
            self.fixture.call_function('NotifyPossession',self.parts,None,self.new);row['duplicate_notification_preserved_actors']=self.part_actors(self.new)==before
            self.fixture.call_function('NotifyPossession',self.parts,self.new,self.new);row['same_pawn_notification']=self.rows()
            self.parts.call_function('RemoveAllCharacterParts');row['removed_all']=not self.rows() and not self.part_actors(self.new)
            row['original_component_and_replication_implementation_retained']=True;self.phase='parts-settle'
    def cleanup(self):
        if hasattr(self,'saved_parts'):
            self.parts.call_function('RemoveAllCharacterParts')
            for part,source in zip(self.saved_parts,self.saved_sources):self.fixture.call_function('AddSourcePart',self.parts,part.Part,source)
            restored=self.rows()
            self.report['parts_restored']=len(restored)==len(self.saved_sources) and [r['source'] for r in restored]==self.saved_sources
        if getattr(self,'handles',None):
            for handle in self.handles:self.protection.call_function('RemoveWitness',self.asc,handle)
            self.handles=[]
        for actor in reversed(self.actors):
            if valid(actor):actor.actor_destroy()
        self.cdo.set_property('PythonMixinProfile',self.original_profile)
        self.report['selector_restored']=self.cdo.get_property('PythonMixinProfile')==self.original_profile
        self.report['owned_actors_destroyed']=all(not valid(actor) for actor in self.actors)
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<180.,'world validation timeout: '+self.phase)
            if self.phase=='ready':self.ready()
            else:self.parts_step()
            atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        if hasattr(self,'host'):self.report['world_policy_metrics']=copy.deepcopy(world_policies.metrics(self.host))
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_WORLD_'+('FAILED '+error if error else 'READY'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            self.report['status']='passed'
            try:
                from .world_validation_contract import validate
                validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report)
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_WORLD_SHUTDOWN_'+self.report['status'].upper())


validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
