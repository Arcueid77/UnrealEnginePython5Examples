"""Configure only the four first-batch weapon widgets in a marked stage."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

# UEP's Py commandlet executes a file in __main__ without setting __file__.
script_file = globals().get("__file__") or next(
    (arg for arg in sys.argv if not arg.startswith("-") and Path(arg).name == "generate_weapon_hud_mixin_assets.py"), None
)
if not script_file:
    raise RuntimeError("generate_weapon_hud_mixin_assets.py must be passed as the Py commandlet script")
sys.path.insert(0, str(Path(script_file).resolve().parent))
from stage_safety import require_authoring_stage


ASSETS = {
    "W_WeaponAmmoAndName": ("/ShooterCore/UserInterface/HUD/W_WeaponAmmoAndName", "LyraWeaponAmmoPythonProfile"),
    "W_AmmoCounter_Pistol": ("/ShooterCore/Weapons/Pistol/W_AmmoCounter_Pistol", "LyraAmmoCounterPythonProfile"),
    "W_AmmoCounter_Rifle": ("/ShooterCore/Weapons/Rifle/W_AmmoCounter_Rifle", "LyraAmmoCounterPythonProfile"),
    "W_AmmoCounter_Shotgun": ("/ShooterCore/Weapons/Shotgun/W_AmmoCounter_Shotgun", "LyraAmmoCounterPythonProfile"),
}


def argument(prefix):
    return next((arg[len(prefix):] for arg in sys.argv if arg.startswith(prefix)), None)


def generate():
    require_authoring_stage(
        argument("-UEPWeaponHUDStageRoot="),
        ue.convert_relative_path_to_full(ue.get_content_dir()),
    )
    ue.unregister_all_mixins()
    report = {"schema_version": 1, "status": "passed", "assets": []}
    for name, (path, python_class) in ASSETS.items():
        mixin_path = "/Game/UEPMixins/DA_" + name + "Mixin"
        mixin = ue.find_asset(mixin_path + "." + mixin_path.rsplit("/", 1)[-1])
        if mixin is None:
            factory = DataAssetFactory()
            factory.DataAssetClass = UEPPythonMixinSet
            mixin = ue.create_asset(mixin_path.rsplit("/", 1)[-1], "/Game/UEPMixins", UEPPythonMixinSet, factory)
        mixin.DefaultProfile = "Python"
        mixin.Profiles = [
            UEPPythonMixinProfile(ProfileName="Python", PythonModule="uep_lyra_hud.ammo_mixin", PythonClass=python_class),
            UEPPythonMixinProfile(ProfileName="BlueprintFallback", PythonModule="uep_lyra_hud.ammo_mixin",
                                  PythonClass="LyraWeaponHUDBlueprintFallbackProfile"),
        ]
        blueprint = ue.load_object(Blueprint, path + "." + name)
        ue.unregister_all_mixins()
        ue.blueprint_configure_mixin(blueprint, mixin, "Python", "PythonMixinProfile")
        ue.compile_blueprint(blueprint)
        cdo = blueprint.GeneratedClass.get_cdo()
        if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
            raise RuntimeError("weapon HUD Interface/CDO configuration differs for " + name)
        mixin.save_package()
        blueprint.save_package()
        report["assets"].append({"blueprint": path, "mixin_set": mixin_path,
                                  "python_class": python_class, "runtime_class": blueprint.GeneratedClass.get_name()})
    return report


result_path = argument("-UEPGenerateWeaponHUDResult=")
if not result_path:
    raise RuntimeError("-UEPGenerateWeaponHUDResult=<path> is required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_WEAPON_HUD_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
