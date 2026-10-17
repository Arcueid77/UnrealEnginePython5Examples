"""Original/Python receiver comparison from real GAS changes and native AI sense."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from .health_changed_observation import Context, OwnedAI
from .health_changed_contract import CLASS, PLAN, require, validate


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result)
        self.context = self.owned = None
        self.report.update(callback_replayed=False, health_properties_written=False, sense_report_called_by_fixture=False,
            component_delegate_broadcast_by_fixture=False, gameplay_state_delivered_by_files=False, pixels_verified=False,
            whole_character_migrated=False, full_acceptance=False, retained_character_class=CLASS)

    def begin(self):
        self.owned = OwnedAI(self.world); self.enter("fixture")

    def attach_fixture(self):
        if not self.owned.ready(): return
        require(self.owned.pawn.get_class().get_path_name() == CLASS, "native RestartPlayer did not retain actual Character type")
        self.context = Context(dict(A=self.pawn, AI=self.owned.pawn), dict(A=self.controller), self.owned)
        self.report.update(native_net_mode=self.context.net_mode, natural_startup_python_dispatch=self.context.startup)
        self.prepare()

    def prepare(self):
        self.name, self.profile = PLAN[self.index]
        self.context.prepare(self.name); require(self.context.prepared(self.name), "native health preparation differs")
        self.context.arm(self.name, self.profile); self.context.produce(); self.enter("observe")

    def observe(self):
        if not self.context.seen() or time.monotonic()-self.phase_started < .35: return
        self.report["cases"].append(copy.deepcopy(self.context.row()))
        self.context.restore(); require(self.context.restored(), "native GAS restoration failed")
        ue.log("UEP_CHARACTER_HEALTH_CASE_PASSED "+self.name+"/"+self.profile)
        self.index += 1
        if self.index == len(PLAN): self.finish()
        else: self.enter("settle")

    def cleanup(self):
        errors = []
        if self.context is not None:
            try:
                self.context.restore(); self.report["cleanup"] = self.context.cleanup()
            except Exception: errors.append(traceback.format_exc())
        if self.owned is not None:
            try: self.report["owned_fixture_cleanup"] = self.owned.close()
            except Exception: errors.append(traceback.format_exc())
        if errors: raise RuntimeError("native health cleanup failed: "+"\n".join(errors))

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300, "native health standalone timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "fixture": self.attach_fixture()
            elif self.phase == "observe": self.observe()
            elif self.phase == "settle" and time.monotonic()-self.phase_started >= .2: self.prepare()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_HEALTH_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_HEALTH_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterHealthResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
