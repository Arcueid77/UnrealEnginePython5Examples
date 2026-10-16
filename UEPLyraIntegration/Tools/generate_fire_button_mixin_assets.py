"""Author only the 0.10 FireButton copy in a marked disposable stage."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_fire_button_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass this script to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def argument(name):
    prefix = "-" + name + "="
    return next((arg[len(prefix):] for arg in sys.argv if arg.startswith(prefix)), None)


def generate():
    require_authoring_stage(argument("UEPFireButtonStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins()
    path = "/ShooterCore/UserInterface/W_FireButton"
    mixin_path = "/Game/UEPMixins/DA_W_FireButtonMixin"
    mixin = ue.find_asset(mixin_path + ".DA_W_FireButtonMixin")
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset("DA_W_FireButtonMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [
        UEPPythonMixinProfile(ProfileName="Python", PythonModule="uep_lyra_hud.fire_button_mixin", PythonClass="LyraFireButtonPythonProfile"),
        UEPPythonMixinProfile(ProfileName="BlueprintFallback", PythonModule="uep_lyra_hud.fire_button_mixin", PythonClass="LyraFireButtonBlueprintFallbackProfile"),
    ]
    blueprint = ue.load_object(Blueprint, path + ".W_FireButton")
    ue.blueprint_configure_mixin(blueprint, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(blueprint)
    cdo = blueprint.GeneratedClass.get_cdo()
    if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
        raise RuntimeError("FireButton Interface/CDO postcondition differs")
    mixin.save_package()
    blueprint.save_package()
    return {"status": "passed", "asset": path, "mixin_set": mixin_path,
            "class_preserved": blueprint.GeneratedClass.get_name() == "W_FireButton_C"}


result = argument("UEPGenerateFireButtonResult")
if result is None:
    raise RuntimeError("UEPGenerateFireButtonResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_FIRE_BUTTON_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
