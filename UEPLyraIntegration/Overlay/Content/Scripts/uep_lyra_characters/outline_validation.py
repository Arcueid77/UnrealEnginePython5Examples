"""Real BP/material/interface calls with native GC and exact camera-state undo."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from .inventory_clear_mixin import inventory_state
from . import outline_mixin as policy
from .outline_contract import CLASS, PLAN, SEED_TEAM, SEED_COLOR, validate, require

PROBE = "/Game/UEPValidation/BP_CharacterOutlineCallProbe.BP_CharacterOutlineCallProbe_C"


def path(value): return value.get_path_name() if valid(value) else None


def canon(value):
    if value is None or isinstance(value, (str, bool, int, float)): return value
    if isinstance(value, (list, tuple)): return [canon(item) for item in value]
    if isinstance(value, dict): return {key: canon(item) for key, item in value.items()}
    if callable(getattr(value, "get_path_name", None)): return dict(object=value.get_path_name())
    if callable(getattr(value, "fields", None)): return {name: canon(getattr(value, name)) for name in value.fields()}
    for names in (("r", "g", "b", "a"), ("x", "y", "z", "w"), ("x", "y", "z"), ("x", "y")):
        if all(hasattr(value, name) for name in names): return [float(getattr(value, name)) for name in names]
    raise RuntimeError("unverified native postprocess field type: "+str(type(value)))


def color(values): return ue.FLinearColor(*values)
def rgba(value): return [float(value.r), float(value.g), float(value.b), float(value.a)]
def gc(): ue.find_class("KismetSystemLibrary").get_cdo().call_function("CollectGarbage")


class Caller:
    """The test owns this generated BP class across explicit native GC."""
    def __init__(self):
        self.cls = ue.load_class(PROBE); self.object = self.cls.get_cdo()
        self.added_root, self.released = not self.cls.is_rooted(), 0
        if self.added_root: self.cls.add_to_root()

    def close(self):
        if self.added_root and not self.released:
            self.cls.remove_from_root(); self.released = 1


class Trial:
    def __init__(self, actor, owner, caller):
        self.actor, self.owner = actor, owner
        self.camera, self.material = actor.get_property("CameraComponent"), actor.get_property(policy.FIELD)
        self.profile = str(ue.get_mixin_profile(actor)); self.pp = self.camera.get_property("PostProcessSettings").clone()
        self.pp_before, self.native_roots, self.roots_released = canon(self.pp), [], 0
        self.caller, self.probe = caller, caller.object
        self.locally_controlled = bool(actor.call_function("IsLocallyControlled"))
        references = [self.material]+[entry.Object for entry in self.pp.WeightedBlendables.Array]
        self.original_references = {path(value): value for value in references if valid(value)}
        for value in self.original_references.values():
            if not value.is_rooted(): value.add_to_root(); self.native_roots.append(value)

    def create(self):
        parent = ue.load_object(ue.find_class("MaterialInterface"), policy.PARENT)
        value = ue.find_class("KismetMaterialLibrary").get_cdo().call_function("CreateDynamicMaterialInstance", self.actor, parent, "None", 0)
        require(valid(value), "native fixture material unavailable")
        value.call_function("SetScalarParameterValue", "TeamID", SEED_TEAM)
        value.call_function("SetVectorParameterValue", "TeamColor", color(SEED_COLOR)); return value

    def execute(self, index):
        name, profile, kind, team, values, calls, target = PLAN[index]
        empty = self.pp.clone(); weights = empty.WeightedBlendables.clone(); weights.Array = []; empty.WeightedBlendables = weights
        self.camera.set_property("PostProcessSettings", empty)
        material = None if kind == "new" else self.create()
        self.actor.set_property(policy.FIELD, material)
        if kind == "attached": self.camera.call_function("AddOrUpdateBlendable", material, 1.0)
        ue.set_mixin_profile(self.actor, profile); before = dict(policy.evidence(self.actor)); identities = []
        for number in range(calls):
            self.probe.call_function("UpdateOutline", self.actor, team, color(values))
            identities.append(path(self.actor.get_property(policy.FIELD)))
        current = self.actor.get_property(policy.FIELD)
        blendables = self.camera.get_property("PostProcessSettings").WeightedBlendables.Array
        # Only ordinary material references are temporarily rooted by the
        # fixture. Production code owns via original Actor/camera properties.
        gc()
        return dict(name=name, profile=profile, kind=kind, team=team, color=list(values), calls=calls, target=target,
            locally_controlled=self.locally_controlled, bp_reference_call=True, material_exists=valid(current),
            native_material_class=current.get_class().get_path_name() if valid(current) else None,
            material_parent=path(current.get_property("Parent")) if valid(current) else None,
            scalar=float(current.call_function("K2_GetScalarParameterValue", "TeamID")) if valid(current) else None,
            vector=rgba(current.call_function("K2_GetVectorParameterValue", "TeamColor")) if valid(current) else None,
            same_material_across_repeats=len(set(identities)) == 1,
            native_probe_class_cdo_survived_gc=valid(self.caller.cls) and valid(self.probe),
            native_gc_held_reference_survived=path(self.actor.get_property(policy.FIELD)) == identities[-1] and (current is None or valid(current)),
            blendable_count=len(blendables), blendable_weights=[float(entry.Weight) for entry in blendables],
            blendable_references_match=all(entry.Object == current for entry in blendables),
            counters={key: value-before[key] for key, value in policy.evidence(self.actor).items()})

    def restore(self):
        self.actor.set_property(policy.FIELD, self.material); self.camera.set_property("PostProcessSettings", self.pp)
        ue.set_mixin_profile(self.actor, self.profile)
        restored = self.actor.get_property(policy.FIELD) == self.material and canon(self.camera.get_property("PostProcessSettings")) == self.pp_before and str(ue.get_mixin_profile(self.actor)) == self.profile
        require(restored, "outline original field/full camera settings/Profile not restored")
        return restored

    def close(self):
        try: self.restore()
        finally:
            for value in self.native_roots:
                if value.is_rooted(): value.remove_from_root(); self.roots_released += 1


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result); self.trials, self.fixture_actor, self.caller = [], None, None
        self.report.update(pixels_verified=False, outline_rendering_verified=False, material_replication_claimed=False,
            whole_character_migrated=False, full_acceptance=False, production_roots_objects=False)

    def begin(self):
        self.caller = Caller()
        self.inventory_before = inventory_state(self.controller); self.cdo = self.pawn.get_class().get_cdo()
        self.cdo_before = (str(ue.get_mixin_profile(self.cdo)), path(self.cdo.get_property(policy.FIELD)))
        self.report["natural_startup_python_dispatch"] = dict(policy.evidence(self.pawn))
        self.report["natural_startup_material_exists"] = valid(self.pawn.get_property(policy.FIELD))
        cls = ue.load_class(CLASS)
        self.fixture_actor = self.world.actor_spawn(cls, ue.FVector(200000., 200000., 2000.))
        require(valid(self.fixture_actor), "native unpossessed Character fixture spawn failed")
        self.report.update(retained_character_class=self.pawn.get_class().get_path_name(),
            native_owner_local_control=bool(self.pawn.call_function("IsLocallyControlled")),
            native_unpossessed_actor_local_control=bool(self.fixture_actor.call_function("IsLocallyControlled")))
        self.trials.append(Trial(self.pawn, True, self.caller))
        self.trials.append(Trial(self.fixture_actor, False, self.caller)); self.enter("trial")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240, "native outline software timeout")
            if self.phase == "ready": self.ready()
            elif self.phase == "trial" and time.monotonic()-self.phase_started >= .1:
                trial = self.trials[0 if PLAN[self.index][-1] == "owner" else 1]
                row = trial.execute(self.index); row["original_field_camera_profile_restored"] = trial.restore()
                self.report["cases"].append(row); ue.log("UEP_CHARACTER_OUTLINE_CASE_PASSED "+row["name"]+"/"+row["profile"])
                self.index += 1
                if self.index == len(PLAN): self.finish()
                else: self.enter("trial")
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def cleanup(self):
        errors = []
        for trial in self.trials:
            try: trial.close()
            except Exception: errors.append(traceback.format_exc())
        self.report["fixture_material_roots_created"] = sum(len(trial.native_roots) for trial in self.trials)
        self.report["fixture_material_roots_released"] = sum(trial.roots_released for trial in self.trials)
        if self.trials:
            try:
                gc()
                self.report["native_original_material_references_valid_after_gc"] = all(valid(value) for trial in self.trials for value in trial.original_references.values())
                self.report["original_actor_camera_profile_cdo_inventory_restored"] = all(trial.restore() for trial in self.trials) and inventory_state(self.controller) == self.inventory_before and (
                    str(ue.get_mixin_profile(self.cdo)), path(self.cdo.get_property(policy.FIELD))) == self.cdo_before
            except Exception: errors.append(traceback.format_exc())
        try:
            if valid(self.fixture_actor): self.fixture_actor.call_function("K2_DestroyActor")
        except Exception: errors.append(traceback.format_exc())
        self.report["native_unpossessed_actor_created_destroyed"] = self.fixture_actor is not None and not valid(self.fixture_actor)
        if self.caller is not None:
            try: self.caller.close()
            except Exception: errors.append(traceback.format_exc())
            self.report.update(fixture_probe_class_roots_created=int(self.caller.added_root), fixture_probe_class_roots_released=self.caller.released)
        if errors: raise RuntimeError("outline fixture cleanup failed: "+"\n".join(errors))

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_OUTLINE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_OUTLINE_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterOutlineResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
