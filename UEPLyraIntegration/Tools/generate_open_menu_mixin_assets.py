"""Configure the example-owned menu button only; never edit the reference."""

import hashlib
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_open_menu_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass the generator to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


def generate():
    stage = require_authoring_stage(argument("UEPOpenMenuStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = source / "Content/UI/Hud/W_OpenMenuTouchButton.uasset"
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    name = "DA_W_OpenMenuTouchButtonMixin"
    mixin = ue.find_asset("/Game/UEPMixins/" + name + "." + name)
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.open_menu_mixin", PythonClass=python_class)
                      for profile, python_class in (("Python", "LyraOpenMenuPythonProfile"), ("BlueprintFallback", "LyraOpenMenuBlueprintFallbackProfile"))]
    path = "/Game/UI/Hud/W_OpenMenuTouchButton"
    bp = ue.load_object(Blueprint, path + ".W_OpenMenuTouchButton")
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
        raise RuntimeError("Open Menu Interface/CDO postcondition differs")
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != digest:
        raise RuntimeError("official button changed")
    return {"status": "passed", "asset": path, "reference_sha256": digest,
            "class_preserved": bp.GeneratedClass.get_name() == "W_OpenMenuTouchButton_C", "runtime_acceptance": False}


result = argument("UEPGenerateOpenMenuResult")
if result is None:
    raise RuntimeError("UEPGenerateOpenMenuResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_OPEN_MENU_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
