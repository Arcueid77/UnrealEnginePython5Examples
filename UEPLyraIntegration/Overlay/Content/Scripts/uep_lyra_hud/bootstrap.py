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


def register_weapon_hud_mixins():
    # Four optional example-owned configured copies. The source-only/0.8
    # stage may not include them; never silently bind an unconfigured class.
    paths = (
        "/ShooterCore/UserInterface/HUD/W_WeaponAmmoAndName.W_WeaponAmmoAndName_C",
        "/ShooterCore/Weapons/Pistol/W_AmmoCounter_Pistol.W_AmmoCounter_Pistol_C",
        "/ShooterCore/Weapons/Rifle/W_AmmoCounter_Rifle.W_AmmoCounter_Rifle_C",
        "/ShooterCore/Weapons/Shotgun/W_AmmoCounter_Shotgun.W_AmmoCounter_Shotgun_C",
    )
    available = []
    for path in paths:
        try:
            cls = ue.load_class(path)
        except Exception:
            continue
        cdo = cls.get_cdo()
        if "PythonMixinProfile" not in cdo.properties():
            continue
        # Configured-but-invalid Interface/Set/Profile must fail registration,
        # not be silently treated as an optional source-only asset absence.
        ue.register_declared_mixin(cls)
        available.append(path)
    ue.log("UEP_LYRA_WEAPON_HUD_REGISTERED " + str(len(available)))
    return available


weapon_hud_registered = register_weapon_hud_mixins()


def register_combat_hud_mixins():
    available = []
    for path in (
        "/ShooterCore/UserInterface/HUD/W_Reticle_AmmoBar.W_Reticle_AmmoBar_C",
        "/ShooterCore/UserInterface/W_FireButton.W_FireButton_C",
        "/ShooterCore/UserInterface/HUD/W_DebugWeaponSpreadWidget.W_DebugWeaponSpreadWidget_C",
        "/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot_C",
    ):
        try:
            cls = ue.load_class(path)
        except Exception:
            continue
        if "PythonMixinProfile" not in cls.get_cdo().properties():
            continue
        ue.register_declared_mixin(cls)
        available.append(path)
    ue.log("UEP_LYRA_COMBAT_HUD_REGISTERED " + str(len(available)))
    return available


combat_hud_registered = register_combat_hud_mixins()


def register_nameplate_mixins():
    available = []
    for path in (
        "/Game/UI/Indicators/W_Nameplate.W_Nameplate_C",
        "/Game/UI/Indicators/NameplateManagerComponent.NameplateManagerComponent_C",
        "/Game/UI/Indicators/NameplateSource.NameplateSource_C",
    ):
        try:
            cls = ue.load_class(path)
        except Exception:
            continue
        if "PythonMixinProfile" not in cls.get_cdo().properties():
            continue
        ue.register_declared_mixin(cls)
        available.append(path)
    ue.log("UEP_LYRA_NAMEPLATES_REGISTERED "+str(len(available)))
    return available


nameplates_registered = register_nameplate_mixins()
