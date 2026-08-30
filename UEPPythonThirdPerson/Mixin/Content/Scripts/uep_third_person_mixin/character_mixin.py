"""Per-instance Python profiles routed through one unchanged Blueprint class."""

import math

import unreal_engine as ue
from unreal_engine import FRotator


CHARACTER_CLASS_PATH = (
    "/Game/ThirdPerson/Blueprints/"
    "BP_ThirdPersonCharacter.BP_ThirdPersonCharacter_C"
)
PYTHON_PROFILE = "Python"
BLUEPRINT_FALLBACK_PROFILE = "BlueprintFallback"

BP_THIRD_PERSON_CHARACTER = ue.load_class(CHARACTER_CLASS_PATH)
if BP_THIRD_PERSON_CHARACTER is None:
    raise RuntimeError("unable to load the official Third Person character class")


_reentrancy_probe_enabled = False
_reentrancy_probe_peer = None
_reentrancy_probe = {
    "initializer_mutations_rejected": 0,
    "teardown_mutations_rejected": 0,
    "nested_peer_dispatches": 0,
}


def arm_reentrancy_probe(peer):
    """Exercise callback mutation guards and nested-object initialization once."""
    global _reentrancy_probe_enabled, _reentrancy_probe_peer
    _reentrancy_probe_enabled = True
    _reentrancy_probe_peer = peer
    for key in _reentrancy_probe:
        _reentrancy_probe[key] = 0


def reentrancy_probe_snapshot():
    return dict(_reentrancy_probe)


def _probe_initializer_reentrancy(instance):
    global _reentrancy_probe_peer
    if not _reentrancy_probe_enabled:
        return
    try:
        ue.unregister_mixin(BP_THIRD_PERSON_CHARACTER)
    except RuntimeError:
        _reentrancy_probe["initializer_mutations_rejected"] += 1
    else:
        raise RuntimeError("mixin initializer was allowed to unregister its router")

    peer = _reentrancy_probe_peer
    _reentrancy_probe_peer = None
    if peer is not None and peer is not instance:
        peer.Aim(0.0, 0.0)
        _reentrancy_probe["nested_peer_dispatches"] += 1


def _probe_teardown_reentrancy():
    if not _reentrancy_probe_enabled:
        return
    try:
        ue.set_default_mixin_profile(
            BP_THIRD_PERSON_CHARACTER,
            PYTHON_PROFILE,
        )
    except RuntimeError:
        _reentrancy_probe["teardown_mutations_rejected"] += 1
    else:
        raise RuntimeError("mixin teardown was allowed to mutate its router")


def _initialize_profile_state(instance, profile_name):
    instance.PythonMixinInitializationEvents = (
        getattr(instance, "PythonMixinInitializationEvents", 0) + 1
    )
    instance.PythonMixinTeardownEvents = getattr(
        instance,
        "PythonMixinTeardownEvents",
        0,
    )
    instance.PythonMixinInitialized = True
    instance.PythonMixinActiveProfile = profile_name
    instance.PythonMixinBeginPlayEvents = getattr(
        instance,
        "PythonMixinBeginPlayEvents",
        0,
    )
    instance.PythonMixinOriginalBeginPlayCalls = getattr(
        instance,
        "PythonMixinOriginalBeginPlayCalls",
        0,
    )
    instance.PythonMixinMoveEvents = getattr(
        instance,
        "PythonMixinMoveEvents",
        0,
    )
    instance.PythonMixinAimEvents = getattr(
        instance,
        "PythonMixinAimEvents",
        0,
    )
    instance.PythonAnimationSpeed = 0.0
    instance.PythonAnimationState = "blueprint_anim"
    _probe_initializer_reentrancy(instance)


def _teardown_profile_state(instance):
    _probe_teardown_reentrancy()
    instance.PythonMixinTeardownEvents += 1
    instance.PythonMixinActiveProfile = None


def _profile_snapshot(instance):
    velocity = instance.get_actor_velocity()
    instance.PythonAnimationSpeed = math.sqrt(
        (velocity.x * velocity.x) + (velocity.y * velocity.y)
    )
    return {
        "profile": instance.PythonMixinActiveProfile,
        "initialized": instance.PythonMixinInitialized,
        "initializations": instance.PythonMixinInitializationEvents,
        "teardowns": instance.PythonMixinTeardownEvents,
        "begin_play": instance.PythonMixinBeginPlayEvents,
        "original_begin_play": instance.PythonMixinOriginalBeginPlayCalls,
        "move": instance.PythonMixinMoveEvents,
        "aim": instance.PythonMixinAimEvents,
        "speed": instance.PythonAnimationSpeed,
    }


class ThirdPersonPythonProfile:
    """Python owns Move/Aim while the original BP remains the Unreal type."""

    def __init__(self):
        _initialize_profile_state(self, PYTHON_PROFILE)

    def __uep_mixin_teardown__(self):
        _teardown_profile_state(self)

    def ReceiveBeginPlay(self):
        self.PythonMixinBeginPlayEvents += 1
        self.call_mixin_original("ReceiveBeginPlay")
        self.PythonMixinOriginalBeginPlayCalls += 1
        ue.log("UEP_MIXIN_THIRD_PERSON_CHARACTER_READY")

    def Move(self, right, forward):
        self.PythonMixinMoveEvents += 1
        rotation = self.get_control_rotation()
        yaw_rotation = FRotator(0.0, 0.0, rotation.yaw)
        self.add_movement_input(ue.get_forward_vector(yaw_rotation), forward)
        self.add_movement_input(ue.get_right_vector(yaw_rotation), right)

    def Aim(self, yaw, pitch):
        self.PythonMixinAimEvents += 1
        self.add_controller_yaw_input(yaw)
        self.add_controller_pitch_input(pitch)

    def mixin_snapshot(self):
        return _profile_snapshot(self)


class ThirdPersonBlueprintFallbackProfile:
    """Override Aim only; Move is intentionally inherited from the original BP."""

    def __init__(self):
        _initialize_profile_state(self, BLUEPRINT_FALLBACK_PROFILE)

    def __uep_mixin_teardown__(self):
        _teardown_profile_state(self)

    def ReceiveBeginPlay(self):
        self.PythonMixinBeginPlayEvents += 1
        self.call_mixin_original("ReceiveBeginPlay")
        self.PythonMixinOriginalBeginPlayCalls += 1

    def Aim(self, yaw, pitch):
        self.PythonMixinAimEvents += 1
        self.add_controller_yaw_input(yaw * 0.35)
        self.add_controller_pitch_input(pitch * 0.35)

    def mixin_snapshot(self):
        return _profile_snapshot(self)


MIXED_FUNCTIONS = ("Aim", "Move", "ReceiveBeginPlay")
PROFILE_FUNCTIONS = {
    PYTHON_PROFILE: ("Aim", "Move", "ReceiveBeginPlay"),
    BLUEPRINT_FALLBACK_PROFILE: ("Aim", "ReceiveBeginPlay"),
}


def register_character_profiles_direct():
    """Register both profiles through the explicit Python API for regression."""
    ue.register_mixin_profile(
        BP_THIRD_PERSON_CHARACTER,
        PYTHON_PROFILE,
        ThirdPersonPythonProfile,
        make_default=True,
    )
    ue.register_mixin_profile(
        BP_THIRD_PERSON_CHARACTER,
        BLUEPRINT_FALLBACK_PROFILE,
        ThirdPersonBlueprintFallbackProfile,
    )


def register_character_mixin():
    """Register the Mixin Set declared by the playable Character Blueprint."""
    ue.register_declared_mixin(BP_THIRD_PERSON_CHARACTER)


ue.log("UEP_MIXIN_THIRD_PERSON_PROFILE_CLASSES_LOADED")
