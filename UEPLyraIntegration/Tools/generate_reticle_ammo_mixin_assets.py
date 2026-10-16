"""Author only the 0.10 ammo-reticle copy in a marked disposable stage."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_reticle_ammo_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass this script to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def argument(name):
    prefix = "-" + name + "="
    return next((arg[len(prefix):] for arg in sys.argv if arg.startswith(prefix)), None)


def generate():
    require_authoring_stage(argument("UEPReticleStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.unregister_all_mixins()
    name = "W_Reticle_AmmoBar"
    path = "/ShooterCore/UserInterface/HUD/" + name
    mixin_path = "/Game/UEPMixins/DA_" + name + "Mixin"
    mixin = ue.find_asset(mixin_path + "." + mixin_path.rsplit("/", 1)[-1])
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(mixin_path.rsplit("/", 1)[-1], "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [
        UEPPythonMixinProfile(ProfileName="Python", PythonModule="uep_lyra_hud.reticle_ammo_mixin", PythonClass="LyraReticleAmmoPythonProfile"),
        UEPPythonMixinProfile(ProfileName="BlueprintFallback", PythonModule="uep_lyra_hud.reticle_ammo_mixin", PythonClass="LyraReticleAmmoBlueprintFallbackProfile"),
    ]
    blueprint = ue.load_object(Blueprint, path + "." + name)
    ue.blueprint_configure_mixin(blueprint, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(blueprint)
    cdo = blueprint.GeneratedClass.get_cdo()
    if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
        raise RuntimeError("reticle Interface/CDO postcondition differs")
    mixin.save_package()
    blueprint.save_package()
    return {"status": "passed", "asset": path, "mixin_set": mixin_path,
            "class_preserved": blueprint.GeneratedClass.get_name() == name + "_C"}


result = argument("UEPGenerateReticleResult")
if result is None:
    raise RuntimeError("UEPGenerateReticleResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_RETICLE_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
