"""Owned direct/derived Characters; single-body control isolates native impulse."""
import atexit,copy,hashlib,json,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from .hero_default_stencil_validation import CLASSES,path
from .hero_parent_test_profiles import defaults
from .ragdoll_observation import physical
from . import hero_default_ragdoll_mixin as policy,ragdoll_mixin as ragdoll
from .hero_default_ragdoll_contract import KINDS,SCENARIOS,FALSE_FIELDS,require,validate

def count(a):return ragdoll.evidence(a)['python_calls']+ragdoll.evidence(a)['fallback_calls']

def primary_state(a):
    state=physical(a);state.pop('velocity');mesh=a.get_property('Mesh');state.update(skeletal_mesh=path(mesh.call_function('GetSkeletalMeshAsset')),physics_override=path(mesh.get_property('PhysicsAssetOverride')));return state

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.actors=[];self.controllers=[];self.roots=[];self.selector=None;self.actor=None;self.original_strength=None;self.index=0
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.primary_physics=primary_state(self.pawn);require(not self.primary_physics['simulating'],'primary pawn must remain kinematic');self.report['primary_physics_before']=self.primary_physics;self.shooter_owner_before=ue.describe_function(self.pawn.get_class(),'Ragdoll')['owner'];self.cls=ue.load_class(policy.CLASS);self.selector=self.cls.get_cdo().get_property(policy.SELECTOR);ue.register_declared_mixin(self.cls)
        self.caller=ue.load_class('/Game/UEPValidation/BP_HeroDefaultRagdollCaller.BP_HeroDefaultRagdollCaller_C').get_cdo();self.control=ue.load_object(ue.find_class('PhysicsAsset'),'/Game/UEPValidation/PA_HeroDefaultRagdollControl.PA_HeroDefaultRagdollControl');self.mesh_asset=self.pawn.get_property('Mesh').call_function('GetSkeletalMeshAsset');require(valid(self.mesh_asset),'primary skeletal mesh unavailable')
        for obj in (self.cls,self.caller,self.control,self.mesh_asset):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        require(len(self.control.get_property('SkeletalBodySetups'))==1 and not self.control.get_property('ConstraintSetup'),'one-body control differs');self.classes={k:ue.load_class(v) for k,v in CLASSES.items()};self.queue=[(p,k,n) for p in ('BlueprintFallback','Python') for k in KINDS for n in SCENARIOS];self.start_case()
    def start_case(self):
        self.profile,self.kind,self.name=self.queue[self.index];self.spawn_owned();self.actors.append(self.actor);self.actor.call_function('SetReplicates',False);ue.set_mixin_profile(self.actor,self.profile);self.original_strength=float(self.actor.get_property('RagdollImpulseStrength'));self.actor.set_property('RagdollImpulseStrength',0. if self.name=='zero-strength' else self.original_strength)
        self.mesh=self.actor.get_property('Mesh');self.mesh.call_function('SetPhysicsAsset',self.control,True);self.mesh.call_function('SetSkeletalMeshAsset',self.mesh_asset);self.bone=self.actor.get_property('RagdollImpulseBone');require(int(self.mesh.call_function('GetBoneIndex',self.bone))>=0,'owned native bone absent');self.movement=self.actor.get_property('CharacterMovement');self.movement.call_function('SetMovementMode',5,0)
        self.owner=self.world.actor_spawn(ue.find_class('AIController'));self.controllers.append(self.owner);self.owner.call_function('Possess',self.actor);require(self.owner.get_controlled_pawn()==self.actor,'native AI possession missing')
        if self.name!='stationary':self.actor.call_function('LaunchCharacter',ue.FVector(150.,50.,100.),True,True);self.enter('launch')
        else:self.invoke()
    def spawn_owned(self):
        with defaults(self.classes[self.kind],self.profile):self.actor=self.world.actor_spawn(self.classes[self.kind],ue.FVector(200000.+self.index*1000.,200000.,5000.))
    def invoke(self):
        self.mesh.call_function('SetAllBodiesBelowSimulatePhysics',self.bone,True,True);self.mesh.call_function('SetEnableGravity',False);self.mesh.call_function('SetLinearDamping',0.);self.mesh.call_function('SetAngularDamping',0.);self.mesh.call_function('SetPhysicsLinearVelocity',ue.FVector(3.,4.,5.),False,self.bone);self.movement.call_function('StopMovementImmediately');velocity=ragdoll.vector(self.movement.call_function('GetLastUpdateVelocity'));before=physical(self.actor);counts=copy.deepcopy(ragdoll.evidence(self.actor));hidden=bool(self.actor.get_property('bHidden'));calls=2 if self.name=='repeat' else 1
        for _ in range(calls):self.caller.call_function('Run',self.actor)
        after=ragdoll.evidence(self.actor);self.row=dict(profile=self.profile,kind=self.kind,name=self.name,calls=calls,route_delta=count(self.actor)-counts['python_calls']-counts['fallback_calls'],python_calls_delta=after['python_calls']-counts['python_calls'],fallback_calls_delta=after['fallback_calls']-counts['fallback_calls'],target_function_is_parent_router=self.actor.find_function('Ragdoll').get_class().get_name()=='PythonFunction' and ue.describe_function(self.actor.get_class(),'Ragdoll')['owner']==policy.CLASS,single_body_native_control=self.mesh.get_property('PhysicsAssetOverride')==self.control,native_ai_possession=self.owner.get_controlled_pawn()==self.actor,native_launch_producer=self.name!='stationary',input_velocity=velocity,strength=float(self.actor.get_property('RagdollImpulseStrength')),native_before=before,native_after=physical(self.actor),trace=after['trace'][len(counts['trace']):],python_impulse=after['last_call']['impulse'] if after['last_call'] else None,pawn_hidden_unchanged=bool(self.actor.get_property('bHidden'))==hidden)
        self.report['cases'].append(self.row);self.frame=int(ue.find_class('KismetSystemLibrary').get_cdo().call_function('GetFrameCount'));self.enter('physics')
    def observe(self):
        require(time.monotonic()-self.phase_started<10.,'parent ragdoll native phase timeout')
        if self.phase=='launch':
            if ragdoll.vector(self.movement.call_function('GetLastUpdateVelocity'))[0]>100.:self.invoke()
            return
        frame=int(ue.find_class('KismetSystemLibrary').get_cdo().call_function('GetFrameCount'))
        if frame<self.frame+2:return
        self.row.update(native_after_physics_step=physical(self.actor),native_physics_frames_elapsed=frame-self.frame);self.actor.set_property('RagdollImpulseStrength',self.original_strength);self.row['owned_strength_restored_before_destroy']=float(self.actor.get_property('RagdollImpulseStrength'))==self.original_strength;ue.clear_mixin_profile(self.actor);self.owner.call_function('UnPossess');self.actor.actor_destroy();self.owner.actor_destroy();self.index+=1
        if self.index<len(self.queue):self.start_case()
        else:self.finish()
    def cleanup(self):
        if valid(self.actor) and self.original_strength is not None:self.actor.set_property('RagdollImpulseStrength',self.original_strength)
        for c in self.controllers:
            if valid(c):c.call_function('UnPossess');c.actor_destroy()
        for a in self.actors:
            if valid(a):ue.clear_mixin_profile(a);a.actor_destroy()
        if self.selector is not None:self.cls.get_cdo().set_property(policy.SELECTOR,self.selector)
        for obj in self.roots:obj.remove_from_root()
        self.report['primary_physics_after']=primary_state(self.pawn);self.report['existing_shooter_child_router_owner_preserved']=ue.describe_function(self.pawn.get_class(),'Ragdoll')['owner']==self.shooter_owner_before;self.report['primary_player_inventory_health_and_physics_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before and self.report['primary_physics_after']==self.primary_physics;self.report['owned_actors_controllers_profiles_roots_and_selectors_restored']=all(not valid(a) for a in self.actors+self.controllers) and all(not obj.is_rooted() for obj in self.roots) and self.cls.get_cdo().get_property(policy.SELECTOR)==self.selector
        hashes=json.loads(Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroRagdollDescendantHashes='))).read_text(encoding='utf-8-sig'));self.report['original_descendant_file_hashes_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()==h.upper() for p,h in hashes.items());source=json.loads(Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroRagdollPhysicsHashes='))).read_text(encoding='utf-8-sig'));self.report['original_physics_source_hashes_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()==h.upper() for p,h in source.items())
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'parent ragdoll readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_HERO_PARENT_RAGDOLL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HERO_PARENT_RAGDOLL_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroParentRagdollResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
