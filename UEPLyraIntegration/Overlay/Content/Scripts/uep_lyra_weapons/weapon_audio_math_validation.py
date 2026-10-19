"""Call the retained public static API and real Blueprint VM caller per input."""
import atexit
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from . import weapon_audio_math_mixin as policy
from .weapon_audio_math_contract import SIDE_PLAN,WHIZ_PLAN,require,validate


def model(value):
    if hasattr(value,"x"):return [float(value.x),float(value.y),float(value.z)]
    if isinstance(value,tuple):return [model(v) for v in value]
    return value


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False
        self.report=dict(status="running",error=None,side_pairs=[],whiz_pairs=[],full_acceptance=False,network_acceptance=False,audible_playback_tested=False,
            cpp_compile_executed=False,static_functions_registered_as_mixins=False,physics_or_audio_state_written=False)
    def vector(self,value):return self.math.call_function("MakeVector",*value)
    def invoke(self,method,args,caller):
        ue.set_random_seed(104729);result=(self.caller if caller else self.library).call_function(("CallSides" if method=="GetSideReflectionAngles" else "CallWhiz") if caller else method,*args,self.world)
        following=int(self.math.call_function("RandomIntegerInRange",0,32767));return model(result),following
    def trial(self,method,index,args):
        values=[];counts=[];before=policy.evidence(self.router).copy();prefix="side" if method=="GetSideReflectionAngles" else "whiz"
        for profile in ("BlueprintFallback","Python"):
            ue.set_mixin_profile(self.router,profile);values.append([self.invoke(method,args,caller) for caller in (False,True)]);after=policy.evidence(self.router).copy()
            counts.append(after[prefix+("_fallback" if profile=="BlueprintFallback" else "_python")]-before[prefix+("_fallback" if profile=="BlueprintFallback" else "_python")]);before=after
        return dict(index=index,blueprint=values[0],python=values[1],direct_and_bp_callers_equal=values[0][0]==values[0][1] and values[1][0]==values[1][1],
            original_python_outputs_equal=values[0][0][0]==values[1][0][0],native_next_random_equal=len({value[1] for group in values for value in group})==1,
            fallback_dispatches=counts[0],python_dispatches=counts[1])
    def begin(self):
        self.player_health=float(self.health.call_function("GetHealth"));self.math=policy.math();self.library_cls=ue.load_class("/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C");self.library=self.library_cls.get_cdo()
        self.router_cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.router_cls);self.router=self.router_cls.get_cdo();self.original_profile=str(ue.get_mixin_profile(self.router))
        self.caller=ue.load_class("/Game/UEPValidation/BP_WeaponAudioMathCaller.BP_WeaponAudioMathCaller_C").get_cdo()
        signatures={method:ue.describe_function(self.library_cls,method) for method in policy.METHODS}
        require(all(value["flags"]&0x2000 for value in signatures.values()),"public static flags missing")
        for index,(origin,normal,distance,axis) in enumerate(SIDE_PLAN):self.report["side_pairs"].append(self.trial("GetSideReflectionAngles",index,[self.vector(origin),self.vector(normal),distance,self.vector(axis)]))
        for index,(listener,origin,minimum,impact) in enumerate(WHIZ_PLAN):self.report["whiz_pairs"].append(self.trial("Calculate Whiz By",index,[self.vector(listener),self.vector(origin),minimum,self.vector(impact)]))
        self.report["original_static_signatures_preserved"]=all(ue.describe_function(self.library_cls,method)==value for method,value in signatures.items())
        self.finish()
    def cleanup(self):
        if hasattr(self,"original_profile"):
            ue.set_mixin_profile(self.router,self.original_profile);self.report["router_profile_restored"]=str(ue.get_mixin_profile(self.router))==self.original_profile
            self.report["original_player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.player_health
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
        (ue.log_error if error else ue.log)("UEP_WEAPON_AUDIO_MATH_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_AUDIO_MATH_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPWeaponAudioMathResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
