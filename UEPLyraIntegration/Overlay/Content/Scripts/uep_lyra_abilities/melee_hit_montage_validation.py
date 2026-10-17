"""Actual granted Melee; a second BP calls with native Actor references."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_helpers_validation import Validation as Ready, instances, specs
from . import melee_hit_montage_mixin as policy
from .melee_hit_montage_contract import PLAN, require, validate

PROBE = "/Game/UEPValidation/BP_MeleeHitMontageProbe.BP_MeleeHitMontageProbe_C"
def path(value): return value.get_path_name() if valid(value) else None
def vector(value): return [float(value.x), float(value.y), float(value.z)]


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result); self.require_auto_active = False; self.cleaned = False; self.case_index = 0; self.control = None; self.caller = None
        self.report = dict(schema_version=1, status="running", error=None, cases=[], full_acceptance=False, network_acceptance=False,
            packaged_runtime=False, physical_input_tested=False, fixture_activated_ability=False, fixture_granted_ability=False,
            gameplay_state_delivered_by_files=False, whole_melee_activation_trace_damage_migrated=False)
    def begin(self):
        values = instances(self.asc, ue.load_class(policy.CLASS))
        require(len(values) == 1 and not values[0].get_property("bIsActive"), "one actually granted inactive native Melee instance required")
        self.melee = values[0]; self.profile = str(ue.get_mixin_profile(self.melee)); self.original_specs = specs(self.asc)
        self.caller_class = ue.load_class(PROBE); self.caller = self.caller_class.get_cdo(); self.caller_added = not self.caller_class.is_rooted()
        if self.caller_added: self.caller_class.add_to_root()
        self.control = self.world.actor_spawn(ue.find_class("Actor")); require(valid(self.control), "test-owned native basis Actor missing")
        self.report.update(actual_granted_primary_instance=True, actual_ability_class=path(self.melee.get_class()),
            native_role=int(self.pawn.call_function("GetLocalRole")), control_actor_fixture=True)
        self.enter("helper")
    def state(self):
        return dict(active=bool(self.melee.get_property("bIsActive")), pawn=path(self.pawn), location=vector(self.pawn.get_actor_location()),
            velocity=vector(self.pawn.call_function("GetVelocity")), health=float(self.health.call_function("GetHealth")),
            montage=path(self.pawn.call_function("GetCurrentMontage")), specs=specs(self.asc))
    def pair(self):
        case = PLAN[self.case_index]; actor = self.control if case["target"] == "native-identity-control" else self.pawn
        math = ue.find_class("KismetMathLibrary").get_cdo(); normal = math.call_function("MakeVector", *case["normal"])
        forward = float(math.call_function("Dot_VectorVector", actor.call_function("GetActorForwardVector"), normal))
        right = float(math.call_function("Dot_VectorVector", actor.call_function("GetActorRightVector"), normal))
        before = self.state(); rows = {}
        try:
            for profile, key in (("BlueprintFallback", "blueprint"), ("Python", "python")):
                ue.set_mixin_profile(self.melee, profile); counts = copy.deepcopy(policy.evidence(self.melee))
                result = self.caller.call_function("Select", self.melee, normal, actor)
                require(isinstance(result, tuple) and len(result) == 1, "external BP one-out montage shape differs")
                after = policy.evidence(self.melee)
                rows[key] = dict(result=path(result[0]), counters={name: after[name]-counts[name] for name in ("python_calls", "fallback_calls", "invalid_actor_native_fallback")}, last=copy.deepcopy(after["last"]))
        finally: ue.set_mixin_profile(self.melee, self.profile)
        self.report["cases"].append(dict(input=copy.deepcopy(case), native_normal=vector(normal), target_path=path(actor),
            native_forward_dot=forward, native_right_dot=right, native_state_before=before, native_state_after=self.state(), **rows))
        self.case_index += 1
        if self.case_index == len(PLAN): self.quiet_before = copy.deepcopy(policy.evidence(self.melee)); self.quiet_ticks = 0; self.enter("quiet")
    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "native Melee helper timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "helper": self.pair()
            elif self.phase == "quiet":
                require(policy.evidence(self.melee) == self.quiet_before, "late Melee helper dispatch")
                self.quiet_ticks += 1
                if self.quiet_ticks >= 20: self.report["quiet_after_helper_calls"] = True; self.complete()
            self.write(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def complete(self): self.finish()
    def cleanup(self):
        if self.cleaned: return
        if hasattr(self, "melee") and valid(self.melee):
            ue.set_mixin_profile(self.melee, self.profile)
            self.report.update(original_profile_restored=str(ue.get_mixin_profile(self.melee)) == self.profile, native_specs_unchanged=specs(self.asc) == self.original_specs)
        if self.caller is not None:
            if self.caller_added: self.caller_class.remove_from_root()
            self.report["caller_roots"] = dict(created=int(self.caller_added), released=int(self.caller_added)); self.caller = None
        if valid(self.control): self.control.call_function("K2_DestroyActor")
        self.report["control_actor_destroyed"] = not valid(self.control) or bool(self.control.call_function("IsActorBeingDestroyed"))
        self.cleaned = True
    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_MELEE_HIT_MONTAGE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_MELEE_HIT_MONTAGE_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPMeleeHitMontageResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
