"""Native SurfaceImpacts structs, Niagara stores and published Data Channel rows."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod,ENCPoolMethod
from unreal_engine.structs import NiagaraDataChannelSearchParameters
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .weapon_fire_fx_validation import dead,vec,parameter
from .weapon_decals_validation import Validation as NativeLifetime,array_kind
from . import weapon_impacts_mixin as policy
from .weapon_impacts_contract import PROFILES,BUCKET_CASES,BUCKET_SURFACES,ARRAY_CASES,require,validate

SYSTEMS=("/Game/Effects/Particles/Impacts/NS_ImpactConcrete.NS_ImpactConcrete",
         "/Game/Effects/Particles/Impacts/NS_ImactSparksCharacter.NS_ImactSparksCharacter",
         "/Game/Effects/Particles/Impacts/NS_ImpactGlass.NS_ImpactGlass")


def buckets(actor):
    return [dict(positions=[vec(v) for v in value.get_field(policy.POSITIONS)],normals=[vec(v) for v in value.get_field(policy.NORMALS)]) for value in actor.get_property("ImpactBuckets")]


def read_parameters(component):
    arrays=policy.lib("NiagaraDataInterfaceArrayFunctionLibrary");muzzle=native_outputs("NiagaraComponent","GetVariablePosition",component.call_function("GetVariablePosition","User.MuzzlePosition"))
    muzzle_kind="Position"
    if not muzzle["bIsValid"]:
        # SetVariablePosition deliberately falls back to vector for an asset
        # whose existing user variable is not Position (the Character system).
        muzzle=native_outputs("NiagaraComponent","GetVariableVec3",component.call_function("GetVariableVec3","User.MuzzlePosition"));muzzle_kind="Vector"
    names=[str(value.Name) for value in component.get_property("OverrideParameters").SortedParameterOffsets]
    count_name="NumberOfHits" if "NumberOfHits" in names else "User.NumberOfHits"
    return dict(position_array_kind=array_kind(component,"User.ImpactPositions"),
        positions=[vec(v) for v in arrays.call_function("GetNiagaraArrayPosition",component,"User.ImpactPositions")],
        normals=[vec(v) for v in arrays.call_function("GetNiagaraArrayVector",component,"User.ImpactNormals")],
        number_of_hits=parameter(component,count_name,"<i")[0],count_parameter_name=count_name,
        muzzle=vec(muzzle["ReturnValue"]),muzzle_valid=bool(muzzle["bIsValid"]),muzzle_storage_kind=muzzle_kind)


class Validation(NativeLifetime):
    def __init__(self,result):
        super().__init__(result);self.report.update(bucket_cases=[],fire_cases=[],channel_cases=[],data_channel_buffers_written_by_fixture=False)
        self.routes=[]
    def begin(self):
        bridge=policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world);self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","native impacts standalone required")
        self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.signature=ue.describe_function(self.cls,"Fire")
        self.report["function_locals_not_actor_properties"]=all(name not in self.cls.get_cdo().properties() for name in ("CurrentIndex","CurrentSurface"))
        self.signatures={name:ue.describe_function(self.cls,name) for name in policy.METHODS}
        self.health_before=self.healths();self.original_view=self.controller.call_function("GetViewTarget")
        self.camera=self.world.actor_spawn(ue.find_class("CameraActor"));self.actors.append(self.camera)
        require(self.camera.call_function("K2_TeleportTo",ue.FVector(-250.,0.,100.),ue.FRotator(0.,-20.,0.)),"native impact camera placement failed")
        self.controller.call_function("SetViewTargetWithBlend",self.camera,0.,0,0.,False)
        self.systems=[ue.load_object(ue.find_class("NiagaraSystem"),path) for path in SYSTEMS]
        self.warm_components=[self.native_spawn(asset,ue.FVector(),False,True) for asset in self.systems]
        require(all(valid(value) for value in self.warm_components),"native impact prewarm spawn failed")
        binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls]
        self.original_classes={name:row["python_class"] for name,row in binding["profiles"].items()};owner=self
        for name,base in self.original_classes.items():
            methods={key:value for key,value in vars(base).items() if not key.startswith("__") and callable(value)}
            for method in ("SpawnFromArrays","SpawnFromDataChannels"):
                def observe(handler,entry):
                    def invoke(actor,SurfaceType):
                        if actor==owner.target:owner.routes.append(dict(method=entry,surface=int(SurfaceType)))
                        return handler(actor,SurfaceType)
                    invoke.override=entry;return invoke
                methods[method]=observe(getattr(base,method),method)
            def around(handler):
                def invoke(actor):
                    if actor==owner.target:owner.cleanup_events.append(dict(time=owner.game_time()))
                    return handler(actor)
                invoke.override=policy.AFTER;return invoke
            methods["AfterDelay"]=around(base.AfterDelay)
            ue.register_mixin_profile(self.cls,name,type("ObservedImpactNativeBoundaries"+name,(),methods))
        self.warm_ticks=0;self.enter("warm")
    def native_spawn(self,asset,point,auto_destroy=True,auto_activate=True):
        return self.remember(policy.lib("NiagaraFunctionLibrary").call_function("SpawnSystemAtLocation",WorldContextObject=self.world,SystemTemplate=asset,
            Location=point,Rotation=ue.FRotator(),Scale=ue.FVector(1.,1.,1.),bAutoDestroy=auto_destroy,bAutoActivate=auto_activate,
            PoolingMethod=getattr(ENCPoolMethod,"None"),bPreCullCheck=True))
    def spawn(self,profile):
        transform=ue.FTransform(ue.FVector(),ue.FRotator(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        for name,asset in zip(policy.TEMPLATES,(self.systems[0],self.systems[1],self.systems[0],self.systems[2])):actor.set_property(name,asset)
        actor.set_property("ImpactBuckets",[]);actor.set_property("Impact Systems",[]);actor.set_property("MuzzlePosition",ue.FVector(25.,-10.,5.));actor.set_property("Distance Threshold",10.)
        self.statics.call_function("FinishSpawningActor",actor,transform,scale);ue.set_mixin_profile(actor,profile);self.actors.append(actor);return actor
    def bucket_trials(self):
        for profile in PROFILES:
            actor=self.spawn(profile);actor.set_property("ImpactBuckets",[policy.bucket([ue.FVector(999.,0.,0.)],[ue.FVector(0.,1.,0.)]) for _ in range(5)])
            for index,name in enumerate(BUCKET_CASES):
                points=[ue.FVector(100.+i*10.,index,25.) for i in range(len(BUCKET_SURFACES[index]))];normals=[ue.FVector(-1.,0.,0.) for _ in points]
                actor.set_property("ImpactPositions",points);actor.set_property("ImpactNormals",normals);actor.set_property("ImpactSurfaceTypes",list(BUCKET_SURFACES[index]))
                actor.call_function("AddImpactsToBuckets")
                values=list(actor.get_property("ImpactBuckets"))
                self.report["bucket_cases"].append(dict(name=name,profile=profile,buckets=buckets(actor),points=[vec(v) for v in points],normals=[vec(v) for v in normals],
                    native_struct_type=values[0].get_struct().get_path_name(),
                    input_arrays_unchanged=[vec(v) for v in actor.get_property("ImpactPositions")]==[vec(v) for v in points] and
                        [vec(v) for v in actor.get_property("ImpactNormals")]==[vec(v) for v in normals] and list(actor.get_property("ImpactSurfaceTypes"))==list(BUCKET_SURFACES[index])))
            actor.call_function("K2_DestroyActor")
    def array_trials(self):
        xs=(0.,2.,12.,25.,50.,60.,80.,100.,20.,30.,40.)
        for profile in PROFILES:
            actor=self.spawn(profile);self.target=actor
            for index,name in enumerate(ARRAY_CASES):
                surface={"character":1,"concrete":2,"glass":3}.get(name,0)
                if name=="inactive-far":
                    inactive=self.native_spawn(self.systems[0],ue.FVector(),False,False)
                    require(valid(inactive) and not inactive.call_function("IsActive"),"native inactive impact cache fixture invalid")
                    actor.set_property("Impact Systems",[inactive])
                elif name=="null-cache":actor.set_property("Impact Systems",[None])
                elif name=="changed-template-far":actor.set_property("Default",self.systems[2])
                elif name=="invalid-template":actor.set_property("Default",None)
                systems=list(actor.get_property("Impact Systems"));old=systems[surface] if surface<len(systems) else None
                before_data=read_parameters(old) if name=="invalid-template" else None;before_location=vec(old.call_function("K2_GetComponentLocation")) if valid(old) else None
                points=[ue.FVector(xs[index],0.,50.),ue.FVector(xs[index]+1.,1.,50.)];normals=[ue.FVector(-1.,0.,0.)]*2
                groups=[policy.bucket() for _ in range(surface+1)];groups[surface]=policy.bucket(points,normals);actor.set_property("ImpactBuckets",groups)
                actor.call_function("SpawnFromArrays",surface);component=self.remember(actor.get_property("Impact Systems")[surface])
                require(valid(component),"native impact array cache absent")
                rotation=component.call_function("K2_GetComponentRotation")
                self.report["cases"].append(dict(name=name,profile=profile,component_valid=True,same_cached=component==old,
                    points=[vec(v) for v in points],normals=[vec(v) for v in normals],muzzle=vec(actor.get_property("MuzzlePosition")),
                    before_parameters=before_data,before_location=before_location,native_parameters=read_parameters(component),
                    world_location=vec(component.call_function("K2_GetComponentLocation")),active=bool(component.call_function("IsActive")),
                    asset_is_current_template=component.call_function("GetAsset")==actor.get_property(policy.TEMPLATES[surface]),
                    unattached=not valid(component.call_function("GetAttachParent")),world_rotation=[float(rotation.roll),float(rotation.pitch),float(rotation.yaw)],world_scale=vec(component.call_function("K2_GetComponentScale"))))
            actor.call_function("K2_DestroyActor")
        for value in self.components:self.remove(value)
    def capture_fire(self,profile,channels):
        self.target=self.spawn(profile);self.routes=[];self.target.set_property("Use Data Channels",channels)
        surfaces=[0,1,2,3,2,3];offset=200.+100.*PROFILES.index(profile)+50.*int(channels)
        points=[ue.FVector(offset+i*2.,0.,50.) for i in range(6)];normals=[ue.FVector(-1.,0.,0.)]*6
        for field,value in (("ImpactPositions",points),("ImpactNormals",normals),("ImpactSurfaceTypes",surfaces)):self.target.set_property(field,value)
        before=dict(policy.evidence(self.target));self.target.call_function("Fire");after=policy.evidence(self.target)
        systems=list(self.target.get_property("Impact Systems"))
        for component in systems:self.remember(component)
        self.report["fire_cases"].append(dict(profile=profile,channels=channels,routes=list(self.routes),buckets=buckets(self.target),
            selected_fire_dispatch=after["python_calls" if profile=="Python" else "fallback_calls"]-before["python_calls" if profile=="Python" else "fallback_calls"]==1,
            input_arrays_cleared=all(not self.target.get_property(field) for field in ("ImpactPositions","ImpactNormals","ImpactSurfaceTypes")),
            cached_surfaces=[i for i,value in enumerate(systems) if valid(value)]))
        return [dict(position=vec(point),normal=vec(normals[i]),muzzle=vec(self.target.get_property("MuzzlePosition")),surface=surfaces[i],valid=True) for i,point in enumerate(points) if surfaces[i] in (2,3)]
    def visual_trials(self):
        self.bucket_trials();self.array_trials()
        for profile in PROFILES:
            self.capture_fire(profile,False);self.target.call_function("K2_DestroyActor")
        self.channel_index=0;self.start_channel()
    def start_channel(self):
        self.profile=PROFILES[self.channel_index];self.expected_channel=self.capture_fire(self.profile,True)
        self.channel_started=time.monotonic();self.enter("channel-read")
    def channel_read(self):
        channel=ue.load_object(ue.find_class("NiagaraDataChannelAsset"),policy.CHANNEL)
        first=self.expected_channel[0]["position"];search=NiagaraDataChannelSearchParameters(OwningComponent=self.target.get_property("DefaultSceneRoot"),Location=ue.FVector(*first),bOverrideLocation=True)
        wanted={tuple(row["position"]) for row in self.expected_channel}
        for previous in (False,True):
            reader=policy.lib("NiagaraDataChannelLibrary").call_function("ReadFromNiagaraDataChannel",self.world,channel,search,previous)
            if not valid(reader):continue
            count=int(reader.call_function("Num"));found=[]
            for index in range(count):
                def read(method,name):return native_outputs("NiagaraDataChannelReader",method,reader.call_function(method,name,index))
                point=read("ReadPosition","ImpactPosition")
                if not point["IsValid"] or tuple(vec(point["ReturnValue"])) not in wanted:continue
                normal=read("ReadVector","ImpactNormal");muzzle=read("ReadPosition","MuzzlePosition");surface=read("ReadEnum","ImpactSurface")
                found.append(dict(position=vec(point["ReturnValue"]),normal=vec(normal["ReturnValue"]),muzzle=vec(muzzle["ReturnValue"]),surface=int(surface["ReturnValue"]),
                    valid=all(value["IsValid"] for value in (point,normal,muzzle,surface))))
            if len(found)!=4:continue
            self.report["channel_cases"].append(dict(profile=self.profile,native_reader=True,reader_count=count,previous_frame=previous,published=found,expected=self.expected_channel))
            self.target.call_function("K2_DestroyActor");self.channel_index+=1
            if self.channel_index<len(PROFILES):self.start_channel()
            else:
                for component in self.components:self.remove(component)
                self.index=0;self.start_timer()
            return
        require(time.monotonic()-self.channel_started<3.,"native Data Channel published rows not observed")
    def fire_and_remove(self):
        self.target.call_function("Fire")
        for component in self.target.get_property("Impact Systems"):self.remove(self.remember(component))
    def timer(self):
        elapsed=self.game_time()-self.timer_start
        if not self.retriggered and elapsed>=1.:
            require(not dead(self.target),"impacts died before native delay");self.fire_and_remove();self.retriggered=True
        if 3.1<=elapsed<3.4:require(not dead(self.target),"impact native deadline did not reset");self.survived=True
        if not dead(self.target):require(elapsed<5.5,"native impact empty cleanup failed");return
        require(len(self.cleanup_events)==1,"native impact cleanup count differs")
        self.timer_row=dict(profile=self.profile,native_retrigger_observed=self.retriggered,survived_original_deadline=self.survived,
            destroyed_after_retrigger=True,destroy_elapsed=elapsed,native_callback_elapsed=self.cleanup_events[0]["time"]-self.timer_start)
        self.target=self.spawn(self.profile);self.cleanup_events=[];self.target.call_function("Fire")
        self.hold_component=self.remember(self.target.add_actor_component(ue.find_class("NiagaraComponent"),"UEPValidInactiveImpactHold"))
        require(not self.hold_component.call_function("IsActive"),"native impact hold active")
        self.target.set_property("Impact Systems",[None,self.hold_component,None]);self.hold_start=self.game_time();self.hold_removed=False;self.enter("hold")
    def hold(self):
        if not self.hold_removed and self.cleanup_events:self.timer_row["native_has_valid_systems"]=bool(self.target.get_property("Has Valid Systems"))
        super().hold()
    def cleanup(self):
        super().cleanup()
        if hasattr(self,"signatures"):self.report["original_signature_restored"]=all(ue.describe_function(self.cls,name)==value for name,value in self.signatures.items())
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,"native impact total timeout")
            if self.phase=="ready":self.ready()
            elif self.phase=="warm":
                require(time.monotonic()-self.phase_started<20.,"native impact readiness timeout")
                self.warm_ticks=self.warm_ticks+1 if all(valid(c) and c.call_function("IsActive") for c in self.warm_components) else 0
                if self.warm_ticks>=3:self.report["native_warmup_ready"]=True;self.visual_trials()
            elif self.phase=="channel-read":self.channel_read()
            elif self.phase=="timer":self.timer()
            elif self.phase=="hold":self.hold()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_IMPACTS_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_IMPACTS_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPWeaponImpactsResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
