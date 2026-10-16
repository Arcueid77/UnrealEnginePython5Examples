"""Configure only the example-owned debug widget in a marked disposable stage."""

import hashlib
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_debug_spread_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass this script to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def argument(name):
    prefix = "-" + name + "="
    return next((arg[len(prefix):] for arg in sys.argv if arg.startswith(prefix)), None)


def generate():
    stage = require_authoring_stage(argument("UEPDebugSpreadStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = source / "Plugins/GameFeatures/ShooterCore/Content/UserInterface/HUD/W_DebugWeaponSpreadWidget.uasset"
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    factory = DataAssetFactory()
    factory.DataAssetClass = UEPPythonMixinSet
    name = "DA_W_DebugWeaponSpreadWidgetMixin"
    mixin = ue.find_asset("/Game/UEPMixins/" + name + "." + name)
    if mixin is None:
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.debug_spread_mixin", PythonClass=python_class)
                      for profile, python_class in (("Python", "LyraDebugSpreadPythonProfile"),
                                                     ("BlueprintFallback", "LyraDebugSpreadBlueprintFallbackProfile"))]
    path = "/ShooterCore/UserInterface/HUD/W_DebugWeaponSpreadWidget"
    blueprint = ue.load_object(Blueprint, path + ".W_DebugWeaponSpreadWidget")
    parent = blueprint.ParentClass
    ue.blueprint_configure_mixin(blueprint, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(blueprint)
    cdo = blueprint.GeneratedClass.get_cdo()
    if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python" or blueprint.ParentClass != parent:
        raise RuntimeError("Debug spread Interface/CDO/parent postcondition differs")
    blueprint.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Official debug widget changed")
    return {"status": "passed", "asset": path, "mixin_set": "/Game/UEPMixins/" + name,
            "reference_sha256": digest, "class_preserved": blueprint.GeneratedClass.get_name() == "W_DebugWeaponSpreadWidget_C",
            "parent_preserved": parent.get_path_name(), "runtime_acceptance": False}


result = argument("UEPGenerateDebugSpreadResult")
if not result:
    raise RuntimeError("UEPGenerateDebugSpreadResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_DEBUG_SPREAD_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
