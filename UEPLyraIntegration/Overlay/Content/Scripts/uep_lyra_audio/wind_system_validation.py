"""Paired live wind actors share real physics while native schedulers stay independent."""
import atexit
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import wind_system_mixin as policy
from .wind_system_contract import PLAN,TICKS,exterior,require,validate


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[]
        self.report=dict(status="running",error=None,cases=[],full_acceptance=False,network_acceptance=False,audible_playback_tested=False,
            multigate_state_reimplemented_in_python=False,trace_results_injected=False,cpp_compile_executed=False)
    def spawn(self,profile):
        actor=self.world.actor_spawn(self.cls);self.actors.append(actor);actor.call_function("SetActorTickEnabled",False);ue.set_mixin_profile(actor,profile)
        require(valid(policy.audio(actor)),"original SCS wind AudioComponent missing");return actor
    def state(self,actor):
        audio=policy.audio(actor);params={str(p.ParamName):dict(kind=int(p.ParamType),scalar=float(p.FloatParam),integer=int(p.IntParam)) for p in audio.get_property("InstanceParameters")}
        loc=actor.get_property("PawnLoc")
        return dict(location=[float(loc.x),float(loc.y),float(loc.z)],hits=int(actor.get_property("Hits")),wind=float(actor.get_property("Wind")),speed=float(actor.get_property("Speed")),
            player_array_size=len(actor.get_property("Player")),parameters=params)
    def begin(self):
        self.health_before=float(self.health.call_function("GetHealth"));self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls)
        for index,(distance,size,pattern) in enumerate(PLAN):
            actors=[self.spawn(profile) for profile in ("BlueprintFallback","Python")]
            for actor in actors:
                actor.set_property("TraceDistance",distance);actor.set_property("Player",[None] if size else []);actor.set_property("Hits",2);actor.set_property("Wind",.777);actor.set_property("Speed",.123);policy.audio(actor).call_function("ResetParameters")
            row=dict(index=index,ticks=[])
            for tick in range(TICKS):
                if tick in (7,16):
                    for actor in actors:ue.set_mixin_profile(actor,"Python" if str(ue.get_mixin_profile(actor))=="BlueprintFallback" else "BlueprintFallback")
                states=[];stages=[];query_count=0
                for actor in actors:
                    actor.set_property("IsExterior",exterior(pattern,tick));stats=policy.evidence(actor);before=len(stats["stages"]);queries=stats["queries"]
                    actor.call_function("ReceiveTick",9999. if tick%2 else 0.);stages.append(stats["stages"][-1] if len(stats["stages"])>before else None);query_count+=stats["queries"]-queries;states.append(self.state(actor))
                row["ticks"].append(dict(index=tick,stages=stages,states=states,python_queries=query_count))
            self.report["cases"].append(row)
            for actor in actors:actor.call_function("K2_DestroyActor")
        self.natural=self.spawn("Python");self.natural.set_property("Player",[self.pawn]);self.before_natural=policy.evidence(self.natural)["tick_python"];self.natural.call_function("SetActorTickEnabled",True);self.natural_start=self.game_time();self.phase="natural"
    def cleanup(self):
        for actor in self.actors:
            if valid(actor):actor.call_function("K2_DestroyActor")
        self.report["owned_actors_destroyed"]=all(not valid(actor) for actor in self.actors)
        if hasattr(self,"health_before"):self.report["player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            if self.phase=="ready":self.ready()
            elif self.phase=="natural":
                delta=policy.evidence(self.natural)["tick_python"]-self.before_natural
                if delta>=5:self.report["natural_python_ticks"]=delta;self.finish()
                else:require(self.game_time()-self.natural_start<3.,"natural wind actor did not tick")
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WIND_SYSTEM_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WIND_SYSTEM_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPWindSystemResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
