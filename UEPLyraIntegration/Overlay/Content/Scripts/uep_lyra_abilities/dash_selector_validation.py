"""Actual granted inactive Dash; a second BP invokes the retained helper."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_helpers_validation import Validation as Ready, instances, specs
from . import dash_selector_mixin as policy
from .dash_selector_contract import PLAN, require, validate

PROBE = "/Game/UEPValidation/BP_DashSelectorProbe.BP_DashSelectorProbe_C"


def path(value): return value.get_path_name() if valid(value) else None
def vector(value): return [float(value.x), float(value.y), float(value.z)]


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result); self.require_auto_active = False; self.caller = None; self.cleaned = False; self.case_index = 0
        self.report = {key: self.report[key] for key in ("schema_version", "status", "error", "cases", "full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested")}
        self.report.update(dash_selector_business_migrated=True, dash_activation_business_migrated=False, dash_rpc_movement_tested=False,
            fixture_activated_ability=False, fixture_granted_ability=False, gameplay_state_delivered_by_files=False)

    def begin(self):
        values = instances(self.asc, ue.load_class(policy.CLASS))
        require(len(values) == 1 and not values[0].get_property("bIsActive"), "one actual granted inactive primary Dash instance required")
        self.dash = values[0]; self.dash_original_profile = str(ue.get_mixin_profile(self.dash))
        self.configuration = {name: self.dash.get_property(name) for name in policy.FIELDS}
        self.cdo_configuration = {name: path(self.dash.get_class().get_cdo().get_property(name)) for name in policy.FIELDS}
        self.before_specs = specs(self.asc)
        self.caller_class = ue.load_class(PROBE); self.caller = self.caller_class.get_cdo(); self.caller_added = not self.caller_class.is_rooted()
        if self.caller_added: self.caller_class.add_to_root()
        self.report.update(actual_granted_primary_instance=True, actual_ability_class=path(self.dash.get_class()), ability_was_not_rooted=not self.dash.is_rooted(),
            original_montages={name: path(value) for name, value in self.configuration.items()}, native_role=int(self.pawn.call_function("GetLocalRole")),
            player_id=int(self.controller.PlayerState.PlayerId))
        require(all(self.report["original_montages"].values()) and len(set(self.report["original_montages"].values())) == 4, "four distinct original Dash montage controls required")
        self.enter("selector")

    def native_state(self):
        return dict(ability_active=bool(self.dash.get_property("bIsActive")), pawn=path(self.pawn),
            location=vector(self.pawn.get_actor_location()), velocity=vector(self.pawn.call_function("GetVelocity")),
            health=float(self.health.call_function("GetHealth")), current_montage=path(self.pawn.call_function("GetCurrentMontage")), specs=specs(self.asc))

    def run_pair(self):
        case = PLAN[self.case_index]; before = self.native_state(); rows = {}
        try:
            if case["null_field"]: self.dash.set_property(case["null_field"], None)
            for profile, key in (("BlueprintFallback", "blueprint"), ("Python", "python")):
                ue.set_mixin_profile(self.dash, profile); counts = copy.deepcopy(policy.evidence(self.dash))
                result = self.caller.call_function("Select", self.dash, ue.FVector(*case["facing"]), ue.FVector(*case["movement"]))
                require(isinstance(result, tuple) and len(result) == 2 and type(result[1]) is bool, "typed BP Dash named outputs not a montage/bool pair")
                after = policy.evidence(self.dash)
                rows[key] = dict(profile=profile, result=dict(DirectionalMontage=path(result[0]), BiasForwardMovement=result[1]),
                    counters={name: after[name]-counts[name] for name in ("python_calls", "fallback_calls")}, last=copy.deepcopy(after["last"]))
        finally:
            for name, value in self.configuration.items(): self.dash.set_property(name, value)
            ue.set_mixin_profile(self.dash, self.dash_original_profile)
        self.report["cases"].append(dict(input=copy.deepcopy(case), native_state_before=before, native_state_after=self.native_state(),
            configuration_restored=all(self.dash.get_property(name) == value for name, value in self.configuration.items()), **rows))
        self.case_index += 1
        if self.case_index == len(PLAN): self.quiet_before = copy.deepcopy(policy.evidence(self.dash)); self.quiet_ticks = 0; self.enter("quiet")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240, "Dash selector fixture timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "selector": self.run_pair()
            elif self.phase == "quiet":
                self.quiet_ticks += 1
                require(policy.evidence(self.dash) == self.quiet_before, "Dash helper dispatched late work")
                if self.quiet_ticks >= 20: self.report["quiet_after_helper_calls"] = True; self.complete()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def cleanup(self):
        if self.cleaned: return
        if hasattr(self, "dash") and valid(self.dash):
            for name, value in self.configuration.items(): self.dash.set_property(name, value)
            ue.set_mixin_profile(self.dash, self.dash_original_profile)
            self.report.update(original_profile_restored=str(ue.get_mixin_profile(self.dash)) == self.dash_original_profile,
                instance_configuration_restored=all(self.dash.get_property(name) == value for name, value in self.configuration.items()),
                cdo_configuration_unchanged={name: path(self.dash.get_class().get_cdo().get_property(name)) for name in policy.FIELDS} == self.cdo_configuration,
                native_specs_unchanged=specs(self.asc) == self.before_specs)
        if self.caller is not None:
            if self.caller_added: self.caller_class.remove_from_root()
            self.report["caller_roots"] = dict(created=int(self.caller_added), released=int(self.caller_added)); self.caller = None
        self.cleaned = True

    def complete(self): self.finish()

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_DASH_SELECTOR_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); marker = "UEP_DASH_SELECTOR_NETWORK_" if self.report.get("peer") == "server" else "UEP_DASH_SELECTOR_SHUTDOWN_"
        (ue.log if self.report["status"] == "passed" else ue.log_error)(marker+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPDashSelectorResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
