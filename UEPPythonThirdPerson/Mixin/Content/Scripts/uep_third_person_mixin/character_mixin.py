"""Python behavior mixed into the unchanged template Character Blueprint."""

import math

import unreal_engine as ue
from unreal_engine import FRotator


CHARACTER_CLASS_PATH = (
    "/Game/ThirdPerson/Blueprints/"
    "BP_ThirdPersonCharacter.BP_ThirdPersonCharacter_C"
)

BP_THIRD_PERSON_CHARACTER = ue.load_class(CHARACTER_CLASS_PATH)
if BP_THIRD_PERSON_CHARACTER is None:
    raise RuntimeError("unable to load the official Third Person character class")


@ue.mixin(BP_THIRD_PERSON_CHARACTER)
class ThirdPersonCharacterMixin:
    """Replace only movement/look while retaining the Blueprint class."""

    def __init__(self):
        self.PythonMixinInitializationEvents = (
            getattr(self, "PythonMixinInitializationEvents", 0) + 1
        )
        self.PythonMixinTeardownEvents = getattr(
            self,
            "PythonMixinTeardownEvents",
            0,
        )
        self.PythonMixinInitialized = True
        self.PythonMixinBeginPlayEvents = 0
        self.PythonMixinOriginalBeginPlayCalls = 0
        self.PythonMixinMoveEvents = 0
        self.PythonMixinAimEvents = 0
        self.PythonAnimationSpeed = 0.0
        self.PythonAnimationState = "blueprint_anim"

    def __uep_mixin_teardown__(self):
        self.PythonMixinTeardownEvents += 1

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
        velocity = self.get_actor_velocity()
        self.PythonAnimationSpeed = math.sqrt(
            (velocity.x * velocity.x) + (velocity.y * velocity.y)
        )
        return {
            "initialized": self.PythonMixinInitialized,
            "initializations": self.PythonMixinInitializationEvents,
            "teardowns": self.PythonMixinTeardownEvents,
            "begin_play": self.PythonMixinBeginPlayEvents,
            "original_begin_play": self.PythonMixinOriginalBeginPlayCalls,
            "move": self.PythonMixinMoveEvents,
            "aim": self.PythonMixinAimEvents,
            "speed": self.PythonAnimationSpeed,
        }


MIXED_FUNCTIONS = ("Aim", "Move", "ReceiveBeginPlay")


def register_character_mixin():
    """Re-register the same class after an explicit restoration test."""
    return ue.register_mixin(
        BP_THIRD_PERSON_CHARACTER,
        ThirdPersonCharacterMixin,
    )


ue.log("UEP_MIXIN_THIRD_PERSON_REGISTERED")
