"""Local direction preparation; original navigation/math/movement implementations stay native."""
import unreal_engine as ue
from .dash_rpc_input_mixin import (LyraDashRPCInputPythonProfile, LyraDashRPCInputBlueprintFallbackProfile,
    vector, path)

GATE = "UEPDashPrepareLocalDirection"


def evidence(ability):
    value = getattr(ability, "_uep_dash_local_direction", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, last=None)
        ability._uep_dash_local_direction = value
    return value


def library(name): return ue.find_class(name).get_cdo()


def resolve(ability):
    actor = ability.call_function("GetLyraCharacterFromActorInfo")
    facing = actor.call_function("GetActorForwardVector")
    last = actor.call_function("GetLastMovementInputVector")
    controller = library("AIBlueprintHelperLibrary").call_function("GetAIController", actor)
    ai = bool(library("KismetSystemLibrary").call_function("IsValid", controller))
    math = library("KismetMathLibrary"); projected = None; projection_succeeded = None
    if ai:
        point = actor.get_actor_location()
        # Original BP ignores the success flag, including native failure output.
        result = library("NavigationSystemV1").call_function("K2_ProjectPointToNavigation", WorldContextObject=ability,
            Point=point, NavData=None, FilterClass=None, QueryExtent=ue.FVector(500., 500., 500.))
        projected, = [value for value in result if type(value) is not bool]
        projection_succeeded, = [value for value in result if type(value) is bool]
        flat = math.call_function("Multiply_VectorVector", math.call_function("Subtract_VectorVector", projected, point), ue.FVector(1., 1., 0.))
        last = movement = math.call_function("Normal", flat, .0001)
    else:
        camera = actor.get_property("CameraComponent").call_function("GetForwardVector")
        movement = math.call_function("Multiply_VectorVector", camera, ue.FVector(1., 1., 1.2))
    return facing, last, movement, dict(ai=ai, facing=vector(facing), last_input=vector(last), movement=vector(movement),
        projected=vector(projected) if projected is not None else None, projection_succeeded=projection_succeeded)


def prepare(ability):
    value = evidence(ability); value["python_calls"] += 1
    facing, last, movement, data = resolve(ability)
    result = ability.call_function("SelectDirectionalMontage", facing, last)
    if not isinstance(result, tuple) or len(result) != 2 or type(result[1]) is not bool:
        raise RuntimeError("native Dash selector must return montage/bool")
    montage, bias = result
    direction = movement if bias else last
    # Match the original executable stores, then skip their whole BP span.
    ability.set_property("Montage", montage); ability.set_property("Direction", direction)
    value["last"] = dict(data, bias=bias, montage=path(montage), direction=vector(direction))
    return False


class LyraDashLocalDirectionPythonProfile:
    SelectDirectionalMontage = LyraDashRPCInputPythonProfile.__dict__["SelectDirectionalMontage"]
    StoreRemoteInput = LyraDashRPCInputPythonProfile.__dict__["StoreRemoteInput"]
    def PrepareLocalDirection(self): return prepare(self)
    PrepareLocalDirection.override = GATE


class LyraDashLocalDirectionBlueprintFallbackProfile:
    SelectDirectionalMontage = LyraDashRPCInputBlueprintFallbackProfile.__dict__["SelectDirectionalMontage"]
    StoreRemoteInput = LyraDashRPCInputBlueprintFallbackProfile.__dict__["StoreRemoteInput"]
    def PrepareLocalDirection(self): evidence(self)["fallback_calls"] += 1; return True
    PrepareLocalDirection.override = GATE
