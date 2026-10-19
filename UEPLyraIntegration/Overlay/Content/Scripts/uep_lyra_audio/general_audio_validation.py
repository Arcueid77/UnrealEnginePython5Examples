"""Retained static GeneralAudio API to native live music component receiver."""
import atexit
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import general_audio_mixin as policy
from .general_audio_contract import PLAN,require,validate


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.positives=[]
        self.report=dict(status="running",error=None,pairs=[],full_acceptance=False,network_acceptance=False,audible_playback_tested=False,
            static_functions_registered_as_mixins=False,native_error_branches_exercised=False,cpp_compile_executed=False)
    def begin(self):
        self.health_before=float(self.health.call_function("GetHealth"));self.library_cls=ue.load_class("/Game/Audio/Blueprints/GeneralAudioFunctions.GeneralAudioFunctions_C");self.library=self.library_cls.get_cdo();self.signature=ue.describe_function(self.library_cls,"FireStinger")
        self.router_cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.router_cls);self.router=self.router_cls.get_cdo();self.router_original=str(ue.get_mixin_profile(self.router))
        self.caller=ue.load_class("/Game/UEPValidation/BP_GeneralAudioCaller.BP_GeneralAudioCaller_C").get_cdo();self.music_cls=ue.load_class(policy.MUSIC)
        self.manager=self.statics.call_function("GetGameState",self.world).get_component_by_type(self.music_cls);require(valid(self.manager),"actual native music manager missing")
        self.fields={name:self.manager.get_property(name) for name in ("Music System","Alpha_Intensity","Alpha_Mvmt","bIsMenu")};self.observe_receiver()
        self.actor=self.world.actor_spawn(ue.find_class("Actor"));root=self.actor.add_actor_root_component(ue.find_class("SceneComponent"),"UEPGeneralAudioRoot");self.audio=self.actor.add_actor_component(ue.find_class("AudioComponent"),"UEPGeneralAudioSound",root)
        self.audio.set_property("bAutoDestroy",False);self.audio.call_function("SetSound",ue.load_object(ue.find_class("SoundBase"),"/Game/Audio/MetaSounds/mx_System.mx_System"))
        for index,args in enumerate(PLAN):self.report["pairs"].append(self.trial(index,args))
        self.report["static_signature_flags_preserved"]=ue.describe_function(self.library_cls,"FireStinger")==self.signature and bool(self.signature["flags"]&0x2000);self.finish()
    def observe_receiver(self):
        row,=[r for r in ue.get_registered_mixins() if r["target_class"]==self.music_cls];self.original_classes={name:value["python_class"] for name,value in row["profiles"].items()};owner=self
        for profile,source in self.original_classes.items():
            methods={name:fn for name,fn in vars(source).items() if not name.startswith("__") and callable(fn)}
            def observed(handler):
                def invoke(component,Positive):
                    if component==owner.manager:owner.positives.append(bool(Positive))
                    return handler(component,Positive)
                invoke.override="Fire Stinger";return invoke
            methods["Stinger"]=observed(source.Stinger);ue.register_mixin_profile(self.music_cls,profile,type("ObservedGeneralAudioReceiver"+profile,(),methods))
    def invoke(self,args,caller):
        positive,mode,alpha=args;self.audio.call_function("Stop");self.audio.call_function("ResetParameters")
        if mode=="playing":self.audio.call_function("Play",0.)
        self.manager.set_property("Music System",None if mode=="invalid" else self.audio);self.manager.set_property("Alpha_Intensity",alpha);self.positives=[]
        (self.caller if caller else self.library).call_function("CallStinger" if caller else "FireStinger",positive,self.world)
        return dict(intensity=float(self.manager.get_property("Alpha_Intensity")),positive_arguments=list(self.positives),
            playing=bool(self.audio.call_function("IsPlaying")),parameters={str(p.ParamName):dict(kind=int(p.ParamType),scalar=float(p.FloatParam),boolean=bool(p.BoolParam)) for p in self.audio.get_property("InstanceParameters")})
    def trial(self,index,args):
        values=[];counts=[];manager_calls=0
        for profile in ("BlueprintFallback","Python"):
            ue.set_mixin_profile(self.router,profile);before=dict(policy.evidence(self.router));values.extend(self.invoke(args,caller) for caller in (False,True));after=policy.evidence(self.router)
            key="fallback_calls" if profile=="BlueprintFallback" else "python_calls";counts.append(after[key]-before[key])
            if profile=="Python":manager_calls=after["manager_calls"]-before["manager_calls"]
        return dict(index=index,observations=values,fallback_dispatches=counts[0],python_dispatches=counts[1],python_manager_calls=manager_calls)
    def cleanup(self):
        if hasattr(self,"router_original"):
            ue.set_mixin_profile(self.router,self.router_original);self.report["router_profile_restored"]=str(ue.get_mixin_profile(self.router))==self.router_original
        if hasattr(self,"fields"):
            for name,value in self.fields.items():self.manager.set_property(name,value)
            self.report["manager_fields_restored"]=all(self.manager.get_property(name)==value for name,value in self.fields.items())
        if hasattr(self,"original_classes"):
            for name,source in self.original_classes.items():ue.register_mixin_profile(self.music_cls,name,source)
            row,=[r for r in ue.get_registered_mixins() if r["target_class"]==self.music_cls];self.report["music_profile_family_restored"]=all(row["profiles"][name]["python_class"] is source for name,source in self.original_classes.items())
        if hasattr(self,"audio") and valid(self.audio):self.audio.call_function("Stop")
        if hasattr(self,"actor") and valid(self.actor):self.actor.call_function("K2_DestroyActor")
        self.report["owned_actor_destroyed"]=not hasattr(self,"actor") or not valid(self.actor)
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
        (ue.log_error if error else ue.log)("UEP_GENERAL_AUDIO_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GENERAL_AUDIO_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPGeneralAudioResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
