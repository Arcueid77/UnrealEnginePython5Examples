"""Original device-color native signatures/defaults/graph pins; never save assets."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_device_color.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit():
    stage = require_authoring_stage(arg("UEPDeviceColorStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    relative = "Plugins/GameFeatures/ShooterCore/Content/Game/B_TeamColor_DeviceProperty.uasset"
    hashes = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (source, stage)}
    if len(set(hashes.values())) != 1: raise RuntimeError("device color audit requires unchanged original asset")
    bp = ue.load_object(ue.find_class("Blueprint"), "/ShooterCore/Game/B_TeamColor_DeviceProperty.B_TeamColor_DeviceProperty")
    cdo = bp.GeneratedClass.get_cdo()
    path = Path(arg("UEPDeviceColorAuditResult")).parent/"device-color-cdo.t3d"
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    if not exporter.export_to_file(cdo, str(path)): raise RuntimeError("native device color CDO export failed")
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in ("EvaluateDeviceProperty", "ApplyDeviceProperty", "ResetDeviceProperty")}
    parent = ue.describe_function(ue.find_class("ColorInputDeviceProperty"), "EvaluateDeviceProperty")
    nodes = []
    for graph in ue.blueprint_get_all_graphs(bp):
        for node in graph.Nodes:
            if node.get_class().get_name() not in ("K2Node_Event", "K2Node_CallParentFunction"): continue
            nodes.append(dict(graph=graph.get_name(), name=node.get_name(), type=node.get_class().get_name(),
                pins=[dict(name=pin.name, category=pin.category, default=pin.default_value,
                    object=pin.sub_category_object.get_path_name() if pin.sub_category_object else None,
                    links=[other.owning_node.get_name()+":"+other.name for other in pin.get_linked_to()]) for pin in node.node_pins()]))
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest: raise RuntimeError("read-only device audit changed an asset")
    return dict(status="passed", runtime_acceptance=False, assets_modified=False,
        assets=[dict(native_class=bp.GeneratedClass.get_path_name(), native_cdo_text=str(path), serialized_duration=float(cdo.get_property("PropertyDuration")),
            signatures=signatures, native_parent_signature=parent, original_event_parent_pins=nodes)], reference_hashes=hashes,
        hardware_output_tested=False)


report = audit()
Path(arg("UEPDeviceColorAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_DEVICE_COLOR_AUDIT_PASSED")
