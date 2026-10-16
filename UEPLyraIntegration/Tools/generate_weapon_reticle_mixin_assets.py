"""Retain each original weapon reticle class/layout and declare Python business."""

import hashlib
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_weapon_reticle_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass the generator to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


def generate():
    stage = require_authoring_stage(argument("UEPWeaponReticleStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    helper = ue.load_class("/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C")
    rows, hashes = [], {}
    for kind in ("Pistol", "Rifle", "Shotgun"):
        ue.unregister_all_mixins()
        name = "W_Reticle_" + kind
        path = "/ShooterCore/Weapons/" + kind + "/" + name
        reference = source / "Plugins/GameFeatures/ShooterCore/Content/Weapons" / kind / (name + ".uasset")
        hashes[str(reference)] = hashlib.sha256(reference.read_bytes()).hexdigest()
        bp = ue.load_object(Blueprint, path + "." + name)
        parent = bp.ParentClass
        mixin_name = "DA_" + name + "Mixin"
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.find_asset("/Game/UEPMixins/" + mixin_name + "." + mixin_name)
        if mixin is None:
            mixin = ue.create_asset(mixin_name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
        mixin.DefaultProfile = "Python"
        mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.weapon_reticle_mixin", PythonClass=python_class)
                          for profile, python_class in (("Python", "LyraWeaponReticlePythonProfile"),
                                                         ("BlueprintFallback", "LyraWeaponReticleBlueprintFallbackProfile"))]
        variables = {str(var.VarName) for var in bp.NewVariables}
        if "UEPReticleKind" not in variables:
            ue.blueprint_add_member_variable(bp, "UEPReticleKind", "name", False, kind)
        if "PythonMessageAdapterClass" not in variables:
            ue.blueprint_add_member_variable(bp, "PythonMessageAdapterClass",
                                            EdGraphPinType(PinCategory="class", PinSubCategoryObject=ue.find_class("Object")))
        ue.compile_blueprint(bp)
        ue.unregister_all_mixins()
        ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
        ue.compile_blueprint(bp)
        cdo = bp.GeneratedClass.get_cdo()
        cdo.set_property("PythonMessageAdapterClass", helper)
        if (str(cdo.UEPReticleKind) != kind or cdo.GetPythonMixinSet() != mixin
                or str(cdo.GetPythonMixinProfile()) != "Python" or bp.ParentClass != parent):
            raise RuntimeError("reticle CDO/Interface/parent differs: " + name)
        bp.save_package()
        mixin.save_package()
        rows.append({"asset": path, "class_preserved": bp.GeneratedClass.get_name() == name + "_C",
                     "kind": kind, "message_adapter": helper.get_path_name()})
    for path, digest in hashes.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Official reticle asset changed")
    return {"status": "passed", "assets": rows, "reference_hashes": hashes, "runtime_acceptance": False}


result = argument("UEPGenerateWeaponReticleResult")
if result is None:
    raise RuntimeError("UEPGenerateWeaponReticleResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_WEAPON_RETICLE_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
