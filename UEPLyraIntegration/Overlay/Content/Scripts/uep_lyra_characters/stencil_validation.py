"""Retained parent signature, real ChildActor recursion, native setters and GC."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .team_cosmetics_validation import Validation as TeamNative, ActorState, primitives
from .team_cosmetics_contract import PLAN as TEAM_PLAN
from .stencil_contract import PLAN, validate, require
from .outline_validation import gc
from . import stencil_mixin as policy

PROBE = "/Game/UEPValidation/BP_CharacterStencilCallProbe.BP_CharacterStencilCallProbe_C"


class Validation(TeamNative):
    def __init__(self, result):
        super().__init__(result)
        self.child = self.child_box = self.extra = self.stencil_caller = None
        self.stencil_caller_root = self.stencil_caller_released = False
        self.direct_complete = False
        self.report.update(stencil_cases=[], parent_bp_asset_modified=False, whole_parent_class_family_migrated=False,
            native_child_actor_created_destroyed=False, native_child_component_recursive_discovery=False,
            native_fixture_extra_component_created=False)

    def begin(self):
        self.report["natural_startup_stencil_python_dispatch"] = copy.deepcopy(policy.evidence(self.pawn))
        super().begin()
        self.stencil_caller = ue.load_class(PROBE); self.stencil_probe = self.stencil_caller.get_cdo()
        self.stencil_caller_root = not self.stencil_caller.is_rooted()
        if self.stencil_caller_root: self.stencil_caller.add_to_root()
        root = self.fixture_actor.get_property("RootComponent")
        self.extra = self.fixture_actor.add_actor_component(ue.find_class("BoxComponent"), "UEPStencilExtra", root)
        self.extra.call_function("SetCollisionEnabled", 0)
        child_component = self.fixture_actor.add_actor_component(ue.find_class("ChildActorComponent"), "UEPStencilChild", root)
        child_component.call_function("SetChildActorClass", ue.find_class("Actor"))
        self.child = child_component.get_property("ChildActor")
        require(valid(self.child), "native ChildActorComponent created no child")
        self.child.call_function("SetReplicates", False)
        self.child_box = self.child.add_actor_component(ue.find_class("BoxComponent"), "UEPStencilChildBox")
        self.child_box.call_function("SetCollisionEnabled", 0)
        found = primitives(self.fixture_actor)
        require(self.child_box in found and self.extra in found, "native recursive component discovery omitted fixture primitives")
        self.report.update(native_child_component_recursive_discovery=True, native_fixture_extra_component_created=True,
            fixture_actor_replication_disabled=not bool(self.fixture_actor.get_property("bReplicates")) and not bool(self.child.get_property("bReplicates")))
        # The two new primitives belong only to the test-owned Actor, not to
        # the actual player. Snapshot them before any business trial starts.
        self.states[1] = ActorState(self.fixture_actor)

    def start_trial(self):
        actor = self.states[0 if TEAM_PLAN[self.index][-1] == "owner" else 1].actor
        before = dict(policy.evidence(actor)); super().start_trial()
        self.row["stencil_counters"] = {key: value-before[key] for key, value in policy.evidence(actor).items()}

    def direct_trials(self):
        for name, profile, target, value, calls in PLAN:
            state = self.states[0 if target == "owner" else 1]; actor = state.actor
            components = list(primitives(actor)); flags = [bool(item.get_property("bRenderCustomDepth")) for item in components]
            ue.set_mixin_profile(actor, profile); before = dict(policy.evidence(actor))
            for number in range(calls): self.stencil_probe.call_function("UpdateStencil", actor, value)
            rows = [dict(component=item.get_path_name().replace(actor.get_path_name(), "Actor", 1), value=int(item.get_property("CustomDepthStencilValue")),
                render_custom_depth_unchanged=bool(item.get_property("bRenderCustomDepth")) == flag) for item, flag in zip(components, flags)]
            counts = {key: item-before[key] for key, item in policy.evidence(actor).items()}
            gc()
            self.report["stencil_cases"].append(dict(name=name, profile=profile, target=target, team_id=value, calls=calls, bp_reference_call=True,
                locally_controlled=bool(actor.call_function("IsLocallyControlled")), player_controlled=bool(actor.call_function("IsPlayerControlled")),
                components=sorted(rows, key=lambda row: row["component"]), child_components=sum(item.get_owner() == self.child for item in components),
                counters=counts, native_gc_held_components_and_callers_survived=all(valid(item) for item in components) and valid(self.caller) and valid(self.stencil_caller),
                original_visual_camera_profile_restored=state.restore()))
            ue.log("UEP_CHARACTER_STENCIL_CASE_PASSED "+name+"/"+profile)
        self.direct_complete = True

    def cleanup(self):
        errors = []
        try: super().cleanup()
        except Exception: errors.append(traceback.format_exc())
        try:
            if self.stencil_caller_root and not self.stencil_caller_released:
                self.stencil_caller.remove_from_root(); self.stencil_caller_released = True
        except Exception: errors.append(traceback.format_exc())
        self.report.update(stencil_caller_roots_created=int(self.stencil_caller_root), stencil_caller_roots_released=int(self.stencil_caller_released),
            native_child_actor_created_destroyed=self.child is not None and not valid(self.child))
        if errors: raise RuntimeError("stencil fixture cleanup failed: "+"\n".join(errors))

    def finish(self, error=None):
        if self.finished: return
        if not error and not self.direct_complete:
            try: self.direct_trials()
            except Exception: error = traceback.format_exc()
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_STENCIL_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_STENCIL_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterStencilResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
