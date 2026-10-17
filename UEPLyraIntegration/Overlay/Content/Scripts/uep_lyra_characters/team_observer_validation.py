"""Original typed BP listener entry -> real native initial observer broadcast."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from .team_observer_contract import CLASS, PLAN, require, validate
from .team_observer_observation import Context, proxies


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result); self.context = self.bare = None
        self.report.update(retained_character_class=CLASS, callback_replayed=False, team_properties_written=False, observer_delegate_broadcast_by_fixture=False,
            all_native_observers_cancelled=False, replicated_team_changes_tested=False, listener_factory_orchestration_migrated=False,
            hardware_output_tested=False, pixels_verified=False, whole_character_migrated=False, full_acceptance=False)

    def begin(self):
        before = set(proxies()); self.bare = self.world.actor_spawn(ue.load_class(CLASS), ue.FVector(200000., 200000., 2000.)); self.bare.call_function("SetReplicates", False)
        owned = [value for key, value in proxies().items() if key not in before]
        require(len(owned) == 1, "owned unassigned Actor did not run one original startup listener")
        self.context = Context(dict(owner=self.pawn, unassigned=self.bare), dict(owner=self.controller), before, owned)
        self.report.update(native_net_mode=self.context.net_mode, natural_startup_python_dispatch=self.context.startup)
        self.prepare()

    def prepare(self):
        name, target, calls, profile = PLAN[self.index]
        self.context.produce(target, profile, calls); self.enter("device")

    def observe(self):
        if not self.context.devices_done(): return
        name, target, calls, profile = PLAN[self.index]
        self.row = self.context.complete(); self.row.update(name=name, target=target, calls=calls); self.enter("gc")

    def after_collection(self):
        row = self.context.settle_collection(self.row)
        self.report["cases"].append(row); ue.log("UEP_CHARACTER_OBSERVER_CASE_PASSED "+row["name"]+"/"+row["profile"])
        self.index += 1
        if self.index == len(PLAN):
            self.report["cleanup"] = self.context.cleanup(self.bare); self.enter("cleanup-gc")
        else: self.prepare()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300, "native team observer standalone timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "device": self.observe()
            elif self.phase == "gc" and time.monotonic()-self.phase_started >= .15: self.after_collection()
            elif self.phase == "cleanup-gc" and time.monotonic()-self.phase_started >= .15:
                self.report["cleanup"] = self.context.finalize_collection(); self.finish()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if self.context is not None: self.report["cleanup"] = self.context.cleanup(self.bare)
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_OBSERVER_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_OBSERVER_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterObserverResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
