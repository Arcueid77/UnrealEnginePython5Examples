"""Read-only signatures and defaults for the first Lyra weapon HUD batch."""

import json
from pathlib import Path
import sys

import unreal_engine as ue

# UEP's Py commandlet executes a file in __main__ without setting __file__.
script_file = globals().get("__file__") or next(
    (arg for arg in sys.argv if not arg.startswith("-") and Path(arg).name == "audit_weapon_hud.py"), None
)
if not script_file:
    raise RuntimeError("audit_weapon_hud.py must be passed as the Py commandlet script")
sys.path.insert(0, str(Path(script_file).resolve().parent))
from stage_safety import require_authoring_stage


ASSETS = {
    "W_WeaponAmmoAndName": "/ShooterCore/UserInterface/HUD/W_WeaponAmmoAndName.W_WeaponAmmoAndName_C",
    "W_AmmoCounter_Pistol": "/ShooterCore/Weapons/Pistol/W_AmmoCounter_Pistol.W_AmmoCounter_Pistol_C",
    "W_AmmoCounter_Rifle": "/ShooterCore/Weapons/Rifle/W_AmmoCounter_Rifle.W_AmmoCounter_Rifle_C",
    "W_AmmoCounter_Shotgun": "/ShooterCore/Weapons/Shotgun/W_AmmoCounter_Shotgun.W_AmmoCounter_Shotgun_C",
}

prefix = "-UEPWeaponHUDAuditResult="
result_path = next((arg[len(prefix):] for arg in sys.argv if arg.startswith(prefix)), None)
if not result_path:
    raise RuntimeError(prefix + "<path> is required")
stage_prefix = "-UEPWeaponHUDStageRoot="
stage_root = next((arg[len(stage_prefix):] for arg in sys.argv if arg.startswith(stage_prefix)), None)
project_content = ue.convert_relative_path_to_full(ue.get_content_dir())
if stage_root:
    require_authoring_stage(stage_root, project_content)
rows = []
for name, path in ASSETS.items():
    target = ue.load_class(path)
    cdo = target.get_cdo()
    functions = ["Tick"]
    if name == "W_WeaponAmmoAndName":
        functions.append("BndEvt__W_WeaponAmmoAndName_TouchButton_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature")
    else:
        functions.extend(("OnWeaponInitialized", "SetWeaponSpecificImages"))
    properties = sorted(cdo.properties())
    declaration = None
    if "PythonMixinProfile" in properties:
        mixin_set = cdo.GetPythonMixinSet()
        declaration = {"mixin_set": mixin_set.get_path_name() if mixin_set else None,
                       "default_profile": str(cdo.GetPythonMixinProfile())}
    rows.append({"name": name, "path": path, "properties": properties, "declaration": declaration,
                 "functions": {function: ue.describe_function(target, function) for function in functions}})
brush = ue.find_struct("SlateBrush")()
report = {"status": "passed", "assets": rows,
          "brush_default_image_size": str(brush.ImageSize),
          "stage_guard_passed": stage_root is not None, "project_content_dir": project_content}
Path(result_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_WEAPON_HUD_AUDIT_PASSED")
