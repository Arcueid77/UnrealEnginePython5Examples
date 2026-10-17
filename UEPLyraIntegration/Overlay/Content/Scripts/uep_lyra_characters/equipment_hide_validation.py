"""Owned inherited-function/death producers after all previous regressions."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from .begin_play_validation import Validation as BeginValidation
from .equipment_hide_observation import Trial, Caller, SCENARIOS
from .equipment_hide_contract import validate
from .health_changed_observation import health
from .outline_validation import path
from .initial_inventory_contract import require
from uep_lyra_network_bots import isolate_bots


class Validation(BeginValidation):
    hide_trial_type = Trial
    marker = "UEP_CHARACTER_EQUIPMENT_HIDE"
    validate_report = staticmethod(validate)
    def __init__(self, result):
        super().__init__(result); self.hide_trial = self.hide_caller = None; self.hide_complete = False
        self.original_bot_states = None
        self.report.update(inherited_equipment_hide_migrated=True, ragdoll_physics_or_animation_migrated=False, equipment_hidden_fields_written_directly=False, equipment_hide_cases=[])
    def bot_states(self):
        bots, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraPlayerBotController"))
        return sorted([dict(controller=path(value), pawn=path(value.get_controlled_pawn()), health=health(value.get_controlled_pawn())) for value in bots], key=lambda value: value["controller"])
    def begin(self):
        if self.original_bot_states is None:
            self.original_bot_states = self.bot_states(); require(self.original_bot_states, "native comparison lacks original bot controls")
            self.report["original_bots_before"] = copy.deepcopy(self.original_bot_states)
        super().begin()
    def start_hide(self):
        if self.hide_caller is None: self.hide_caller = Caller()
        self.hide_trial = self.hide_trial_type(self.world, self.hide_caller, SCENARIOS[len(self.report["equipment_hide_cases"])]); self.enter("equipment-hide")
    def tick(self, seconds):
        if not self.finished and hasattr(self, "world"):
            try: isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            except Exception: self.finish(traceback.format_exc()); return False
        if not self.finished and self.phase == "equipment-hide":
            try:
                if self.hide_trial.step():
                    self.report["equipment_hide_cases"].append(copy.deepcopy(self.hide_trial.row))
                    ue.log(self.marker+"_HIDE_PASSED "+self.hide_trial.scenario[0]+"/"+self.hide_trial.scenario[3]); self.hide_trial = None
                    if len(self.report["equipment_hide_cases"]) == len(SCENARIOS): self.hide_complete = True; self.finish()
                    else: self.start_hide()
                return not self.finished
            except Exception:
                self.report["equipment_hide_failed_case"] = copy.deepcopy(getattr(self.hide_trial, "row", {})); self.finish(traceback.format_exc()); return False
        return super().tick(seconds)
    def finish(self, error=None):
        if self.finished: return
        try:
            if error is None and self.begin_complete and not self.hide_complete: self.start_hide(); return
            if self.hide_trial is not None: self.hide_trial.close()
            if self.hide_caller is not None: self.report["equipment_hide_caller_roots"] = self.hide_caller.close()
            if error is None and self.hide_complete:
                self.report.update(original_bots_after=self.bot_states(), native_ai_isolated_throughout_fixture=True)
                self.report["original_bot_identities_and_health_preserved"] = self.report["original_bots_after"] == self.original_bot_states
        except Exception: error = (error or "")+traceback.format_exc()
        super().finish(error)


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterEquipmentHideResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
