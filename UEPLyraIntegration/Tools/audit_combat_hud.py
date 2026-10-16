"""Read-only reflected defaults/signatures for the 0.10 combat HUD pilots."""

import json
import hashlib
from pathlib import Path
import sys

import unreal_engine as ue


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


script = globals().get("__file__") or next(
    (value for value in sys.argv if Path(value).name == "audit_combat_hud.py"), None)
if script is None:
    raise RuntimeError("pass audit_combat_hud.py to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

stage = require_authoring_stage(argument("UEPCombatHUDStageRoot"),
                                ue.convert_relative_path_to_full(ue.get_content_dir()))
reference = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
result = argument("UEPCombatHUDAuditResult")
if result is None:
    raise RuntimeError("UEPCombatHUDAuditResult required")

from uep_lyra_hud.fire_button_mixin import CLICK_EVENT

fire = ue.load_class("/ShooterCore/UserInterface/W_FireButton.W_FireButton_C")
cdo = fire.get_cdo()
actions = {name: cdo.get_property(name).get_path_name()
           if cdo.get_property(name) else None for name in ("Associated Action", "Hold Action")}
subsystem = ue.find_class("EnhancedInputLocalPlayerSubsystem")
report = {
    "status": "passed", "stage_guard_passed": True,
    "fire_button": {"class": fire.get_path_name(), "properties": sorted(cdo.properties()),
                    "actions": actions, "click": ue.describe_function(fire, CLICK_EVENT)},
    "native_input": ue.describe_function(subsystem, "InjectInputVectorForAction"),
}
report["weapon_reticle_defaults"] = []
for weapon in ("Pistol", "Rifle", "Shotgun"):
    relative = Path("Plugins/GameFeatures/ShooterCore/Content/Weapons") / weapon / ("ID_" + weapon + ".uasset")
    staged_hash = hashlib.sha256((stage / relative).read_bytes()).hexdigest()
    reference_hash = hashlib.sha256((reference / relative).read_bytes()).hexdigest()
    if staged_hash != reference_hash:
        raise RuntimeError("Original weapon definition was modified: " + weapon)
    definition = ue.load_class("/ShooterCore/Weapons/" + weapon + "/ID_" + weapon + ".ID_" + weapon + "_C").get_cdo()
    fragments = []
    for fragment in definition.Fragments:
        if fragment.get_class().get_name() == "InventoryFragment_ReticleConfig":
            fragments.extend(widget.get_path_name() for widget in fragment.ReticleWidgets)
    report["weapon_reticle_defaults"].append({"weapon": weapon, "widgets": fragments,
                                             "stage_asset": str(stage / relative),
                                             "reference_asset": str(reference / relative),
                                             "unchanged_sha256": staged_hash})
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_COMBAT_HUD_AUDIT_PASSED")
