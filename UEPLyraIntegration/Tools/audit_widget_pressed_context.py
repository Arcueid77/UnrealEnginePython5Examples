"""Read original pressed-widget runtime context; never save/compile assets."""
import hashlib
import json
from pathlib import Path
import sys

import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_widget_pressed_context.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

ASSETS = (
    "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhenInputPressed",
    "/ShooterExplorer/Input/Abilities/GA_ToggleInventory",
    "/ShooterExplorer/Input/Abilities/GA_ToggleMap",
    "/ShooterExplorer/System/Experiences/B_TestInventoryExperience",
    "/ShooterExplorer/System/Experiences/LAS_InventoryTest",
    "/ShooterExplorer/Input/Abilities/AbilitySet_InventoryTest",
    "/ShooterExplorer/Blueprint/B_Hero_Explorer",
    "/ShooterExplorer/Blueprint/B_Pawn_Explorer",
    "/ShooterExplorer/Input/Actions/IA_ToggleInventory",
    "/ShooterExplorer/Input/Actions/IA_ToggleMap",
)


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-" + name + "="))


def audit():
    stage = require_authoring_stage(arg("UEPWidgetPressedStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes, rows = {}, []
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    for path in (*ASSETS, "/ShooterExplorer/Maps/L_InventoryTestMap"):
        mount, tail = path.lstrip("/").split("/", 1)
        relative = "Plugins/GameFeatures/" + mount + "/Content/" + tail + (".umap" if path.endswith("L_InventoryTestMap") else ".uasset")
        pair = {str(root / relative): hashlib.sha256((root / relative).read_bytes()).hexdigest() for root in (source, stage)}
        if len(set(pair.values())) != 1: raise RuntimeError("unchanged original pressed-widget context required: " + path)
        hashes.update(pair)
        if path not in ASSETS: continue
        name = path.rsplit("/", 1)[-1]
        obj = ue.load_object(ue.find_class("Object"), path + "." + name)
        exported = obj.GeneratedClass.get_cdo() if obj.is_a(ue.find_class("Blueprint")) else obj
        output = Path(arg("UEPWidgetPressedAuditResult")).parent / (name + ".t3d")
        if not exporter.export_to_file(exported, str(output)): raise RuntimeError("native context export failed: " + path)
        rows.append(dict(asset=path, native_type=obj.get_class().get_path_name(), exported_native_type=exported.get_class().get_path_name(),
                         native_defaults_text=str(output)))
    for path, digest in hashes.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest: raise RuntimeError("read-only context audit changed input")
    return dict(status="passed", runtime_acceptance=False, assets_modified=False, assets=rows,
                reference_hashes=hashes, runtime_input_or_ui_tested=False, editor_or_test_tools_migrated=False)


report = audit()
Path(arg("UEPWidgetPressedAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_WIDGET_PRESSED_CONTEXT_AUDIT_PASSED")
