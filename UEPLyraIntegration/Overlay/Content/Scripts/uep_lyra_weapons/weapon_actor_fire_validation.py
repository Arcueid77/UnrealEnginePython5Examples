"""Native child Fire calls observing unchanged original FX Actor entries."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod, ESpawnActorScaleMethod
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from . import weapon_actor_fire_mixin as policy
from .weapon_actor_helpers_mixin import CLASS
from .weapon_actor_fire_contract import CLASSES, PROFILES, CASES, FIELDS, FX, require, validate


def path(value):return value.get_path_name() if valid(value) else None
def vec(value):return [float(value.x),float(value.y),float(value.z)]
def dead(value):return not valid(value) or value.call_function("IsActorBeingDestroyed")


class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False
        self.actors,self.events,self.fx_classes,self.fx_signatures=[],[],[],{}
        self.target_mesh=None;self.recording=False
        self.report=dict(schema_version=1,status="running",error=None,cases=[],observation_errors=[],full_acceptance=False,network_acceptance=False,
            packaged_runtime=False,audio_playback_tested=False,pixels_tested=False,real_gas_firing_tested=False,health_properties_written=False,begin_play_migrated=False)
    def begin(self):
        bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world)
        self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        self.parent=ue.load_class(CLASS);ue.register_declared_mixin(self.parent)
        binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.parent]
        self.original_parent={name:row["python_class"] for name,row in binding["profiles"].items()}
        self.health_before=self.healths();owner=self
        for index,cls_path in enumerate(FX):
            cls=ue.load_class(cls_path);entry="fire" if index==2 else "Fire"
            require(not any(row["target_class"]==cls for row in ue.get_registered_mixins()),"FX class already has a production binding;preserve it")
            self.fx_classes.append(cls);self.fx_signatures[cls_path]=ue.describe_function(cls,entry)
            def observe(slot,method):
                def invoke(actor):
                    if owner.recording:
                        try:
                            root=actor.get_property("RootComponent")
                            row=dict(**{"class":path(actor.get_class())},actor=path(actor),
                                positions=[vec(v) for v in actor.get_property("ImpactPositions")],normals=[vec(v) for v in actor.get_property("ImpactNormals")],
                                surfaces=[int(v) for v in actor.get_property("Impact Surface Types" if slot==2 else "ImpactSurfaceTypes")],
                                attached_to_weapon_mesh=valid(root) and root.call_function("GetAttachParent")==owner.target_mesh)
                            if slot==0:row.update(mesh_is_weapon_mesh=actor.get_property("Skeletal Mesh Component")==owner.target_mesh,
                                enable_flags=[bool(actor.get_property(name)) for name in ("Enable Shell Eject","Enable Muzzle Flash","Enable Tracer")])
                            if slot==1:row.update(muzzle=vec(actor.get_property("MuzzlePosition")),distance_threshold=float(actor.get_property("Distance Threshold")))
                            owner.events.append(row)
                        except Exception:owner.report["observation_errors"].append(traceback.format_exc())
                    return actor.call_mixin_original(method)
                invoke.override=method;return invoke
            ue.register_mixin_profile(cls,"Observer",type("ObservedOriginalWeaponFX"+str(index),(),dict(ObservedFire=observe(index,entry))),make_default=True)
        self.wall=self.world.actor_spawn(ue.find_class("Actor"));self.actors.append(self.wall)
        self.box=self.wall.add_actor_root_component(ue.find_class("BoxComponent"),"UEPFireWall")
        self.box.call_function("SetBoxExtent",ue.FVector(10.,400.,400.),False);self.box.call_function("SetCollisionObjectType",0)
        self.box.call_function("SetCollisionResponseToAllChannels",2);self.box.call_function("SetCollisionEnabled",1)
        self.enter("trial")
    def trial(self):
        cls_path=CLASSES[self.index//2];profile=PROFILES[self.index%2];cls=ue.load_class(cls_path)
        transform=ue.FTransform(ue.FVector(200000.,200000.,2000.),ue.FRotator(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,self.pawn,scale)
        self.actors.append(actor);actor.set_property("Instigator",self.pawn);self.statics.call_function("FinishSpawningActor",actor,transform,scale)
        actor.call_function("SetReplicates",False);ue.set_mixin_profile(actor,profile)
        self.target_mesh=actor.get_property("SkeletalMesh")
        require(valid(self.target_mesh),"native child weapon mesh missing")
        for name in CASES:
            if name=="replace-impact":
                previous=actor.get_property("Weapon Impacts");require(valid(previous),"missing cached impact Actor");previous.call_function("K2_DestroyActor")
            before_refs=[actor.get_property(field) for field in FIELDS]
            start=self.target_mesh.call_function("GetSocketLocation","Muzzle")
            require(self.wall.call_function("K2_TeleportTo",ue.FVector(start.x+1000.,start.y,start.z),ue.FRotator()),"native Fire wall pose refused")
            positions=[ue.FVector(start.x+990.,start.y,start.z)]
            if name=="reuse":positions.append(ue.FVector(start.x+990.,start.y+20.,start.z))
            normals=[ue.FVector(-1.,0.,0.) for _ in positions];surfaces=[0]*len(positions)
            actor.set_property("NeedsFakeProjectileData",name=="fake");actor.set_property("Numer Of Fake Projectiles",2)
            self.events=[];self.recording=True;before=copy.deepcopy(policy.evidence(actor))
            try:actor.call_function("Fire",positions,normals,surfaces)
            finally:self.recording=False
            require(not self.report["observation_errors"],"native original FX observer failed: "+str(self.report["observation_errors"]))
            after=policy.evidence(actor);refs=[actor.get_property(field) for field in FIELDS]
            for target in refs:
                require(valid(target),"native original FX Actor missing")
                if not any(item==target for item in self.actors):self.actors.append(target)
            self.report["cases"].append(dict(name=name,profile=profile,**{"class":path(cls)},input_count=len(positions),events=copy.deepcopy(self.events),
                positions=[vec(v) for v in actor.get_property("Impact Positions")],normals=[vec(v) for v in actor.get_property("Impact Normals")],
                surfaces=[int(v) for v in actor.get_property("ImpactSurfaceTypes")],muzzle=vec(actor.get_property("MuzzlePosition")),
                same_cached=[old==new for old,new in zip(before_refs,refs)],delta={key:after[key]-before[key] for key in after if isinstance(after[key],int)},
                parent_dispatch_verified=after["python_calls" if profile=="Python" else "fallback_calls"]-before["python_calls" if profile=="Python" else "fallback_calls"]==1))
        for target in [actor.get_property(field) for field in FIELDS]:
            if valid(target) and not dead(target):target.call_function("K2_DestroyActor")
        actor.call_function("K2_DestroyActor");self.index+=1
        ue.log("UEP_WEAPON_ACTOR_FIRE_CHILD_CAPTURED "+cls_path+" "+profile)
        if self.index==len(CLASSES)*2:self.finish()
    def cleanup(self):
        for actor in reversed(self.actors):
            if not dead(actor):actor.call_function("K2_DestroyActor")
        self.report["test_actors_destroyed"]=all(dead(actor) for actor in self.actors)
        for cls in self.fx_classes:ue.unregister_mixin(cls)
        self.report["fx_observers_removed"]=not any(row["target_class"] in self.fx_classes for row in ue.get_registered_mixins())
        self.report["original_fx_signatures_restored"]=all(ue.describe_function(cls,"fire" if index==2 else "Fire")==self.fx_signatures[FX[index]] for index,cls in enumerate(self.fx_classes))
        self.report["original_pawn_health_unchanged"]=self.healths()==self.health_before if hasattr(self,"health_before") else False
        rows=[row for row in ue.get_registered_mixins() if row["target_class"]==self.parent] if hasattr(self,"parent") else []
        self.report["production_parent_binding_preserved"]=len(rows)==1 and all(rows[0]["profiles"][name]["python_class"] is base for name,base in self.original_parent.items())
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<180.,"native weapon Fire total timeout")
            if self.phase=="ready":self.ready()
            elif self.phase=="trial":self.trial()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_ACTOR_FIRE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_ACTOR_FIRE_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPWeaponActorFireResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
