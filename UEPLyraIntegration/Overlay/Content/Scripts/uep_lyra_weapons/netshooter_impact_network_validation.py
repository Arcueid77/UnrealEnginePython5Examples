"""Natural predicted impact, original multicast strands and native latent life."""
import atexit
import copy
import math
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.melee_trace_mixin import break_hit
from . import netshooter_network_validation as flight
from .netshooter_network_validation import base,policy,actor_policy
from .netshooter_network_contract import PEERS,PLAN,require
from .netshooter_actor_validation import near,rotation,MESH,MATERIAL
from .weapon_fire_fx_validation import dead


class Witness(flight.Witness):
    def init_witness(self,result,peer,run):
        super().init_witness(result,peer,run);self.rpc_events=[];self.hit_events=[];self.rpc_components=[];self.component_snapshot=[];self.components_stable=0;self.actor_profiles={};self.selector=None
        self.report.update(impact_or_strand_replication_accepted=False,original_template_baseline_fixture_actors=0,projectile_spawn_requested_by_fixture=True,
            gameplay_projectile_spawn_requested_by_fixture=False,native_seed_set_at_actual_hit=True,life_callback_replayed=False)
    def install(self):
        super().install();self.actor_cls=ue.load_class(policy.PROJECTILE);ue.register_declared_mixin(self.actor_cls)
        self.selector=str(self.actor_cls.get_cdo().get_property("PythonMixinProfile"));owner=self
        row,=[r for r in ue.get_registered_mixins() if r["target_class"]==self.actor_cls]
        self.actor_profiles={name:value["python_class"] for name,value in row["profiles"].items()}
        for selected,source in self.actor_profiles.items():
            def around_hit(handler,profile):
                def invoke(actor,HitLocation,HitNormal):
                    watched=owner.watched(actor)
                    if watched:
                        ue.set_random_seed(8191);owner.hit_events.append(dict(profile=profile,time=owner.game_time(),location=base.vector(HitLocation),normal=base.vector(HitNormal)))
                    result=handler(actor,HitLocation,HitNormal)
                    if watched:owner.hit_events[-1]["next_native_random"]=int(policy.lib("KismetMathLibrary").call_function("RandomIntegerInRange",0,32767))
                    return result
                invoke.override=actor_policy.HIT;return invoke
            def around_rpc(handler,profile):
                def invoke(actor,HitResult):
                    watched=owner.watched(actor);before=owner.rays(actor);point=base.vector(actor.get_actor_location())
                    result=handler(actor,HitResult)
                    if watched:
                        owner.report["source_before_native_instigator_refresh"]=dict(type=type(owner.source).__name__,valid=base.valid(owner.source))
                        owner.source=actor.call_function("GetInstigator");owner.humans[owner.command["owner"]]=owner.source
                        owner.actor=actor;parts=break_hit(HitResult);new=[value for value in owner.rays(actor) if value not in before]
                        expected=rotation(policy.lib("KismetMathLibrary").call_function("FindLookAtRotation",parts["TraceStart"],parts["TraceEnd"]))
                        length=float(policy.lib("KismetMathLibrary").call_function("Vector_Distance",parts["TraceStart"],parts["ImpactPoint"]))
                        owner.rpc_components.extend(new);owner.rpc_events.append(dict(profile=profile,time=owner.game_time(),source_identity=base.wire.read(owner.source),new_components=len(new),
                            native_geometry_matches=len(new)==1 and near(base.vector(new[0].call_function("K2_GetComponentLocation")),point) and near(rotation(new[0].call_function("K2_GetComponentRotation")),expected) and near(base.vector(new[0].call_function("K2_GetComponentScale")),[length,3.,3.]),
                            sphere_hidden=bool(actor.get_property("Sphere").get_property("bHiddenInGame"))))
                    return result
                invoke.override=actor_policy.BODY;return invoke
            methods={name:fn for name,fn in vars(source).items() if not name.startswith("__") and callable(fn)}
            methods.update(HitBody=around_hit(source.HitBody,selected),SpawnBody=around_rpc(source.SpawnBody,selected))
            ue.register_mixin_profile(self.actor_cls,selected,type("ObservedNetImpact"+self.peer+selected,(),methods))
    def watched(self,actor):return self.armed and base.wire.same(base.wire.read(actor.call_function("GetInstigator")),self.command["source_identity"])
    def rays(self,actor):return [value for value in actor.call_function("K2_GetComponentsByClass",ue.find_class("StaticMeshComponent")) if value!=actor.get_property("Sphere") and base.valid(value)]
    def warm_baseline(self):
        actor=self.world.actor_spawn(self.actor_cls,ue.FVector(90000.,90000.,40000.));actor.call_function("SetReplicates",False);actor.get_property("ProjectileMovement").call_function("Deactivate")
        ue.set_mixin_profile(actor,"BlueprintFallback");mathlib=policy.lib("KismetMathLibrary")
        start=mathlib.call_function("MakeVector",90000.,90000.,40000.);end=mathlib.call_function("MakeVector",90100.,90000.,40000.);point=mathlib.call_function("MakeVector",90050.,90000.,40000.);normal=mathlib.call_function("MakeVector",0.,0.,1.)
        result=policy.lib("GameplayStatics").call_function("MakeHitResult",bBlockingHit=True,bInitialOverlap=False,Time=.5,Distance=50.,Location=point,ImpactPoint=point,Normal=normal,ImpactNormal=normal,
            PhysMat=None,HitActor=None,HitComponent=None,HitBoneName="None",BoneName="None",HitItem=0,ElementIndex=0,FaceIndex=-1,TraceStart=start,TraceEnd=end)
        ue.log("UEP_NETSHOOTER_BASELINE_TEMPLATE_BEGIN "+actor.get_path_name());actor.call_function("SpawnComponents",result);ue.log("UEP_NETSHOOTER_BASELINE_TEMPLATE_END "+actor.get_path_name())
        actor.call_function("K2_DestroyActor");require(dead(actor),"original-template local fixture not destroyed");self.report["original_template_baseline_fixture_actors"]=1
    def arm(self):
        super().arm();self.rpc_events=[];self.hit_events=[];self.rpc_components=[];self.component_snapshot=[];self.components_stable=0
        self.actor_cls.get_cdo().set_property("PythonMixinProfile",self.command["profile"])
    def component_rows(self):
        rows=[]
        for component in self.rays(self.actor):
            mesh=component.get_property("StaticMesh");material=component.call_function("GetMaterial",0)
            rows.append(dict(wire=base.wire.read(component),from_native_multicast=component in self.rpc_components,mesh=base.path(mesh),material=base.path(material),
                location=base.vector(component.call_function("K2_GetComponentLocation")),rotation=rotation(component.call_function("K2_GetComponentRotation")),scale=base.vector(component.call_function("K2_GetComponentScale")),
                collision=str(component.call_function("GetCollisionProfileName")),replicated=bool(component.get_property("bReplicates"))))
        return rows
    def sample(self):
        # Continue observing destruction every tick, but retain at most ten
        # stationary post-impact trajectory samples per native game second.
        stationary=self.actor is not None and not dead(self.actor) and self.rpc_events and self.actor_profile_selected and self.samples and self.game_time()-self.samples[-1]["time"]<.1
        if not stationary:super().sample()
        if not self.armed or self.actor is None or dead(self.actor):return
        rows=self.component_rows();signature=[(base.wire.key(row["wire"]),row["from_native_multicast"],row["mesh"],row["material"]) for row in rows]
        previous=getattr(self,"component_signature",None);self.components_stable=self.components_stable+1 if signature==previous else 0;self.component_signature=signature;self.component_snapshot=rows
    def snapshot(self):
        row=super().snapshot();row.update(native_rpc_events=copy.deepcopy(self.rpc_events),native_hit_events=copy.deepcopy(self.hit_events),components=copy.deepcopy(self.component_snapshot),components_stable_ticks=self.components_stable,
            authority_fixture_cleanup=False,native_lifetime_seconds=12.,native_delay_elapsed=(self.game_time()-self.hit_events[0]["time"]) if self.hit_events else None)
        return row
    def close_observers(self):
        super().close_observers()
        if self.selector is not None:self.actor_cls.get_cdo().set_property("PythonMixinProfile",self.selector)
        for name,source in self.actor_profiles.items():ue.register_mixin_profile(self.actor_cls,name,source)
        rows=[row for row in ue.get_registered_mixins() if row["target_class"]==self.actor_cls] if hasattr(self,"actor_cls") else []
        self.report["actor_observers_and_selector_restored"]=bool(rows) and all(rows[0]["profiles"][name]["python_class"] is source for name,source in self.actor_profiles.items()) and str(self.actor_cls.get_cdo().get_property("PythonMixinProfile"))==self.selector


class Client(Witness,flight.Client):
    def begin(self):
        super().begin();self.warm_baseline()
    def aim(self):
        if self.peer==self.command["owner"]:self.controller.call_function("SetControlRotation",ue.FRotator(0.,-50.,45.))
        if time.monotonic()-self.prepare_started<.7:return
        if self.controller.get_property("PlayerCameraManager").call_function("GetCameraLocation").z<8000.:return
        self.acknowledge("ready",dict(control=base.rot(self.controller.call_function("GetControlRotation")),native_line_of_sight=True));self.enter("command")
    def collect(self):
        self.sample()
        if self.pending_row is not None:
            if not self.destroyed:return
            self.pending_row["projectile_destruction_observed"]=True;self.report["cases"].append(self.pending_row);self.acknowledge("cleanup",dict(destroyed=True));self.completed=self.position;self.armed=False;self.enter("command");return
        owner=self.peer==self.command["owner"];expected=self.ammo_before-1 if owner else self.ammo_before
        wired=sum(base.wire.key(value["wire"]) is not None for value in self.component_snapshot)
        if self.actor_identity is None or not self.rpc_events or self.components_stable<6 or wired!=len(self.rpc_events) or self.game_time()-self.rpc_events[-1]["time"]<.35 or base.ammo_policy.ammo(self.item)[0]!=expected or len(self.weapon_events)!=1:return
        row=self.snapshot()
        if owner and (len(self.activations)!=1 or len(self.target_data)!=1 or not row["ability_ended"]):return
        row.update(input_gestures=self.input_gestures,input_released=self.released,ammo_before=self.ammo_before,ammo_after=base.ammo_policy.ammo(self.item)[0]);self.pending_row=row;self.acknowledge("done",row)
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":self.report["status"]="passed"
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_NETSHOOTER_IMPACT_SHUTDOWN_"+self.report["status"].upper())


class Server(Witness,flight.Server):
    def __init__(self,result,run):super().__init__(result,run);self.walls=[]
    def setup(self):
        super().setup()
        if self.setup_done:self.warm_baseline()
    def publish(self,stage):
        if stage=="fire":self.arrange_room()
        super().publish(stage)
    def arrange_room(self):
        value=self.owners[self.command["owner"]];controller=value["controller"];camera=controller.get_property("PlayerCameraManager");mathlib=policy.lib("KismetMathLibrary")
        location=camera.call_function("GetCameraLocation");forward=controller.call_function("GetActorForwardVector");direction=mathlib.call_function("Conv_RotatorToVector",camera.call_function("GetCameraRotation"))
        start=[a+b*350. for a,b in zip(base.vector(location),base.vector(forward))];top=value["pawn"].get_actor_location().z-2000.;require(direction.z<-.3,"native downward projectile aim missing")
        length=(top-start[2])/direction.z;center=[start[0]+direction.x*length,start[1]+direction.y*length,top-750.]
        if not self.walls:
            for index in range(6):
                actor=self.world.actor_spawn(ue.find_class("Actor"));box=actor.add_actor_root_component(ue.find_class("BoxComponent"),"UEPNetImpactWall")
                box.call_function("SetMobility",2);box.call_function("SetCollisionObjectType",0);box.call_function("SetCollisionResponseToAllChannels",2);box.call_function("SetCollisionEnabled",1);actor.call_function("SetReplicates",True);self.walls.append((actor,box))
        for index,(actor,box) in enumerate(self.walls):
            axis=index//2;sign=(-1.,1.)[index%2];extent=[760.,760.,760.];extent[axis]=10.;box.call_function("SetBoxExtent",ue.FVector(*extent),False)
            point=list(center);point[axis]+=750.*sign;actor.call_function("K2_SetActorLocation",NewLocation=ue.FVector(*point),bSweep=False,bTeleport=True)
        self.report["authority_only_native_box_colliders_used"]=True
    def step(self):
        if self.stage!="fire":return super().step()
        require(time.monotonic()-self.stage_started<60.,"native impact/multicast/12s Delay timeout");self.sample();selected=self.owners[self.command["owner"]]
        if not self.clearing:
            if self.acks("done") is None or self.actor_identity is None or not self.hit_events or self.components_stable<6:return
            row=self.snapshot();row.update(ammo_before=self.ammo_before,ammo_after=base.ammo_policy.ammo(selected["item"])[0],native_aim_sync=self.native_aim_sync);self.pending_authority_row=row;self.clearing=True
        elif self.destroyed and self.acks("cleanup") is not None:
            row=self.pending_authority_row;row.update(projectile_destruction_observed=True,native_delay_elapsed=self.game_time()-self.hit_events[0]["time"]);self.report["cases"].append(row)
            self.armed=False;self.position+=1
            for tag,count in zip((base.ammo_policy.MAGAZINE,base.ammo_policy.CAPACITY,base.ammo_policy.SPARE),self.originals[self.command["owner"]]):base.set_stat(selected["item"],tag,count)
            if self.position==len(PLAN):self.restore();self.command={};self.publish("complete")
            else:self.stage="start";self.stage_started=time.monotonic()
    def restore(self):
        super().restore()
        for actor,_ in self.walls:
            if not dead(actor):actor.call_function("K2_DestroyActor")
        self.report["native_fixture_colliders_destroyed"]=all(dead(actor) for actor,_ in self.walls)
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":self.report["status"]="passed"
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_NETSHOOTER_IMPACT_"+self.report["status"].upper())


if any(value.startswith("-UEPNetShooterImpactNetworkResult=") for value in sys.argv):
    result,peer,run=base.arg("-UEPNetShooterImpactNetworkResult="),base.arg("-UEPJumpPeer="),base.arg("-UEPJumpRun=")
    validation=Server(result,run) if peer=="server" else Client(result,peer,run);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
