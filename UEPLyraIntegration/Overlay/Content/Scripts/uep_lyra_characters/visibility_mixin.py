"""Native GameplayReady delegate -> native next-tick action -> Actor visibility."""
import unreal_engine as ue
from unreal_engine.structs import LatentActionInfo
from uep_lyra_world.effect_pad_mixin import valid
from . import possessed_mixin as possessed
from .latent_keys import allocate

SHOW, RESUME, REGISTER = "ShowPawnAgainNextFrame", "UEPCharacterVisibilityResume", "UEPRegisterCharacterVisibilityReady"


def evidence(actor):
    value = getattr(actor, "_uep_character_visibility", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, delay_requests=0, resumes=0, show_calls=0,
            uuid=None, pending=False, last_payload=None, trace=[])
        actor._uep_character_visibility = value
    return value


def trace(actor, event):
    value = evidence(actor)
    value["trace"].append(dict(event=event, frame=int(ue.find_class("KismetSystemLibrary").get_cdo().call_function("GetFrameCount")),
        hidden=bool(actor.get_property("bHidden"))))
    value["trace"] = value["trace"][-32:]


def received(actor, params, profile):
    counts = evidence(actor); counts["python_calls" if profile == "Python" else "fallback_calls"] += 1
    # Observation only: the original deliberately ignores this payload.
    counts["last_payload"] = dict(actor=params.OwningActor.get_path_name() if valid(params.OwningActor) else None,
        feature=str(params.FeatureName), state=str(params.FeatureState.TagName),
        implementer=params.Implementer.get_path_name() if valid(params.Implementer) else None)
    trace(actor, "received")
    return counts


def resume(actor, linkage):
    if linkage != 0: raise ValueError("invalid native visibility linkage")
    counts = evidence(actor); counts["pending"] = False; counts["resumes"] += 1
    trace(actor, "resume"); actor.call_function("SetActorHiddenInGame", False); counts["show_calls"] += 1; trace(actor, "shown")


class LyraCharacterVisibilityPythonProfile:
    def ShowPawnAgainNextFrame(self, Params):
        counts = received(self, Params, "Python")
        if counts["uuid"] is None: counts["uuid"], = allocate(self, "gameplay-ready-visibility", 1)
        info = LatentActionInfo(Linkage=0, UUID=counts["uuid"], ExecutionFunction=RESUME, CallbackTarget=self)
        ue.find_class("KismetSystemLibrary").get_cdo().call_function("DelayUntilNextTick", self, info)
        counts["delay_requests"] += 1; counts["pending"] = True; trace(self, "delay")

    def PythonVisibilityResume(self, Linkage: int): resume(self, Linkage)
    PythonVisibilityResume.override = RESUME


class LyraCharacterVisibilityBlueprintFallbackProfile:
    def ShowPawnAgainNextFrame(self, Params):
        received(self, Params, "BlueprintFallback"); self.call_mixin_original(SHOW, Params)

    # A pending Python-created action keeps its own continuation across Profile
    # changes. Fresh fallback entries still use the untouched original BP delay.
    PythonVisibilityResume = LyraCharacterVisibilityPythonProfile.__dict__["PythonVisibilityResume"]


for profile, parent in ((LyraCharacterVisibilityPythonProfile, possessed.LyraCharacterPossessedPythonProfile),
                        (LyraCharacterVisibilityBlueprintFallbackProfile, possessed.LyraCharacterPossessedBlueprintFallbackProfile)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__"): setattr(profile, name, method)
