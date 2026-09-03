"""Configure the staged Lyra healthbar for the UEP 0.8 Python mixin."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile


RESULT_PREFIX = "-UEPGenerateLyraHUDMixinAssetsResult="

HEALTHBAR_BLUEPRINT = "/Game/UI/Hud/W_Healthbar"
MIXIN_ROOT = "/Game/UEPMixins"
MIXIN_NAME = "DA_LyraHealthbarMixin"
MIXIN_SET = f"{MIXIN_ROOT}/{MIXIN_NAME}"
PROFILE_VARIABLE = "PythonMixinProfile"
PYTHON_PROFILE = "Python"
BLUEPRINT_FALLBACK_PROFILE = "BlueprintFallback"


def object_path(package_path):
    return f"{package_path}.{package_path.rsplit('/', 1)[-1]}"


def command_line_value(prefix):
    for argument in sys.argv:
        if argument.startswith(prefix):
            return argument[len(prefix) :].strip('"')
    return None


def load_or_create_mixin_set():
    existing = ue.find_asset(object_path(MIXIN_SET))
    if existing is not None and existing.is_valid():
        return existing
    factory = DataAssetFactory()
    factory.DataAssetClass = UEPPythonMixinSet
    return ue.create_asset(MIXIN_NAME, MIXIN_ROOT, UEPPythonMixinSet, factory)


def generate():
    mixin_set = load_or_create_mixin_set()
    mixin_set.DefaultProfile = PYTHON_PROFILE
    mixin_set.Profiles = [
        UEPPythonMixinProfile(
            ProfileName=PYTHON_PROFILE,
            PythonModule="uep_lyra_hud.healthbar_mixin",
            PythonClass="LyraHealthbarPythonProfile",
        ),
        UEPPythonMixinProfile(
            ProfileName=BLUEPRINT_FALLBACK_PROFILE,
            PythonModule="uep_lyra_hud.healthbar_mixin",
            PythonClass="LyraHealthbarBlueprintFallbackProfile",
        ),
    ]

    healthbar = ue.load_object(Blueprint, HEALTHBAR_BLUEPRINT)
    if healthbar is None or not healthbar.is_valid():
        raise RuntimeError("unable to load the staged Lyra W_Healthbar Blueprint")

    # Package-load discovery can register an existing configured copy before
    # this commandlet edits it. Restore all routers before compiling the asset.
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(
        healthbar,
        mixin_set,
        PYTHON_PROFILE,
        PROFILE_VARIABLE,
    )
    ue.compile_blueprint(healthbar)

    cdo = healthbar.GeneratedClass.get_cdo()
    if PROFILE_VARIABLE not in cdo.properties():
        raise RuntimeError("healthbar profile selector is not reflected on the CDO")
    if cdo.GetPythonMixinSet() != mixin_set:
        raise RuntimeError("healthbar Interface did not return its Mixin Set")
    selected_profile = str(cdo.GetPythonMixinProfile())
    if selected_profile != PYTHON_PROFILE:
        raise RuntimeError("healthbar Interface did not return the Python profile")

    mixin_set.save_package()
    healthbar.save_package()

    return {
        "schema_version": 1,
        "status": "passed",
        "assets": [MIXIN_SET, HEALTHBAR_BLUEPRINT],
        "healthbar": {
            "path": HEALTHBAR_BLUEPRINT,
            "generated_class": healthbar.GeneratedClass.get_name(),
            "mixin_set": mixin_set.get_name(),
            "default_profile": mixin_set.DefaultProfile,
            "profile_count": len(mixin_set.Profiles),
            "profile_variable": PROFILE_VARIABLE,
            "profile_value": selected_profile,
        },
    }


result_value = command_line_value(RESULT_PREFIX)
if not result_value:
    raise RuntimeError(RESULT_PREFIX + "<path> is required")

try:
    report = generate()
    ue.log("UEP_LYRA_HUD_MIXIN_ASSET_GENERATION_PASSED")
except Exception:
    report = {
        "schema_version": 1,
        "status": "failed",
        "error": traceback.format_exc(),
    }
    ue.log_error("UEP_LYRA_HUD_MIXIN_ASSET_GENERATION_FAILED")

result_path = Path(result_value)
result_path.parent.mkdir(parents=True, exist_ok=True)
result_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["status"] != "passed":
    raise RuntimeError(report["error"])
