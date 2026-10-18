"""Actual deferred Actor Spawn/BeginPlay -> original BP -> routed VFX helper."""
import atexit
import copy
import struct
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod,EAttachLocation,ENCPoolMethod
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Activation
from . import grenade_vfx_mixin as policy
from .grenade_vfx_contract import PLAN,require,validate


def path(obj): return obj.get_path_name() if valid(obj) else None
def vector(obj): return [float(obj.x),float(obj.y),float(obj.z)]
def rotation(obj): return [float(obj.roll),float(obj.pitch),float(obj.yaw)]
def color(obj): return [float(obj.r),float(obj.g),float(obj.b),float(obj.a)]


def parameter(component):
    store=component.get_property("OverrideParameters")
    matches=[value for value in store.SortedParameterOffsets if str(value.Name) in ("Team_Color","User.Team_Color")]
    require(len(matches)==1,"one actual reflected native Team_Color parameter offset required")
    entry=matches[0];data=bytes(store.ParameterData);offset=int(entry.Offset)
    require(0<=offset and offset+16<=len(data),"native Niagara color offset outside reflected byte storage")
    return dict(parameter_name=str(entry.Name),parameter_offset=offset,parameter_data_bytes=len(data),parameter_store_color=list(struct.unpack_from("<4f",data,offset)))


class Validation(Ready):
    healths=Activation.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.events=[];self.target=None;self.installed=False;self.cleaned=False
        self.report=dict(schema_version=1,status="running",error=None,cases=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,
            physical_input_tested=False,actor_collision_fuse_explosion_damage_migrated=False,projectile_physics_tested=False,projectile_replication_tested=False,
            particle_rendering_tested=False,
            health_properties_written=False,team_properties_written=False,begin_play_replayed=False,native_deferred_spawn_finish=True,
            original_blueprint_begin_calls_helper=True,repeat_ordinary_helper_call_by_fixture=True,grenade_actors_destroyed_before_world_tick=True,observation_errors=[])
    def begin(self):
        bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world)
        self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","native VFX standalone fixture required")
        self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls)
        self.teams=ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem",self.world,ue.find_class("LyraTeamSubsystem"))
        owner=self
        for name,base in (("Python",policy.LyraGrenadeVFXPythonProfile),("BlueprintFallback",policy.LyraGrenadeVFXBlueprintFallbackProfile)):
            def around(handler):
                def invoke(actor):
                    handler(actor)
                    if actor==owner.target: owner.events.append(path(actor))
                invoke.override=policy.METHOD;return invoke
            ue.register_mixin_profile(self.cls,name,type("ObservedGrenadeVFX"+name,(),dict(SetupVFX=around(base.SetupVFX))))
        self.installed=True;self.health_before=self.healths();self.enter("sources")
    def sources(self):
        require(time.monotonic()-self.phase_started<30.,"actual native team1/other-team Pawn sources missing")
        pawns,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("Pawn"));found={};discovery=[]
        for pawn in pawns:
            health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if not valid(health) or health.call_function("GetHealth")<=0: continue
            part,team=self.teams.call_function("FindTeamFromActor",pawn)
            discovery.append(dict(pawn=path(pawn),part_of_team=bool(part),team_id=int(team)))
            if part: found["team1" if int(team)==1 else "other-team"]=pawn
        self.report["native_team_source_discovery"]=discovery
        if set(found)!={"team1","other-team"}: return
        self.team_sources=found;self.warmup()
    def warmup(self):
        # Native system/PSO readiness is asynchronous. Warm the same system on
        # a harmless ordinary Actor,not a Grenade with a live fuse. Never force
        # ready/active flags or bypass the authored pre-cull/activation settings.
        point=self.pawn.get_actor_location();forward=self.pawn.call_function("GetActorForwardVector")
        location=ue.FVector(point.x+forward.x*200.,point.y+forward.y*200.,point.z+50.)
        self.warm_actor=self.world.actor_spawn(ue.find_class("Actor"),location);self.actors.append(self.warm_actor)
        root=self.warm_actor.add_actor_root_component(ue.find_class("SceneComponent"),"UEPGrenadeVFXWarmup")
        require(self.warm_actor.call_function("K2_TeleportTo",location,ue.FRotator()),"native VFX warmup root transform refused")
        self.warm_component=ue.find_class("NiagaraFunctionLibrary").get_cdo().call_function("SpawnSystemAttached",
            SystemTemplate=ue.load_object(ue.find_class("NiagaraSystem"),policy.TRAIL),AttachToComponent=root,AttachPointName="None",Location=ue.FVector(),Rotation=ue.FRotator(),
            LocationType=EAttachLocation.KeepRelativeOffset,bAutoDestroy=False,bAutoActivate=True,PoolingMethod=getattr(ENCPoolMethod,"None"),bPreCullCheck=True)
        require(valid(self.warm_component),"native common VFX prewarm component missing")
        self.warm_active_ticks=0;self.enter("warm")
    def warm(self):
        require(time.monotonic()-self.phase_started<15.,"actual native VFX/PSO prewarm readiness timeout")
        self.warm_active_ticks=self.warm_active_ticks+1 if self.warm_component.call_function("IsActive") else 0
        if self.warm_active_ticks<3: return
        self.warm_actor.call_function("K2_DestroyActor")
        self.report.update(native_warmup_ready=True,warmup_actual_active_ticks=self.warm_active_ticks,
            warmup_actor_destroyed=not valid(self.warm_actor) or bool(self.warm_actor.call_function("IsActorBeingDestroyed")))
        self.health_before=self.healths();self.enter("spawn")
    def state(self,actor):
        component=actor.get_property("NS_Trail");require(valid(component),"native original/Python trail did not spawn")
        components=actor.call_function("K2_GetComponentsByClass",ue.find_class("NiagaraComponent"))
        matching=[value for value in components if path(value.call_function("GetAsset"))==policy.TRAIL]
        stats=policy.evidence(actor)
        return dict(component=path(component),asset=path(component.call_function("GetAsset")),parent=path(component.call_function("GetAttachParent")),
            relative_location=vector(component.get_property("RelativeLocation")),relative_rotation=rotation(component.get_property("RelativeRotation")),
            relative_scale=vector(component.get_property("RelativeScale3D")),auto_destroy=bool(component.get_property("bAutoDestroy")),
            auto_activate=bool(component.get_property("bAutoActivate")),active=bool(component.call_function("IsActive")),
            actor_team_color=color(actor.get_property("Team Color")),matching_components=len(matching),helper_calls=len(self.events),
            stats={key:value for key,value in stats.items() if isinstance(value,int)},last_team_id=(stats["last"] or {}).get("team_id"),**parameter(component))
    def spawn(self):
        name,profile=PLAN[self.index];instigator=None if name=="no-instigator" else self.team_sources[name]
        point=self.pawn.get_actor_location();forward=self.pawn.call_function("GetActorForwardVector")
        location=ue.FVector(point.x+forward.x*200.,point.y+forward.y*200.,point.z+50.)
        transform=ue.FTransform(location,self.pawn.get_actor_rotation(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        require(valid(actor),"actual native deferred Grenade Actor missing");self.actors.append(actor)
        actor.set_property("Instigator",instigator);ue.set_mixin_profile(actor,profile);self.target=actor;self.events=[]
        self.statics.call_function("FinishSpawningActor",actor,transform,scale)
        part,team=self.teams.call_function("FindTeamFromActor",instigator)
        row=dict(name=name,profile=profile,**{"class":path(actor.get_class())},instigator=path(instigator),team_id=int(team),mesh=path(actor.get_property("Mesh")),initial=self.state(actor))
        actor.call_function(policy.METHOD) # Ordinary business function,not a lifecycle callback replay.
        row["repeated"]=self.state(actor);actor.call_function("K2_DestroyActor");row["actor_destroyed"]=not valid(actor) or bool(actor.call_function("IsActorBeingDestroyed"))
        require(self.healths()==self.health_before,"VFX fixture changed actual Pawn Health")
        self.report["cases"].append(copy.deepcopy(row));self.target=None;self.index+=1
        ue.log("UEP_GRENADE_VFX_CASE_PASSED "+name+" "+profile)
        if self.index==len(PLAN): self.quiet_ticks=0;self.enter("quiet")
    def quiet(self):
        require(self.healths()==self.health_before,"VFX quiet interval changed actual Pawn Health")
        self.quiet_ticks+=1
        if self.quiet_ticks>=20: self.report["quiet_ticks"]=self.quiet_ticks;self.finish()
    def cleanup(self):
        if self.cleaned: return
        self.target=None
        for actor in self.actors:
            if valid(actor) and not actor.call_function("IsActorBeingDestroyed"): actor.call_function("K2_DestroyActor")
        if self.installed:
            for name,base in (("Python",policy.LyraGrenadeVFXPythonProfile),("BlueprintFallback",policy.LyraGrenadeVFXBlueprintFallbackProfile)): ue.register_mixin_profile(self.cls,name,base)
            binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==self.cls]
            self.report["profile_classes_restored"]=all(binding["profiles"][name]["python_class"] is base for name,base in (("Python",policy.LyraGrenadeVFXPythonProfile),("BlueprintFallback",policy.LyraGrenadeVFXBlueprintFallbackProfile)))
        self.report.update(remaining_test_actors=len([actor for actor in self.actors if valid(actor) and not actor.call_function("IsActorBeingDestroyed")]),
            all_pawn_health_unchanged=self.healths()==self.health_before if hasattr(self,"health_before") else False)
        self.cleaned=True
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<180.,"native Grenade VFX total timeout")
            if self.phase=="ready": self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.phase=="sources": self.sources()
                elif self.phase=="warm": self.warm()
                elif self.phase=="spawn": self.spawn()
                elif self.phase=="quiet": self.quiet()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_GRENADE_VFX_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";validate(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_VFX_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeVFXResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
