"""Actual BeginPlay schedules Actor-owned native timers; read handle/name parity."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .grenade_cleanup_validation import Validation as Cleanup,path
from . import grenade_begin_mixin as policy,grenade_vfx_mixin as vfx
from .grenade_begin_contract import validate,require


class Validation(Cleanup):
    def __init__(self,result):
        super().__init__(result);self.begin_events=[];self.handles=[];self.drain_complete=False
        self.report.update(begin_cases=[],begin_play_replayed=False,python_timer_entry="KismetSystemLibrary.K2_SetTimer",native_named_actor_timer_binding=True,native_detonate_callback_observed=False)
    def timer_state(self,actor):
        handle=actor.get_property("Timer");system=ue.find_class("KismetSystemLibrary").get_cdo();instigator=actor.get_property("Instigator")
        character=valid(instigator) and instigator.is_a(ue.find_class("Character"))
        values=vfx.evidence(actor)
        result=dict(fuse_handle_exists=bool(system.call_function("K2_TimerExistsHandle",self.world,handle)),fuse_handle_active=bool(system.call_function("K2_IsTimerActiveHandle",self.world,handle)),
            fuse_named_exists=bool(system.call_function("K2_TimerExists",actor,"Detonate")),cleanup_named_exists=bool(system.call_function("K2_TimerExists",actor,"PostLaunchCleanup")),
            fuse_handle_remaining=float(system.call_function("K2_GetTimerRemainingTimeHandle",self.world,handle)),fuse_named_remaining=float(system.call_function("K2_GetTimerRemainingTime",actor,"Detonate")),
            cleanup_named_remaining=float(system.call_function("K2_GetTimerRemainingTime",actor,"PostLaunchCleanup")),fuse_property=float(actor.get_property("TimeBeforeExplode")),
            vfx_helper_calls=values["python_calls"]+values["fallback_calls"],vfx_stats=copy.deepcopy(values),trail_valid=valid(actor.get_property("NS_Trail")),
            actor_team_color=[float(getattr(actor.get_property("Team Color"),key)) for key in ("r","g","b","a")])
        result.update(self.state(actor));return result
    def begin(self):
        super().begin();owner=self
        binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==self.cls]
        for name,record in binding["profiles"].items():
            base=record["python_class"]
            def around(handler,profile):
                def invoke(actor):
                    watched=actor==owner.target;row=None
                    if watched:
                        try: row=dict(profile=profile,before=owner.timer_state(actor))
                        except Exception: owner.report["observation_errors"].append(traceback.format_exc())
                    handler(actor)
                    if row is not None:
                        try: row.update(after=owner.timer_state(actor),stats=copy.deepcopy(policy.evidence(actor)));owner.begin_events.append(row)
                        except Exception: owner.report["observation_errors"].append(traceback.format_exc())
                return invoke
            methods={key:value for key,value in vars(base).items() if not key.startswith("__") and callable(value)}
            methods["ReceiveBeginPlay"]=around(base.ReceiveBeginPlay,name)
            ue.register_mixin_profile(self.cls,name,type("ObservedGrenadeBegin"+name,(),methods))
    def spawn(self):
        self.begin_events=[];super().spawn()
        require(len(self.begin_events)==1 and not self.report["observation_errors"],"one actual native BeginPlay witness required: "+str(self.report["observation_errors"]))
        self.handle=self.target.get_property("Timer");self.handles.append(self.handle)
        self.begin_row=dict(name=self.row["name"],profile=self.row["profile"],actor=self.row["actor"],instigator=self.row["instigator"],native_begin_count=1,event=copy.deepcopy(self.begin_events[0]))
    def timer(self):
        super().timer()
        if self.phase=="quiet":
            self.begin_row["cleanup_timer_gone_after_callback"]=not ue.find_class("KismetSystemLibrary").get_cdo().call_function("K2_TimerExists",self.target,"PostLaunchCleanup")
    def quiet(self):
        system=ue.find_class("KismetSystemLibrary").get_cdo();before=len(self.report["cases"])
        self.begin_row.update(fuse_handle_exists_before_destroy=bool(system.call_function("K2_TimerExistsHandle",self.world,self.handle)),
            fuse_remaining_before_destroy=float(system.call_function("K2_GetTimerRemainingTimeHandle",self.world,self.handle)))
        super().quiet()
        if len(self.report["cases"])>before:
            self.begin_row["fuse_handle_gone_after_destroy"]=not system.call_function("K2_TimerExistsHandle",self.world,self.handle)
            self.report["begin_cases"].append(copy.deepcopy(self.begin_row));self.write()
    def cleanup(self):
        super().cleanup()
        if hasattr(self,"world"):
            system=ue.find_class("KismetSystemLibrary").get_cdo()
            self.report["native_destroyed_actor_timers_naturally_expired"]=all(not system.call_function("K2_TimerExistsHandle",self.world,handle) for handle in self.handles)
    def tick(self,seconds):
        if self.phase!="timer-drain": return super().tick(seconds)
        if self.finished: return False
        try:
            require(time.monotonic()-self.drain_started<4.,"destroyed Actor native timers did not naturally expire")
            self.drain_max_frame=max(self.drain_max_frame,float(seconds))
            require(self.healths()==self.health_before,"native timer drain changed actual Pawn Health")
            system=ue.find_class("KismetSystemLibrary").get_cdo()
            if all(not system.call_function("K2_TimerExistsHandle",self.world,handle) for handle in self.handles):
                self.drain_complete=True
                self.report.update(timer_drain_elapsed=self.game_time()-self.drain_game_started,timer_drain_max_frame=self.drain_max_frame,timer_drain_expected_remaining=self.drain_expected_remaining)
                self.finish()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        if error is None and not self.drain_complete:
            system=ue.find_class("KismetSystemLibrary").get_cdo()
            self.drain_expected_remaining=max(0.,*(float(system.call_function("K2_GetTimerRemainingTimeHandle",self.world,handle)) for handle in self.handles))
            self.drain_started=time.monotonic();self.drain_game_started=self.game_time();self.drain_max_frame=0.;self.enter("timer-drain");return
        self.finished=True
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_GRENADE_BEGIN_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";self.validate_report()
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_BEGIN_SHUTDOWN_"+self.report["status"].upper())
    def validate_report(self): return validate(self.report)


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeBeginResult=")),None)
if result and "-UEPGrenadeHeadless" not in sys.argv:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
