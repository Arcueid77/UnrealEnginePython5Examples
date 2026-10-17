"""Original hit-react selection; Actor basis/dot/range/animation assets stay native."""
import unreal_engine as ue

CLASS = "/ShooterCore/Game/Melee/GA_Melee.GA_Melee_C"
METHOD = "Slelect Hit Montage"  # Preserve the authored public function name.
ASSETS = {name: "/Game/Characters/Heroes/Mannequin/Animations/Actions/"+asset+"."+asset for name, asset in (
    ("back", "AM_MM_HitReact_Back_Med_01"), ("front", "AM_MM_HitReact_Front_Hvy_01"),
    ("right", "AM_MM_HitReact_Right_Med_01"), ("left", "AM_MM_HitReact_Left_Med_01"))}


def evidence(ability):
    value = getattr(ability, "_uep_melee_hit_montage", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, invalid_actor_native_fallback=0, last=None)
        ability._uep_melee_hit_montage = value
    return value


def original(ability, normal, actor):
    value = ability.call_mixin_original(METHOD, normal, actor)
    if not isinstance(value, tuple) or len(value) != 1: raise RuntimeError("native Melee named output must be one montage tuple")
    return {"Hit Montage": value[0]}


def select(ability, normal, actor):
    record = evidence(ability); record["python_calls"] += 1
    if actor is None:
        # Keep original VM invalid-receiver/default-result behavior, rather
        # than introducing a new validity rule or manufacturing an error.
        record["invalid_actor_native_fallback"] += 1
        return original(ability, normal, actor)
    math = ue.find_class("KismetMathLibrary").get_cdo()
    forward = float(math.call_function("Dot_VectorVector", actor.call_function("GetActorForwardVector"), normal))
    right = float(math.call_function("Dot_VectorVector", actor.call_function("GetActorRightVector"), normal))
    straight = bool(math.call_function("InRange_FloatFloat", right, -.5, .5, True, True))
    choice = ("front" if forward > 0. else "back") if straight else ("left" if right > 0. else "right")
    record["last"] = dict(forward_dot=forward, right_dot=right, straight=straight, choice=choice)
    return {"Hit Montage": ue.load_object(ue.find_class("AnimMontage"), ASSETS[choice])}


class LyraMeleeHitMontagePythonProfile:
    def SelectHitMontage(self, HitNormal, HitActor): return select(self, HitNormal, HitActor)
    SelectHitMontage.override = METHOD
    SelectHitMontage.uep_named_outputs = True


class LyraMeleeHitMontageBlueprintFallbackProfile:
    def SelectHitMontage(self, HitNormal, HitActor):
        evidence(self)["fallback_calls"] += 1; return original(self, HitNormal, HitActor)
    SelectHitMontage.override = METHOD
    SelectHitMontage.uep_named_outputs = True
