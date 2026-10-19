"""Native music parameters and base event state through actual inherited component."""
import atexit
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import music_manager_mixin as policy
from .music_manager_contract import PLANS,require,validate


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[]
        self.report=dict(status="running",error=None,pairs={name:[] for name in PLANS},full_acceptance=False,network_acceptance=False,
            audible_playback_tested=False,begin_play_listeners_migrated=False,child_delay_business_migrated=False,cpp_compile_executed=False)
    def own(self,cls):
        actor=self.world.actor_spawn(ue.find_class(cls));actor.call_function("SetReplicates",False);self.actors.append(actor);return actor
    def begin(self):
        self.health_before=float(self.health.call_function("GetHealth"));cls=ue.load_class(policy.CLASS)
        state=self.statics.call_function("GetGameState",self.world);self.manager=state.get_component_by_type(cls);require(valid(self.manager),"actual derived music manager missing")
        self.report["actual_manager_class"]=self.manager.get_class().get_path_name();self.report["natural_python_tick_before_probe"]=policy.evidence(self.manager)["ReceiveTick_python"]
        ue.register_declared_mixin(cls);self.original_profile=str(ue.get_mixin_profile(self.manager));self.fields={name:self.manager.get_property(name) for name in ("Music System","Alpha_Intensity","Alpha_Mvmt","bIsMenu")}
        self.signatures={name:ue.describe_function(cls,name) for name in (*policy.METHODS,"ReceiveBeginPlay")}
        self.caller=ue.load_class("/Game/UEPValidation/BP_MusicManagerCaller.BP_MusicManagerCaller_C").get_cdo();self.foreign=self.own("Pawn");self.actor=self.own("Actor")
        root=self.actor.add_actor_root_component(ue.find_class("SceneComponent"),"UEPMusicControlRoot");self.audio=self.actor.add_actor_component(ue.find_class("AudioComponent"),"UEPMusicControlAudio",root)
        self.audio.set_property("bAutoDestroy",False);self.audio.call_function("SetSound",ue.load_object(ue.find_class("SoundBase"),"/Game/Audio/MetaSounds/mx_System.mx_System"))
        self.world_delta=float(self.statics.call_function("GetWorldDeltaSeconds",self.world));self.report["native_world_delta_seconds"]=self.world_delta
        for method,plan in PLANS.items():
            for index,args in enumerate(plan):self.report["pairs"][method].append(self.trial(method,index,args))
        self.report["original_signatures_preserved"]=all(ue.describe_function(cls,name)==sig for name,sig in self.signatures.items());self.finish()
    def setup(self,method,args):
        self.audio.call_function("Stop");self.audio.call_function("ResetParameters")
        self.manager.set_property("Alpha_Intensity",.4321);self.manager.set_property("Alpha_Mvmt",.123);self.manager.set_property("bIsMenu",False)
        mode="invalid";values=[]
        players={"local":self.pawn,"foreign":self.foreign,"actor":self.actor,"null":None}
        if method=="SetIsMenu":mode,value,menu=args;self.manager.set_property("bIsMenu",menu);values=[value]
        elif method=="Receive Player Death":who,alpha=args;self.manager.set_property("Alpha_Intensity",alpha);values=[players[who]]
        elif method=="Receive Weapon Fire":who,strength,alpha=args;self.manager.set_property("Alpha_Intensity",alpha);values=[players[who],strength]
        elif method=="Fire Stinger":mode,positive,alpha=args;self.manager.set_property("Alpha_Intensity",alpha);values=[positive]
        else:mode,menu,alpha,delta=args;self.manager.set_property("Alpha_Intensity",alpha);self.manager.set_property("bIsMenu",menu);values=[delta]
        if mode=="playing":self.audio.call_function("Play",0.)
        self.manager.set_property("Music System",None if mode=="invalid" else self.audio)
        return values
    def snapshot(self):
        sound=self.manager.get_property("Music System")
        parameters={str(p.ParamName):dict(kind=int(p.ParamType),integer=int(p.IntParam),scalar=float(p.FloatParam),boolean=bool(p.BoolParam)) for p in self.audio.get_property("InstanceParameters")}
        return dict(intensity=float(self.manager.get_property("Alpha_Intensity")),movement=float(self.manager.get_property("Alpha_Mvmt")),menu=bool(self.manager.get_property("bIsMenu")),
            sound_valid=valid(sound),playing=bool(sound.call_function("IsPlaying")) if valid(sound) else False,parameters=parameters)
    def trial(self,method,index,args):
        values=[];counts=[]
        for profile in ("BlueprintFallback","Python"):
            ue.set_mixin_profile(self.manager,profile);before=dict(policy.evidence(self.manager));callers=(False,) if method=="ReceiveTick" else (False,True)
            for caller in callers:
                inputs=self.setup(method,args)
                (self.caller if caller else self.manager).call_function("Call"+str(policy.METHODS.index(method)) if caller else method,*([self.manager]+inputs if caller else inputs))
                values.append(self.snapshot())
            key=method+("_fallback" if profile=="BlueprintFallback" else "_python");counts.append(policy.evidence(self.manager)[key]-before[key])
        return dict(index=index,observations=values,fallback_dispatches=counts[0],python_dispatches=counts[1])
    def cleanup(self):
        if hasattr(self,"fields"):
            for name,value in self.fields.items():self.manager.set_property(name,value)
            ue.set_mixin_profile(self.manager,self.original_profile);self.report["profile_restored"]=str(ue.get_mixin_profile(self.manager))==self.original_profile
            self.report["manager_fields_restored"]=all(self.manager.get_property(name)==value for name,value in self.fields.items())
        if hasattr(self,"audio") and valid(self.audio):self.audio.call_function("Stop")
        for actor in self.actors:
            if valid(actor):actor.call_function("K2_DestroyActor")
        self.report["owned_actors_destroyed"]=all(not valid(actor) for actor in self.actors)
        if hasattr(self,"health_before"):self.report["player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:self.ready();self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_MUSIC_CONTROLS_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_MUSIC_CONTROLS_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPMusicControlsResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
