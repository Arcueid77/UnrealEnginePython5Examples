"""Original team-color BP business; retained BP transport calls native parent."""
import copy
import unreal_engine as ue
from unreal_engine.structs import DeviceColorData
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/ShooterCore/Game/B_TeamColor_DeviceProperty.B_TeamColor_DeviceProperty_C"
GATE = "UEPDeviceColorRoute"
_counts = {}
_stats = dict(evaluations=0, valid_controllers=0, colors_written=0, fallback_evaluations=0, errors=[])


def snapshot(): return dict(copy.deepcopy(_stats), active_count=0, script_subscriptions_created=0)


def instance_snapshot(instance):
    return dict({key: 0 for key, value in _stats.items() if type(value) is int}, **_counts.get(instance.get_path_name(), {}))


def note(instance, key):
    _stats[key] += 1; row = _counts.setdefault(instance.get_path_name(), {}); row[key] = row.get(key, 0)+1
    while len(_counts) > 256: _counts.pop(next(iter(_counts)))


def choose(instance, platform_user):
    note(instance, "evaluations")
    try:
        controller = ue.find_class("InputDeviceLibrary").get_cdo().call_function("GetPlayerControllerFromPlatformUser", platform_user)
        if not valid(controller) or not controller.is_a(ue.find_class("LyraPlayerController")):
            return dict(ReturnValue=False, bCallNativeParent=False)
        note(instance, "valid_controllers")
        statics = ue.find_class("LyraTeamStatics").get_cdo()
        part_of_team, team_id, display = statics.call_function("FindTeamFromObject", controller.get_controlled_pawn(), False)
        linear = statics.call_function("GetTeamColorWithFallback", display, "TeamColor", ue.FLinearColor(0., 0., 0., 0.))
        color = ue.find_class("KismetMathLibrary").get_cdo().call_function("Conv_LinearColorToColor", linear, True)
        instance.set_property("ColorData", DeviceColorData(bEnable=True, bResetAfterCompletion=False, LightColor=color))
        note(instance, "colors_written")
        # Original native-parent node (including its unconnected DeviceId pin)
        # runs next. Python never replays Evaluate/Apply or changes device mapping.
        return dict(ReturnValue=False, bCallNativeParent=True)
    except Exception as error: _stats["errors"].append(str(error)); raise


class LyraDeviceColorPythonProfile:
    def Route(self, PlatformUser, DeviceId, DeltaTime, Duration): return choose(self, PlatformUser)
    Route.override = GATE
    Route.uep_named_outputs = True


class LyraDeviceColorBlueprintFallbackProfile:
    def Route(self, PlatformUser, DeviceId, DeltaTime, Duration):
        note(self, "fallback_evaluations"); return dict(ReturnValue=True, bCallNativeParent=False)
    Route.override = GATE
    Route.uep_named_outputs = True
