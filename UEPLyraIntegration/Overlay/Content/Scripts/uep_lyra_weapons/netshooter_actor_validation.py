"""Actual native ray/component state, physics Hit, overlap callbacks and Delay."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod,ETraceTypeQuery,EDrawDebugTrace,ELyraTeamComparison,EComponentMobility
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.melee_trace_mixin import native_outputs,break_hit
from .weapon_fire_fx_validation import dead,vec
from . import netshooter_actor_mixin as policy
from .netshooter_actor_contract import PROFILES,COUNTS,require,validate

MESH="/ShooterCore/Blueprint/SM_XFacingCylinderUnit1.SM_XFacingCylinderUnit1"
MATERIAL="/ShooterCore/Effects/Material/M_Launcher_Inst4.M_Launcher_Inst4"


def near(left,right):return len(left)==len(right) and all(abs(a-b)<.01 for a,b in zip(left,right))
def rotation(value):return [float(value.roll),float(value.pitch),float(value.yaw)]


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.watches={};self.originals={};self.naturals=[];self.bot_poses=[]
        self.report=dict(status="running",error=None,ray_pairs=[],natural_cases=[],overlap_cases=[],controlled_hit_method_entries=True)
        for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested","health_properties_written",
                    "natural_hit_callback_replayed","overlap_callback_replayed","life_callback_replayed","rpc_function_overridden"):self.report[key]=False
    def rays(self,actor):
        return [value for value in actor.call_function("K2_GetComponentsByClass",ue.find_class("StaticMeshComponent")) if value!=actor.get_property("Sphere") and valid(value)]
    def watch(self,actor,profile,natural=False):
        value=dict(actor=actor,profile=profile,natural=natural,hit_times=[],spawn_events=[],overlaps=0,moving=[],rpc_bodies=0);self.watches[actor.get_path_name()]=value;return value
    def row_for(self,actor):return self.watches.get(actor.get_path_name())
    def begin(self):
        self.report["native_mode"]=str(policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world).call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","NetShooter Actor standalone required")
        self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.rpc_signature=ue.describe_function(self.cls,"SpawnComponents");self.player_health=float(self.health.call_function("GetHealth"))
        binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls];self.originals={key:value["python_class"] for key,value in binding["profiles"].items()};owner=self
        for profile,base in self.originals.items():
            def around_hit(handler):
                def invoke(actor,HitLocation,HitNormal):
                    row=owner.row_for(actor)
                    if row is not None:
                        row["hit_times"].append(owner.game_time());row["hit_frame_delta"]=float(owner.statics.call_function("GetWorldDeltaSeconds",owner.world))
                    return handler(actor,HitLocation,HitNormal)
                invoke.override=policy.HIT;return invoke
            def around_spawn(handler):
                def invoke(actor,HitResult):
                    before=owner.rays(actor);result=handler(actor,HitResult);row=owner.row_for(actor)
                    if row is not None:
                        parts=break_hit(HitResult);new=[value for value in owner.rays(actor) if value not in before];require(len(new)==1,"native RPC body did not add one strand")
                        component=new[0];distance=float(policy.lib("KismetMathLibrary").call_function("Vector_Distance",parts["TraceStart"],parts["ImpactPoint"]))
                        expected=policy.lib("KismetMathLibrary").call_function("FindLookAtRotation",parts["TraceStart"],parts["TraceEnd"])
                        pose=dict(location=vec(component.call_function("K2_GetComponentLocation")),rotation=rotation(component.call_function("K2_GetComponentRotation")),scale=vec(component.call_function("K2_GetComponentScale")))
                        template=component.get_property("StaticMesh").get_path_name()==MESH and component.call_function("GetMaterial",0).get_path_name()==MATERIAL and str(component.call_function("GetCollisionProfileName"))=="OverlapOnlyPawn"
                        row["spawn_events"].append(dict(pose=pose,native_geometry_matches=near(pose["location"],vec(actor.get_actor_location())) and near(pose["rotation"],rotation(expected)) and near(pose["scale"],[distance,3.,3.]),
                            native_template_matches=template,sphere_hidden=bool(actor.get_property("Sphere").get_property("bHiddenInGame"))));row["rpc_bodies"]+=1
                    return result
                invoke.override=policy.BODY;return invoke
            def around_overlap(handler):
                def invoke(actor,OverlappedComponent,OtherActor,OtherComp,OtherBodyIndex,bFromSweep,SweepResult):
                    row=owner.row_for(actor)
                    if row is not None:row["overlaps"]+=1
                    return handler(actor,OverlappedComponent,OtherActor,OtherComp,OtherBodyIndex,bFromSweep,SweepResult)
                return invoke
            ue.register_mixin_profile(self.cls,profile,type("ObservedNetActor"+profile,(),dict(HitBody=around_hit(base.HitBody),SpawnBody=around_spawn(base.SpawnBody),OverlapRays=around_overlap(base.OverlapRays),LifeEnded=base.LifeEnded)))
        self.center=ue.FVector(50000.,50000.,10000.);self.wall_actors=[]
        for axis in range(3):
            for sign in (-1.,1.):
                actor=self.world.actor_spawn(ue.find_class("Actor"));self.actors.append(actor);self.wall_actors.append(actor)
                box=actor.add_actor_root_component(ue.find_class("BoxComponent"),"UEPNetWall");extent=[550.,550.,550.];extent[axis]=10.
                box.call_function("SetMobility",EComponentMobility.Movable);box.call_function("SetBoxExtent",ue.FVector(*extent),False);box.call_function("SetCollisionObjectType",0);box.call_function("SetCollisionResponseToAllChannels",2);box.call_function("SetCollisionEnabled",1)
                point=vec(self.center);point[axis]+=sign*500.
                actor.call_function("K2_SetActorLocation",NewLocation=ue.FVector(*point),bSweep=False,bTeleport=True)
                require(near(vec(actor.get_actor_location()),point),"native net room wall placement failed")
        self.enter("room-ready")
    def spawn(self,profile,natural=False,number=12,y_offset=0.):
        point=ue.FVector(self.center.x-300.,self.center.y+y_offset,self.center.z) if natural else self.center
        transform=ue.FTransform(point,ue.FRotator(),ue.FVector(.1,.1,.1));scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        actor.set_property("Instigator",self.pawn);actor.set_property("NumberOfWeb",number)
        self.statics.call_function("FinishSpawningActor",actor,transform,scale);ue.set_mixin_profile(actor,profile);self.actors.append(actor)
        if not natural:actor.get_property("ProjectileMovement").call_function("Deactivate")
        return actor
    def room_hit(self):
        end=ue.FVector(self.center.x+1000.,self.center.y,self.center.z)
        output=native_outputs("KismetSystemLibrary","LineTraceSingle",policy.lib("KismetSystemLibrary").call_function("LineTraceSingle",WorldContextObject=self.world,Start=self.center,End=end,
            TraceChannel=ETraceTypeQuery.TraceTypeQuery2,bTraceComplex=True,ActorsToIgnore=[],DrawDebugType=getattr(EDrawDebugTrace,"None"),bIgnoreSelf=False,
            TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=0.))
        require(output["ReturnValue"],"native Camera-channel room trace missed");return output["OutHit"]
    def controlled(self):
        result=self.room_hit();parts=break_hit(result)
        warm=self.spawn("BlueprintFallback")
        ue.log("UEP_NETSHOOTER_BASELINE_TEMPLATE_BEGIN "+warm.get_path_name())
        warm.call_function("SpawnComponents",result)
        ue.log("UEP_NETSHOOTER_BASELINE_TEMPLATE_END "+warm.get_path_name())
        warm.call_function("K2_DestroyActor")
        for number in COUNTS:
            values=[]
            for profile in PROFILES:
                actor=self.spawn(profile,False,number);row=self.watch(actor,profile);ue.set_random_seed(7357+number)
                actor.call_function("ReceiveHit",actor.get_property("Sphere"),parts["HitActor"],parts["HitComponent"],True,parts["ImpactPoint"],parts["ImpactNormal"],ue.FVector(),result)
                before=len(row["spawn_events"]);actor.call_function("ReceiveHit",actor.get_property("Sphere"),parts["HitActor"],parts["HitComponent"],True,parts["ImpactPoint"],parts["ImpactNormal"],ue.FVector(),result)
                following=int(policy.lib("KismetMathLibrary").call_function("RandomIntegerInRange",0,32767))
                values.append(dict(native_hit_body_count=len(row["hit_times"]),duplicate_hit_do_once_blocked=len(row["spawn_events"])==before,
                    native_rpc_flags_preserved=ue.describe_function(self.cls,"SpawnComponents")==self.rpc_signature,ray_components=len(self.rays(actor)),spawn_events=copy.deepcopy(row["spawn_events"]),start=vec(actor.get_property("Start")),next_random=following))
                actor.call_function("K2_DestroyActor")
            self.report["ray_pairs"].append(dict(number=number,blueprint=values[0],python=values[1],same_components=values[0]["spawn_events"]==values[1]["spawn_events"],same_start=values[0]["start"]==values[1]["start"],same_next_native_random=values[0]["next_random"]==values[1]["next_random"]))
        self.stable_ticks=0;self.enter("natural-stabilize")
    def start_naturals(self):
        for index,profile in enumerate(PROFILES):
            actor=self.spawn(profile,True,y_offset=(-120.,120.)[index]);row=self.watch(actor,profile,True);row["started"]=self.game_time()
            movement=actor.get_property("ProjectileMovement");row["initial_speed"]=float(movement.get_property("InitialSpeed"));row["gravity_scale"]=float(movement.get_property("ProjectileGravityScale"));self.naturals.append(row)
        self.overlap_index=0;self.enter("natural-hit")
    def prepare_overlap(self):
        teams=policy.lib("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem",self.world,ue.find_class("LyraTeamSubsystem"))
        bots,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("LyraPlayerBotController"))
        target=None
        for controller in bots:
            pawn=controller.get_controlled_pawn();asc=ability_system(pawn) if valid(pawn) else None;health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent")) if valid(pawn) else None
            if valid(asc) and valid(health) and health.call_function("GetHealth")>0 and not health.call_function("IsDeadOrDying") and teams.call_function("CompareTeams",self.pawn,pawn)[0]==ELyraTeamComparison.DifferentTeams:
                if not asc.call_function("GetGameplayTagCount",ue.find_struct("GameplayTag")(TagName="Gameplay.DamageImmunity")):target=pawn;break
        require(target is not None,"initialized native enemy target missing for strand overlap")
        self.victim=target;self.victim_health=target.get_component_by_type(ue.find_class("LyraHealthComponent"))
        if not any(row[0]==target for row in self.bot_poses):self.bot_poses.append((target,target.get_actor_location(),target.get_actor_rotation()))
        require(target.call_function("K2_TeleportTo",ue.FVector(self.center.x,self.center.y+900.,self.center.z),ue.FRotator()),"native overlap target separation failed")
        self.overlap_actor=self.spawn(PROFILES[self.overlap_index]);self.overlap_row=self.watch(self.overlap_actor,PROFILES[self.overlap_index])
        self.overlap_actor.call_function("SpawnComponents",self.room_hit());ray=self.rays(self.overlap_actor)[0]
        bounds=native_outputs("KismetSystemLibrary","GetComponentBounds",policy.lib("KismetSystemLibrary").call_function("GetComponentBounds",ray))
        self.health_before=float(self.victim_health.call_function("GetHealth"));require(target.call_function("K2_TeleportTo",bounds["Origin"],ue.FRotator()),"native overlap target placement failed")
        target.get_property("CharacterMovement").call_function("StopMovementImmediately");self.enter("overlap")
    def overlap_tick(self):
        if self.overlap_row["overlaps"]<1:
            require(time.monotonic()-self.phase_started<5.,"native strand overlap callback missing");return
        after=float(self.victim_health.call_function("GetHealth"));row=self.overlap_row
        self.report["overlap_cases"].append(dict(profile=row["profile"],native_overlap_callbacks=row["overlaps"],native_source_matches_instigator=self.overlap_actor.call_function("GetInstigator")==self.pawn,
            native_rpc_body_count=row["rpc_bodies"],native_template_matches=row["spawn_events"][0]["native_template_matches"],health_before=self.health_before,health_after=after,native_health_damage_observed=after<self.health_before))
        self.overlap_actor.call_function("K2_DestroyActor");self.overlap_index+=1
        if self.overlap_index==2:self.enter("life-wait")
        else:self.enter("overlap-prepare")
    def sample_naturals(self):
        for row in self.naturals:
            actor=row["actor"]
            if not dead(actor):
                movement=actor.get_property("ProjectileMovement")
                if movement.call_function("IsActive"):row["moving"].append(vec(actor.get_actor_location()))
                row["ray_count"]=len(self.rays(actor))
            elif "ended" not in row:row["ended"]=self.game_time()
    def life_wait(self):
        if not all("ended" in row for row in self.naturals):
            require(time.monotonic()-self.phase_started<17.,"native original net life Delay did not destroy Actors");return
        for row in self.naturals:
            self.report["natural_cases"].append(dict(profile=row["profile"],native_hit_body_count=len(row["hit_times"]),native_moving_samples=len({tuple(value) for value in row["moving"]}),initial_speed=row["initial_speed"],gravity_scale=row["gravity_scale"],
                ray_components_before_end=row.get("ray_count",0),destroyed_by_native_life_delay=True,life_elapsed=row["ended"]-row["hit_times"][0],hit_frame_delta=row["hit_frame_delta"]))
        self.finish()
    def cleanup(self):
        for actor in self.actors:
            if not dead(actor):actor.call_function("K2_DestroyActor")
        for actor,point,rotation_ in self.bot_poses:
            if not dead(actor):actor.call_function("K2_TeleportTo",point,rotation_)
        for name,base in self.originals.items():ue.register_mixin_profile(self.cls,name,base)
        rows=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls]
        self.report["production_profiles_restored"]=len(rows)==1 and all(rows[0]["profiles"][name]["python_class"] is base for name,base in self.originals.items())
        self.report["all_test_actors_destroyed"]=all(dead(actor) for actor in self.actors);self.report["original_player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.player_health
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<200.,"native NetShooter Actor timeout")
            if self.phase=="ready":self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                self.sample_naturals()
                if self.phase=="room-ready":self.controlled()
                elif self.phase=="natural-stabilize":
                    delta=float(self.statics.call_function("GetWorldDeltaSeconds",self.world));self.stable_ticks=self.stable_ticks+1 if delta<.04 else 0
                    if self.stable_ticks>=3:self.start_naturals()
                elif self.phase=="natural-hit":
                    if all(row["hit_times"] for row in self.naturals):self.enter("overlap-prepare")
                elif self.phase=="overlap-prepare":self.prepare_overlap()
                elif self.phase=="overlap":self.overlap_tick()
                elif self.phase=="life-wait":self.life_wait()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_NETSHOOTER_ACTOR_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_NETSHOOTER_ACTOR_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPNetShooterActorResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
