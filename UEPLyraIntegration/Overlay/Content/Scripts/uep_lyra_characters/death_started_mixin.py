"""Real inherited Health delegate -> native random Delay -> virtual BP calls."""
import unreal_engine as ue
from unreal_engine.classes import Actor
from unreal_engine.structs import LatentActionInfo
from uep_lyra_world.effect_pad_mixin import valid
from .latent_keys import allocate
from . import ragdoll_mixin as ragdoll

BOUND_EVENT = "BndEvt__HealthComponent_K2Node_ComponentBoundEvent_0_LyraHealth_DeathEvent__DelegateSignature"
RESUME = "UEPCharacterAfterDeathDelay"


def evidence(actor):
    value = getattr(actor, "_uep_character_death_started", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, montage_calls=0, unregister_calls=0, missing_sense_noops=0,
            delay_requests=0, resumes=0, fallback_resumes=0, ragdoll_forwards=0, hide_forwards=0, death_forwards=0,
            uuid=None, pending=False, last_start=None, last_resume=None, trace=[])
        actor._uep_character_death_started = value
    return value


def stamp(actor):
    return dict(frame=int(ue.find_class("KismetSystemLibrary").get_cdo().call_function("GetFrameCount")),
        game_seconds=float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", actor)))


def trace(actor, event):
    value = evidence(actor); value["trace"].append(dict(event=event, **stamp(actor))); value["trace"] = value["trace"][-64:]


def resume(actor, linkage):
    if linkage != 0: raise ValueError("invalid native Character death-delay linkage")
    value = evidence(actor); value["pending"] = False; value["resumes"] += 1
    value["fallback_resumes"] += int(str(ue.get_mixin_profile(actor)) == "BlueprintFallback")
    value["last_resume"] = stamp(actor); trace(actor, "resume")
    for function, count, event in (("Ragdoll", "ragdoll_forwards", "ragdoll"), ("HideEquippedWeapons", "hide_forwards", "hide"), ("Death", "death_forwards", "death")):
        actor.call_function(function); value[count] += 1; trace(actor, event)


class LyraCharacterDeathStartedPythonProfile:
    def PythonDeathStarted(self, OwningActor: Actor):
        value = evidence(self); value["python_calls"] += 1
        montages = list(self.get_property("Death Montages")); math = ue.find_class("KismetMathLibrary").get_cdo()
        index = int(math.call_function("RandomIntegerInRange", 0, len(montages)-1))
        montage = montages[index] if 0 <= index < len(montages) else None
        self.call_function("PlayAnimMontage", montage, 1., "None"); value["montage_calls"] += 1; trace(self, "montage")
        sense = self.get_property("AIPerceptionStimuliSource")
        if valid(sense): sense.call_function("UnregisterFromSense", ue.find_class("AISense_Sight")); value["unregister_calls"] += 1
        else: value["missing_sense_noops"] += 1
        trace(self, "sight")
        duration = float(math.call_function("RandomFloatInRange", .1, .6))
        if value["uuid"] is None: value["uuid"], = allocate(self, "hero-death-delay", 1)
        value["last_start"] = dict(owning_actor=OwningActor.get_path_name() if valid(OwningActor) else None,
            montage=montage.get_path_name() if valid(montage) else None, montage_index=index, montage_count=len(montages), duration=duration, **stamp(self))
        info = LatentActionInfo(Linkage=0, UUID=value["uuid"], ExecutionFunction=RESUME, CallbackTarget=self)
        ue.find_class("KismetSystemLibrary").get_cdo().call_function("Delay", self, duration, info)
        value["delay_requests"] += 1; value["pending"] = True; trace(self, "delay")
    PythonDeathStarted.override = BOUND_EVENT

    def PythonAfterDeathDelay(self, Linkage: int): resume(self, Linkage)
    PythonAfterDeathDelay.override = RESUME


class LyraCharacterDeathStartedBlueprintFallbackProfile:
    def PythonDeathStarted(self, OwningActor: Actor):
        evidence(self)["fallback_calls"] += 1; trace(self, "fallback"); self.call_mixin_original(BOUND_EVENT, OwningActor)
    PythonDeathStarted.override = BOUND_EVENT

    # A pending Python-native action keeps its continuation across Profile
    # changes; fresh fallback entries still execute the untouched BP Delay.
    PythonAfterDeathDelay = LyraCharacterDeathStartedPythonProfile.__dict__["PythonAfterDeathDelay"]


for profile, parent in ((LyraCharacterDeathStartedPythonProfile, ragdoll.LyraCharacterRagdollPythonProfile),
                        (LyraCharacterDeathStartedBlueprintFallbackProfile, ragdoll.LyraCharacterRagdollBlueprintFallbackProfile)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__"): setattr(profile, name, method)
