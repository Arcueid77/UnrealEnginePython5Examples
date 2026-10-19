"""Observe the retained EarlyReflections graph against real collision and taps."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import weapon_audio_dispatch_mixin as dispatch

LIBRARY="/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C"
ORDER=("Direct.Primary","Direct.Second.C","Side.Second.L","Side.Second.R","Direct.Second.L","Direct.Second.R","Side.First.L","Side.First.R")
INDICES=(0,1,4,5,2,3,6,7)
PLAN=(("local-none","local",None,(0.,800.,300.)),("local-solid","local",0,(0.,800.,300.)),
    ("foreign-near","foreign",4,(0.,800.,300.)),("foreign-far","foreign",0,(0.,6000.,0.)),
    ("local-far","local",4,(0.,6000.,0.)),("flesh","local",1,(0.,800.,300.)),
    ("null-target","null",0,(0.,800.,300.)),("below-limit","foreign",0,(0.,3999.75,0.)),
    ("at-limit","foreign",0,(0.,4000.,0.)),("above-limit","foreign",0,(0.,4000.25,0.)))


def xyz(value):return [float(value.x),float(value.y),float(value.z)]
def tap_model(info):return {field:int(getattr(info,field)) if field in ("TapId","TapLineMode","OutputChannel") else float(getattr(info,field)) for field in info.fields()}


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.materials=[];self.current_events=None
        self.report=dict(status="running",error=None,original_cases=[],full_acceptance=False,network_acceptance=False,audible_playback_tested=False,
            preset_asset_saved=False,cpp_compile_executed=False,trace_results_injected=False,tap_callbacks_replayed=False)
    def own(self):
        actor=self.world.actor_spawn(ue.find_class("Actor"));actor.call_function("SetReplicates",False);self.actors.append(actor);return actor
    def begin(self):
        self.health_before=float(self.health.call_function("GetHealth"));self.camera=self.controller.get_property("PlayerCameraManager")
        self.center=self.camera.call_function("GetCameraLocation");self.library=ue.load_class(LIBRARY).get_cdo();self.foreign=self.own();self.foreign.add_actor_root_component(ue.find_class("SceneComponent"),"UEPEarlyForeign")
        self.foreign.call_function("K2_SetActorLocation",NewLocation=ue.FVector(self.center.x+500.,self.center.y,self.center.z),bSweep=False,bTeleport=True)
        self.walls=[]
        for index,(offset,extent) in enumerate((((1600.,0.,1000.),(10.,2500.,1000.)),((-1600.,0.,1000.),(10.,2500.,1000.)),((0.,1600.,1000.),(2500.,10.,1000.)),((0.,-1600.,1000.),(2500.,10.,1000.)))):
            actor=self.own();box=actor.add_actor_root_component(ue.find_class("BoxComponent"),"UEPEarlyWall"+str(index));box.call_function("SetBoxExtent",ue.FVector(*extent),False)
            box.call_function("SetCollisionEnabled",1);box.call_function("SetCollisionResponseToAllChannels",2)
            actor.call_function("K2_SetActorLocation",NewLocation=ue.FVector(*[a+b for a,b in zip(xyz(self.center),offset)]),bSweep=False,bTeleport=True);self.walls.append(actor)
        self.preset=dispatch.tap_preset();ids,=self.preset.call_function("GetTapIds");self.initial_ids=[int(i) for i in ids];self.owned_taps=[]
        self.before_fixture_taps={str(i):tap_model(self.preset.call_function("GetTap",i)[0]) for i in self.initial_ids};self.ids=list(self.initial_ids)
        while len(self.ids)<8:
            tap,=self.preset.call_function("AddTap");self.owned_taps.append(int(tap));self.ids.append(int(tap))
        self.report.update(initial_preset_tap_ids=self.initial_ids,owned_fixture_tap_ids=self.owned_taps)
        self.original_infos={i:self.preset.call_function("GetTap",i)[0] for i in self.ids};self.original_taps=self.tap_state()
        self.observe_taps();self.material_map={None:None}
        for surface in (0,1,4):
            material=ue.new_object(ue.find_class("PhysicalMaterial"));material.set_property("SurfaceType",surface);material.add_to_root();self.materials.append(material);self.material_map[surface]=material
        self.phase="fixture";self.fixture_started=time.monotonic()
    def tap_state(self):return {str(i):tap_model(self.preset.call_function("GetTap",i)[0]) for i in self.ids}
    def reset_taps(self):
        for i,info in self.original_infos.items():self.preset.call_function("SetTap",i,info)
    def observe_taps(self):
        cls=ue.load_class(dispatch.CLASS);ue.register_declared_mixin(cls);self.dispatch_cls=cls;self.dispatch_router=cls.get_cdo();self.dispatch_original=str(ue.get_mixin_profile(self.dispatch_router))
        row,=[r for r in ue.get_registered_mixins() if r["target_class"]==cls];self.dispatch_sources={name:value["python_class"] for name,value in row["profiles"].items()};owner=self
        for profile,source in self.dispatch_sources.items():
            methods={name:fn for name,fn in vars(source).items() if not name.startswith("__") and callable(fn)}
            def observe(handler):
                def tap(router,DebugSuffix,Cam,HitLocation,TapId,TraceDistance,TravelDistance,DidHit,ListenerLocation,WorldContext):
                    if owner.current_events is not None:owner.current_events.append(dict(suffix=str(DebugSuffix),camera=Cam.get_path_name() if valid(Cam) else None,hit=xyz(HitLocation),tap_id=int(TapId),trace_distance=float(TraceDistance),travel=float(TravelDistance),did_hit=bool(DidHit),listener=xyz(ListenerLocation),world=WorldContext.get_path_name() if valid(WorldContext) else None))
                    return handler(router,DebugSuffix,Cam,HitLocation,TapId,TraceDistance,TravelDistance,DidHit,ListenerLocation,WorldContext)
                tap.override=dispatch.METHODS["Calculate Tap Properties"];tap.uep_named_outputs=True;return tap
            methods["Tap"]=observe(source.Tap);ue.register_mixin_profile(cls,profile,type("ObservedEarlyTap"+profile,(),methods))
    def cue(self,material,location,normal):
        return ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("MakeGameplayCueParameters",NormalizedMagnitude=0.,RawMagnitude=0.,EffectContext=GameplayEffectContextHandle(),
            MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),AggregatedTargetTags=GameplayTagContainer(),Location=location,Normal=normal,
            Instigator=None,EffectCauser=None,SourceObject=None,PhysicalMaterial=material,GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
    def preflight(self):
        center=xyz(self.center);start=ue.FVector(center[0]+1300.,center[1],center[2]+1000.);end=ue.FVector(center[0]+1900.,center[1],center[2]+1000.)
        raw=ue.find_class("KismetSystemLibrary").get_cdo().call_function("LineTraceSingle",WorldContextObject=self.world,Start=start,End=end,TraceChannel=0,bTraceComplex=False,
            ActorsToIgnore=[self.pawn],DrawDebugType=0,bIgnoreSelf=True,TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=2.)
        hit=native_outputs("KismetSystemLibrary","LineTraceSingle",raw);broken=native_outputs("GameplayStatics","BreakHitResult",self.statics.call_function("BreakHitResult",hit["OutHit"]))
        self.report["owned_wall_preflight"]=dict(hit=bool(hit["ReturnValue"]),owned_actor=broken["HitActor"]==self.walls[0],location=xyz(broken["Location"]))
        expected_owned=not self.report.get("open_geometry",False)
        if (broken["HitActor"]==self.walls[0])!=expected_owned or (expected_owned and not hit["ReturnValue"]):raise RuntimeError("owned collision mode did not match actual native simple trace")
    def run(self):
        self.preflight();listener=self.camera.call_function("GetCameraLocation");math=ue.find_class("KismetMathLibrary").get_cdo()
        for name,label,surface,offset in PLAN:
            target=self.pawn if label=="local" else self.foreign if label=="foreign" else None;location=ue.FVector(*[a+b for a,b in zip(xyz(listener),offset)])
            params=self.cue(self.material_map[surface],location,ue.FVector(0.,-1.,0.));self.reset_taps();self.current_events=[]
            self.library.call_function("EarlyReflections",target,params,self.world);events=self.current_events;self.current_events=None
            distance=float(math.call_function("Conv_DoubleToFloat",math.call_function("VSize",math.call_function("Subtract_VectorVector",location,listener))))
            self.report["original_cases"].append(dict(name=name,target=label,surface=surface,distance=distance,events=events,taps=self.tap_state()))
        self.finish()
    def cleanup(self):
        self.current_events=None
        if hasattr(self,"original_infos"):
            self.reset_taps()
        if hasattr(self,"owned_taps"):
            for tap in self.owned_taps:self.preset.call_function("RemoveTap",tap)
            ids,=self.preset.call_function("GetTapIds");after={str(i):tap_model(self.preset.call_function("GetTap",i)[0]) for i in ids}
            self.report["preset_state_restored"]=list(ids)==self.initial_ids and after==self.before_fixture_taps
        if hasattr(self,"dispatch_sources"):
            ue.set_mixin_profile(self.dispatch_router,self.dispatch_original)
            for name,source in self.dispatch_sources.items():ue.register_mixin_profile(self.dispatch_cls,name,source)
            row,=[r for r in ue.get_registered_mixins() if r["target_class"]==self.dispatch_cls]
            self.report["current_dispatch_profiles_restored"]=all(row["profiles"][name]["python_class"] is source for name,source in self.dispatch_sources.items()) and str(ue.get_mixin_profile(self.dispatch_router))==self.dispatch_original
        for actor in self.actors:
            if valid(actor):actor.call_function("K2_DestroyActor")
        for material in self.materials:
            if valid(material):material.remove_from_root()
        self.report["owned_actors_destroyed"]=all(not valid(actor) for actor in self.actors)
        if hasattr(self,"health_before"):self.report["player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            if self.phase=="ready":self.ready()
            elif self.phase=="fixture" and time.monotonic()-self.fixture_started>.2:self.run()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_AUDIO_EARLY_PROBE_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:
                if len(self.report["original_cases"])!=len(PLAN):raise RuntimeError("original reflection matrix incomplete")
                for row in self.report["original_cases"]:
                    eligible=row["target"]!="null" and row["surface"]!=1 and (row["distance"]<4000. or row["target"]=="local")
                    expected=8 if eligible else 0
                    if len(row["events"])!=expected:raise RuntimeError("original reflection eligibility differs: "+row["name"])
                    if eligible and (tuple(e["suffix"] for e in row["events"])!=ORDER or tuple(e["tap_id"] for e in row["events"])!=tuple(self.ids[i] for i in INDICES)):raise RuntimeError("original eight-Tap ordering differs")
                if not all(self.report.get(key) for key in ("preset_state_restored","current_dispatch_profiles_restored","owned_actors_destroyed","player_health_unchanged")):raise RuntimeError("original reflection fixture state not restored")
                self.report["status"]="passed"
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_AUDIO_EARLY_SHUTDOWN_"+self.report["status"].upper())


class Differential(Validation):
    def __init__(self,result):
        super().__init__(result);self.report.update(early_pairs=[],math_regression=[],static_functions_registered_as_mixins=False,
            open_geometry="-UEPWeaponAudioEarlyOpenGeometry" in sys.argv)
    def begin(self):
        from . import weapon_audio_early_mixin as policy
        super().begin();self.policy=policy
        if self.report["open_geometry"]:
            for wall in self.walls:wall.get_property("RootComponent").call_function("SetCollisionEnabled",0)
        cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(cls);self.router=cls.get_cdo();self.router_original=str(ue.get_mixin_profile(self.router))
        self.caller=ue.load_class("/Game/UEPValidation/BP_WeaponAudioEarlyCaller.BP_WeaponAudioEarlyCaller_C").get_cdo()
        self.library_cls=self.library.get_class();self.signatures={name:ue.describe_function(self.library_cls,name) for name in ("EarlyReflections","WhizBy","SendWeaponFire","SetWeaponSoundParams","DebugPrintTap","Calculate Tap Properties","GetSideReflectionAngles","Calculate Whiz By")}
        self.report["tap_ids"]=list(self.ids)
    def invoke(self,target,params,caller):
        self.reset_taps();self.current_events=[]
        try:
            (self.caller if caller else self.library).call_function("Call"+self.policy.METHOD if caller else "EarlyReflections",target,params,self.world)
            return dict(events=list(self.current_events),taps=self.tap_state())
        finally:self.current_events=None
    def run(self):
        from .weapon_audio_early_contract import PLAN as MATRIX
        self.preflight();math=ue.find_class("KismetMathLibrary").get_cdo()
        for index,(name,label,surface,offset,normal) in enumerate(MATRIX):
            listener=self.camera.call_function("GetCameraLocation");target=self.pawn if label=="local" else self.foreign if label=="foreign" else None
            location=ue.FVector(*[a+b for a,b in zip(xyz(listener),offset)]);params=self.cue(self.material_map[surface],location,ue.FVector(*normal))
            payload=native_outputs("AbilitySystemBlueprintLibrary","BreakGameplayCueParameters",ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("BreakGameplayCueParameters",params))
            distance=float(math.call_function("Conv_DoubleToFloat",math.call_function("VSize",math.call_function("Subtract_VectorVector",payload["Location"],listener))))
            values=[];counts=[];python_delta={}
            for profile in ("BlueprintFallback","Python"):
                ue.set_mixin_profile(self.router,profile);before=dict(self.policy.evidence(self.router));values.extend(self.invoke(target,params,caller) for caller in (False,True));after=self.policy.evidence(self.router)
                counts.append(after["fallback_calls" if profile=="BlueprintFallback" else "python_calls"]-before["fallback_calls" if profile=="BlueprintFallback" else "python_calls"])
                if profile=="Python":python_delta={key:after[key]-before[key] for key in ("eligible","queries","taps")}
            self.report["early_pairs"].append(dict(index=index,name=name,distance=distance,listener=xyz(listener),observations=values,fallback_dispatches=counts[0],python_dispatches=counts[1],
                python_eligible=python_delta["eligible"],python_queries=python_delta["queries"],python_taps=python_delta["taps"]))
        self.regressions();self.report["original_static_signatures_preserved"]=all(ue.describe_function(self.library_cls,name)==value for name,value in self.signatures.items());self.finish()
    def regressions(self):
        from .weapon_audio_whiz_validation import Differential as WhizValidation
        from . import weapon_audio_whiz_mixin as whiz
        WhizValidation.regressions(self)
        cls=ue.load_class(whiz.CLASS);ue.register_declared_mixin(cls);router=cls.get_cdo();original=str(ue.get_mixin_profile(router));caller=ue.load_class("/Game/UEPValidation/BP_WeaponAudioWhizCaller.BP_WeaponAudioWhizCaller_C").get_cdo()
        params=self.cue(self.material_map[0],self.camera.call_function("GetCameraLocation"),ue.FVector(0.,0.,1.));counts=[];before_spawns=whiz.evidence(router)["native_spawn_requests"]
        try:
            for profile in ("BlueprintFallback","Python"):
                ue.set_mixin_profile(router,profile);key="fallback_calls" if profile=="BlueprintFallback" else "python_calls";before=whiz.evidence(router)[key]
                for target,method in ((self.library,"WhizBy"),(caller,"Call"+whiz.METHOD)):target.call_function(method,self.foreign,params,self.world)
                counts.append(whiz.evidence(router)[key]-before)
        finally:ue.set_mixin_profile(router,original)
        self.report["whiz_regression_passed"]=counts==[2,2] and whiz.evidence(router)["native_spawn_requests"]-before_spawns==2 and str(ue.get_mixin_profile(router))==original
    def cleanup(self):
        if hasattr(self,"router_original"):
            ue.set_mixin_profile(self.router,self.router_original);self.report["router_profile_restored"]=str(ue.get_mixin_profile(self.router))==self.router_original
        super().cleanup()
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_AUDIO_EARLY_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:
                from .weapon_audio_early_contract import validate
                self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_AUDIO_EARLY_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPWeaponAudioEarlyResult=")),None)
if result:
    validation=(Validation if "-UEPWeaponAudioEarlyOriginalProbe" in sys.argv else Differential)(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
