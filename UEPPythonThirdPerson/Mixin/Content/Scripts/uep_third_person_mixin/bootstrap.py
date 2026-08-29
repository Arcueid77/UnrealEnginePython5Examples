"""Register the Blueprint mixin and start the playable 0.7 runtime."""

import unreal_engine as ue

from .character_mixin import (  # noqa: F401
    BP_THIRD_PERSON_CHARACTER,
    MIXED_FUNCTIONS,
    ThirdPersonCharacterMixin,
)
from .runtime import MixinThirdPersonRuntime
from .smoke import start_smoke_if_requested


runtime = MixinThirdPersonRuntime()
runtime_ticker = ue.add_ticker(runtime.tick)
smoke, smoke_ticker = start_smoke_if_requested(runtime)
