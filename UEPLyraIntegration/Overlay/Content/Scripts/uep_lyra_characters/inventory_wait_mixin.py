"""Three original readiness checkpoints; native latent action owns scheduling."""
import uuid
import unreal_engine as ue
from unreal_engine.structs import LatentActionInfo
from uep_lyra_world.effect_pad_mixin import valid
from . import inventory_ready_mixin as ready

RESUME = "UEPInventoryWaitResume"
CLASSES = (None, "LyraInventoryManagerComponent", "LyraQuickBarComponent")
REASONS = ("missing_controller", "missing_inventory", "missing_quickbar")


def evidence(actor):
    value = getattr(actor, "_uep_character_inventory_wait", None)
    if value is None:
        value = dict(uuids=None, delay_requests=0, resumes=0, fallback_resumes=0, grant_forwards=0,
            pending=[False]*3, stage_requests=[0]*3, stage_resumes=[0]*3, trace=[])
        actor._uep_character_inventory_wait = value
    return value


def trace(actor, event, stage):
    value = evidence(actor)
    frame = int(ue.find_class("KismetSystemLibrary").get_cdo().call_function("GetFrameCount"))
    value["trace"].append(dict(event=event, stage=stage, frame=frame)); value["trace"] = value["trace"][-32:]


def defer(actor, stage):
    values = evidence(actor)
    if values["uuids"] is None:
        # UUID keys belong to this CallbackTarget only. Keep three independent,
        # stable keys per Actor; never cancel other Actor/native latent actions.
        ids = set()
        while len(ids) < 3: ids.add((uuid.uuid4().int & 0x7fffffff) or 1)
        values["uuids"] = list(ids)
    info = LatentActionInfo(Linkage=stage, UUID=values["uuids"][stage], ExecutionFunction=RESUME, CallbackTarget=actor)
    ue.find_class("KismetSystemLibrary").get_cdo().call_function("DelayUntilNextTick", actor, info)
    values["delay_requests"] += 1; values["stage_requests"][stage] += 1; values["pending"][stage] = True
    trace(actor, "delay", stage)


def advance(actor, stage):
    for index in range(stage, 3):
        controller = actor.call_function("GetController")
        value = controller if index == 0 or not valid(controller) else controller.call_function("GetComponentByClass", ue.find_class(CLASSES[index]))
        if not valid(value): defer(actor, index); return REASONS[index]
    actor.call_function("AddInitialInventory"); evidence(actor)["grant_forwards"] += 1; trace(actor, "grant", stage)
    return None


def resume(actor, stage):
    if stage not in (0, 1, 2): raise ValueError("invalid native inventory wait linkage")
    values = evidence(actor); values["pending"][stage] = False; values["resumes"] += 1; values["stage_resumes"][stage] += 1
    trace(actor, "resume", stage); advance(actor, stage)


class LyraCharacterInventoryWaitPythonProfile:
    def PythonExperienceReady(self):
        counts = ready.evidence(self); counts["python_calls"] += 1
        reason = advance(self, 0)
        if reason is None: counts["immediate_grants"] += 1
        else: counts[reason] += 1

    PythonExperienceReady.override = ready.READY

    def PythonInventoryWaitResume(self, Linkage: int): resume(self, Linkage)
    PythonInventoryWaitResume.override = RESUME


class LyraCharacterInventoryWaitBlueprintFallbackProfile:
    def PythonInventoryWaitResume(self, Linkage: int):
        if Linkage not in (0, 1, 2): raise ValueError("invalid native inventory wait linkage")
        values = evidence(self); values["pending"][Linkage] = False; values["fallback_resumes"] += 1
        self.call_mixin_original(ready.READY)

    PythonInventoryWaitResume.override = RESUME


for profile, parent in ((LyraCharacterInventoryWaitPythonProfile, ready.LyraCharacterInventoryReadyPythonProfile),
                        (LyraCharacterInventoryWaitBlueprintFallbackProfile, ready.LyraCharacterInventoryReadyBlueprintFallbackProfile)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__") and name not in profile.__dict__:
            setattr(profile, name, method)
