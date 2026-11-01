"""Native overlap/timer events; only the fixture duration is shortened."""
import atexit
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import services,capture
from .message_validation import arg
from .inventory_validation_helpers import fingerprint
from . import spawner as policy
from .spawner_validation_contract import require,validate


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeSpawnerResult'));self.profile=arg('UEPNativeSpawnerProfile');self.started=time.monotonic();self.finished=False;self.phase='ready';self.boot=[];self.roots=[];self.pad=None;self.empty_pawn=None;self.scope=None;self.prepared=False
        self.report=dict(status='running',error=None,profile=self.profile,guards=[],timer_callback_replayed=False,native_timer_replaced=False,fixture_cooldown_duration=.6,fixture_overlap_delay=.15)
        for target in (policy.CLASS,policy.CHILD):
            cls=ue.load_class(target)
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
            if target==policy.CLASS:ue.register_declared_mixin(cls)
            self.boot.append((cls,cls.get_cdo().get_property('PythonMixinProfile')));cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        atexit.register(self.finalize)

    def setup(self):
        self.statics=ue.find_class('GameplayStatics').get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
            isolate_bots(self.statics,world,ue.find_class('AIController'))
            bridge=ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snapshot=bridge.call_function('CaptureSnapshot')
            if not (snapshot.bExperienceLoaded and snapshot.bHeroInputReady and snapshot.bAbilitySystemReady and snapshot.bHealthReady and snapshot.Health>0 and not snapshot.bDamageImmune):continue
            controller=self.statics.call_function('GetPlayerController',world,0)
            if capture(controller) is None:continue
            self.world=world;self.controller=controller;self.pawn=controller.get_controlled_pawn();self.inventory,self.quickbar=services(controller)
            isolate_bots(self.statics,world,ue.find_class('AIController'));self.original=fingerprint(controller);self.original_items=list(self.inventory.call_function('GetAllItems'));self.location=self.pawn.get_actor_location();self.mode=int(self.pawn.CharacterMovement.MovementMode)
            self.pawn.CharacterMovement.call_function('DisableMovement');self.prepared=True
            transform=ue.FTransform();transform.translation=ue.FVector(self.location.x+6000.,self.location.y,self.location.z+800.)
            self.pad=self.statics.call_function('BeginDeferredActorSpawnFromClass',world,ue.load_class(policy.CLASS),transform,1,None)
            ue.set_mixin_profile(self.pad,self.profile);self.definition=ue.load_object(ue.find_class('LyraWeaponPickupDefinition'),'/ShooterCore/Weapons/Rifle/WeaponPickupData_Rifle.WeaponPickupData_Rifle')
            self.pad.set_property('WeaponDefinition',self.definition);self.pad.set_property('GiveAmmoForDuplicatedWeapons',False);self.statics.call_function('FinishSpawningActor',self.pad,transform)
            self.pad.set_property('CoolDownTime',.6);self.pad.set_property('CheckExistingOverlapDelay',.15)
            self.empty_pawn=world.actor_spawn(ue.find_class('Pawn'),ue.FVector(self.location.x+9000.,self.location.y,self.location.z+900.));self.scope=SubscriptionScope();self.overlaps=[]
            self.scope.bind_event(self.pad.CollisionVolume,'OnComponentBeginOverlap',lambda component,actor,*args:self.overlaps.append(actor==self.pawn) if actor==self.pawn else None)
            self.base_count=len(self.inventory.call_function('GetAllItems'));return True
        return False

    def guard(self,name,pawn):
        before=fingerprint(self.controller);available=bool(self.pad.bIsWeaponAvailable);self.pad.call_function('AttemptPickUpWeapon',pawn)
        self.report['guards'].append(dict(name=name,unchanged=fingerprint(self.controller)==before and bool(self.pad.bIsWeaponAvailable)==available))

    def execute(self):
        self.guard('null_pawn',None);self.guard('pawn_without_asc',self.empty_pawn)
        self.pad.set_property('WeaponDefinition',None);self.guard('missing_definition',self.pawn);self.pad.set_property('WeaponDefinition',self.definition)
        self.pad.set_property('bIsWeaponAvailable',False);self.guard('unavailable',self.pawn);self.pad.set_property('bIsWeaponAvailable',True)
        item=self.quickbar.call_function('GetSlots')[0]
        for i in (1,2):self.quickbar.call_function('AddItemToSlot',i,item)
        self.guard('full_slots',self.pawn)
        for i in (1,2):self.quickbar.call_function('RemoveItemFromSlot',i)
        self.pad.call_function('AttemptPickUpWeapon',self.pawn);self.report['first_pickup_delta']=len(self.inventory.call_function('GetAllItems'))-self.base_count
        self.report['pickup_diagnostic']=dict(metrics=copy.deepcopy(policy.metrics(self.pad)),definition=self.definition.get_path_name(),item_definition=self.definition.InventoryItemDefinition.get_path_name(),role=int(self.pad.call_function('GetLocalRole')),available=bool(self.pad.bIsWeaponAvailable),asc_valid=valid(ue.find_class('AbilitySystemBlueprintLibrary').get_cdo().call_function('GetAbilitySystemComponent',self.pawn)),slot_free=int(self.quickbar.call_function('GetNextFreeItemSlot')),item_count=len(self.inventory.call_function('GetAllItems')))
        if self.report['first_pickup_delta']!=1:
            from uep_lyra_world.spawner_mixin import snapshot
            def inventory_state():
                return [dict(component=c.get_path_name(),owner=c.call_function('GetOwner').get_path_name(),items=[i.ItemDef.get_path_name() for i in c.call_function('GetAllItems')],serializer_owner=c.get_property('InventoryList').OwnerComponent.get_path_name()) for c in ue.tobject_iterator(ue.find_class('LyraInventoryManagerComponent')) if valid(c) and c.get_world()==self.world and valid(c.call_function('GetOwner'))]
            self.report['pickup_diagnostic']['inventories_before_direct']=inventory_state()
            self.report['pickup_diagnostic']['direct_give_result']=self.pad.call_function('GiveWeapon',self.definition.InventoryItemDefinition,self.pawn)
            self.report['pickup_diagnostic']['after_direct_give_count']=len(self.inventory.call_function('GetAllItems'))
            self.report['pickup_diagnostic']['inventories_after_direct']=inventory_state()
            self.report['pickup_diagnostic']['controller']=self.controller.get_path_name()
            self.report['pickup_diagnostic']['pawn_controller']=self.pawn.call_function('GetController').get_path_name()
            self.report['pickup_diagnostic']['slots_after_direct']=[i.get_path_name() if i else None for i in self.quickbar.call_function('GetSlots')]
            self.report['pickup_diagnostic']['prefix_original_result']=self.pad.call_mixin_original('UEPDispatchSpawnerWeaponGive',self.definition.InventoryItemDefinition,self.pawn)
            self.report['pickup_diagnostic']['bp_policy_stats']=snapshot()
        require(self.report['first_pickup_delta']==1,'native first grant failed: '+str(self.report['pickup_diagnostic']))
        self.report['pickup_visibility_hidden']=not self.pad.bIsWeaponAvailable and not self.pad.WeaponMesh.get_property('bVisible')
        self.pad.call_function('AttemptPickUpWeapon',self.pawn);self.report['cooldown_reentry_delta']=len(self.inventory.call_function('GetAllItems'))-self.base_count-self.report['first_pickup_delta']
        require(self.pawn.set_actor_location(self.pad.CollisionVolume.call_function('K2_GetComponentLocation')),'native standing overlap fixture move failed')
        self.phase='cooldown';self.phase_started=time.monotonic();self.report['timer_reset_visibility_restored']=False

    def observe(self):
        prefix='python_' if self.profile=='Python' else 'native_';m=policy.metrics(self.pad)
        if m[prefix+'complete']>=1 and self.pad.bIsWeaponAvailable and self.pad.WeaponMesh.get_property('bVisible'):self.report['timer_reset_visibility_restored']=True
        require(time.monotonic()-self.phase_started<8.,'native cooldown/standing overlap failed')
        if len(self.inventory.call_function('GetAllItems'))-self.base_count!=2:return
        require(m[prefix+'complete']==1 and not self.pad.bIsWeaponAvailable,'standing pickup did not restart native cooldown')
        self.report.update(standing_overlap_delta=2,overlap_begin_events=len(self.overlaps),destroyed_with_cooldown_pending=True)
        self.counts=policy.metrics(self.pad);self.report['metrics']=copy.deepcopy(self.counts)
        self.scope.close();self.pawn.set_actor_location(self.location);self.pad.call_function('K2_DestroyActor');require(not valid(self.pad),'native spawner destroy failed');self.phase='destroyed';self.destroyed_at=time.monotonic()

    def cleanup(self):
        if self.scope is not None:self.scope.close()
        self.report['scope_closed']=self.scope is None or self.scope.closed and self.scope.count==0
        if self.prepared:
            self.quickbar.call_function('SetActiveSlotIndex',self.original['active'])
            for i,item in enumerate(self.quickbar.call_function('GetSlots')):
                if item is not None and item not in self.original_items:self.quickbar.call_function('RemoveItemFromSlot',i)
            for item in list(self.inventory.call_function('GetAllItems')):
                if item not in self.original_items:self.inventory.call_function('RemoveItemInstance',item)
            self.pawn.set_actor_location(self.location);self.pawn.CharacterMovement.call_function('SetMovementMode',self.mode,0)
            self.report['original_player_and_inventory_restored']=fingerprint(self.controller)==self.original and (self.pawn.get_actor_location()-self.location).size()<.01 and int(self.pawn.CharacterMovement.MovementMode)==self.mode
        for actor in (self.pad,self.empty_pawn):
            if valid(actor):actor.call_function('K2_DestroyActor')
        for cls,old in self.boot:cls.get_cdo().set_property('PythonMixinProfile',old)
        self.report['selectors_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==old for cls,old in self.boot)
        for cls in self.roots:cls.remove_from_root()
        self.roots=[]

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<200.,'native spawner readiness timed out')
            if self.phase=='ready' and self.setup():self.execute()
            elif self.phase=='cooldown':self.observe()
            elif self.phase=='destroyed' and time.monotonic()-self.destroyed_at>.9:self.report['no_callbacks_after_destroy']=self.counts==self.report['metrics'];self.finish()
            return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report);(ue.log_error if error else ue.log)('UEP_NATIVE_SPAWNER_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_SPAWNER_SHUTDOWN_'+self.report['status'].upper())


if any(v.startswith('-UEPNativeSpawnerResult=') for v in __import__('sys').argv):
    validation=Validation();ticker=ue.add_ticker(validation.tick)
