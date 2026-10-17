"""Dash direction choice only; actual rotations/math and animation stay native."""
import copy
import unreal_engine as ue

CLASS = "/ShooterCore/Game/Dash/GA_Hero_Dash.GA_Hero_Dash_C"
METHOD = "SelectDirectionalMontage"
FIELDS = ("Dash_Fwd Montage", "Dash_Bwd Montage", "Dash_Left Montage", "Dash_Right Montage")
OUTPUTS = ("DirectionalMontage", "BiasForwardMovement")


def evidence(ability):
    value = getattr(ability, "_uep_dash_selector", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, last=None)
        ability._uep_dash_selector = value
    return value


def choose(ability, facing, movement):
    math = ue.find_class("KismetMathLibrary").get_cdo()
    a = math.call_function("Conv_VectorToRotator", movement)
    b = math.call_function("Conv_VectorToRotator", facing)
    yaw = float(math.call_function("NormalizedDeltaRotator", a, b).yaw)
    magnitude = float(math.call_function("Abs", yaw))
    index = 0 if magnitude < 45. else 1 if magnitude > 135. else 2 if yaw < 0. else 3
    value = evidence(ability); value["python_calls"] += 1
    value["last"] = dict(yaw=yaw, magnitude=magnitude, field=FIELDS[index], forward=index == 0)
    return dict(DirectionalMontage=ability.get_property(FIELDS[index]), BiasForwardMovement=index == 0)


class LyraDashSelectorPythonProfile:
    def SelectDirectionalMontage(self, FacingDirection, MovementDirection): return choose(self, FacingDirection, MovementDirection)
    SelectDirectionalMontage.uep_named_outputs = True


class LyraDashSelectorBlueprintFallbackProfile:
    def SelectDirectionalMontage(self, FacingDirection, MovementDirection):
        evidence(self)["fallback_calls"] += 1
        result = self.call_mixin_original(METHOD, FacingDirection, MovementDirection)
        if not isinstance(result, tuple) or len(result) != 2: raise RuntimeError("original Dash selector named-output shape differs")
        return dict(zip(OUTPUTS, result))
    SelectDirectionalMontage.uep_named_outputs = True
