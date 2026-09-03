"""Register the Mixin Set declared by Lyra's staged W_Healthbar copy."""

import unreal_engine as ue

from . import state
from .healthbar_mixin import (  # noqa: F401
    BLUEPRINT_FALLBACK_PROFILE,
    PYTHON_PROFILE,
    LyraHealthbarBlueprintFallbackProfile,
    LyraHealthbarPythonProfile,
)


HEALTHBAR_CLASS_PATH = "/Game/UI/Hud/W_Healthbar.W_Healthbar_C"


def register_healthbar_mixin():
    # The source-only validation lane intentionally stages no Lyra Content.
    # UEP's load_class raises when the class is absent rather than returning
    # None, so keep the optional HUD slice from blocking the base probe.
    try:
        healthbar_class = ue.load_class(HEALTHBAR_CLASS_PATH)
    except Exception:
        healthbar_class = None
    state.mark_asset_available(healthbar_class is not None)
    if healthbar_class is None:
        ue.log("UEP_LYRA_HUD_SOURCE_ASSET_UNAVAILABLE")
        return False
    ue.register_declared_mixin(healthbar_class)
    state.mark_registered()
    ue.log("UEP_LYRA_HUD_INTERFACE_REGISTERED")
    return True


registered = register_healthbar_mixin()
