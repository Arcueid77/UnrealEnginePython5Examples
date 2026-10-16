"""Original input-driven widget ability families and reflected native UI API."""
import hashlib
import json
from pathlib import Path
import sys

import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_widget_input_abilities.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from blueprint_graph_digest import digest as graph_digest

ASSETS = (
    "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhenInputPressed",
    "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhileInputHeld",
    "/ShooterCore/ControlPoint/GA_ShowLeaderboard_CP",
    "/ShooterCore/Elimination/GA_ShowLeaderboard_TDM",
    "/ShooterExplorer/Input/Abilities/GA_ToggleInventory",
    "/ShooterExplorer/Input/Abilities/GA_ToggleMap",
)


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-" + name + "="))


def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)): return value
    if hasattr(value, "get_path_name"): return value.get_path_name()
    if hasattr(value, "TagName"): return str(value.TagName)
    raise RuntimeError("unexpected widget ability default type: " + type(value).__name__)


def audit():
    stage = require_authoring_stage(arg("UEPWidgetInputStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    marker = json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))
    source = Path(marker["source"]).parent
    rows, hashes = [], {}
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    for path in ASSETS:
        mount, tail = path.lstrip("/").split("/", 1)
        relative = "Plugins/GameFeatures/" + mount + "/Content/" + tail + ".uasset"
        pair = {str(root / relative): hashlib.sha256((root / relative).read_bytes()).hexdigest() for root in (source, stage)}
        if len(set(pair.values())) != 1: raise RuntimeError("read-only audit requires unchanged original widget ability: " + path)
        hashes.update(pair)
        name = path.rsplit("/", 1)[-1]
        bp = ue.load_object(ue.find_class("Blueprint"), path + "." + name)
        cls, cdo = bp.GeneratedClass, bp.GeneratedClass.get_cdo()
        output = Path(arg("UEPWidgetInputAuditResult")).parent / (name + "-cdo.t3d")
        if not exporter.export_to_file(cdo, str(output)): raise RuntimeError("native widget ability CDO export failed")
        defaults = {field: serial(cdo.get_property(field)) for field in ("InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationPolicy",
            "WidgetToSpawn", "Widget Class", "Layer Name", "SpawnedWidget", "Async Action") if field in cdo.properties()}
        methods = ["K2_ActivateAbility", "K2_OnEndAbility"]
        if "WhileInputHeld" in path or "Leaderboard" in path: methods += ["CreateAndDisplayWidget", "RemoveWidget"]
        else: methods += ["OnWidgetDeactivated"]
        rows.append(dict(native_class=cls.get_path_name(), defaults=defaults, native_cdo_text=str(output),
            signatures={name: ue.describe_function(cls, name) for name in methods},
            original_graph_digests={graph.get_name(): graph_digest(graph) for graph in ue.blueprint_get_all_graphs(bp)}))
    native = {}
    for name, methods in (("AsyncAction_PushContentToLayerForPlayer", ("PushContentToLayerForPlayer", "Activate", "Cancel")),
                          ("CommonActivatableWidget", ("DeactivateWidget", "IsActivated"))):
        cls = ue.find_class(name)
        native[name] = {method: ue.describe_function(cls, method) for method in methods}
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest: raise RuntimeError("read-only widget audit changed an asset")
    return dict(status="passed", runtime_acceptance=False, assets_modified=False, assets=rows,
                native_signatures=native, reference_hashes=hashes, ui_input_suspension_runtime_tested=False)


report = audit()
Path(arg("UEPWidgetInputAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_WIDGET_INPUT_AUDIT_PASSED")
