"""Read-only original Emote defaults, public ingress and native task signatures."""
import hashlib
import json
from pathlib import Path
import sys

import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_emote.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from blueprint_graph_digest import digest as digest_graph


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-" + name + "="))


def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "get_path_name"):
        return value.get_path_name()
    if hasattr(value, "TagName"):
        return str(value.TagName)
    raise RuntimeError("unexpected Emote default type: " + type(value).__name__)


def audit():
    stage = require_authoring_stage(arg("UEPEmoteStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    marker = json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))
    source = Path(marker["source"]).parent
    relative = "Plugins/GameFeatures/ShooterCore/Content/Game/Emote/GA_Emote.uasset"
    hashes = {str(root / relative): hashlib.sha256((root / relative).read_bytes()).hexdigest() for root in (source, stage)}
    if len(set(hashes.values())) != 1:
        raise RuntimeError("original Emote asset required for read-only audit")
    cls = ue.load_class("/ShooterCore/Game/Emote/GA_Emote.GA_Emote_C")
    bp = ue.load_object(ue.find_class("Blueprint"), "/ShooterCore/Game/Emote/GA_Emote.GA_Emote")
    cdo = cls.get_cdo()
    fields = ("InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationPolicy", "Montage to Play", "WidgetClasses", "WidgetExtensionPointTags")
    defaults = {}
    for field in fields:
        if field in cdo.properties():
            value = cdo.get_property(field)
            defaults[field] = [serial(item) for item in value] if isinstance(value, list) else serial(value)
    montages = {}
    for field in cdo.properties():
        if "montage" in field.lower():
            value = cdo.get_property(field)
            if value is None or not hasattr(value, "is_a") or not value.is_a(ue.find_class("AnimMontage")):
                continue
            defaults[field] = serial(value)
            montages[field] = float(value.call_function("GetPlayLength"))
    if len(montages) != 1:
        raise RuntimeError("one actual default Emote montage required")
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    cdo_text = Path(arg("UEPEmoteAuditResult")).parent / "GA_Emote-cdo.t3d"
    if not exporter.export_to_file(cdo, str(cdo_text)):
        raise RuntimeError("native Emote CDO export failed")
    signatures = {name: ue.describe_function(cls, name) for name in ("K2_ActivateAbility", "K2_OnEndAbility", "CheckForMovement")}
    native = {}
    for class_name, names in (("Character", ("UnCrouch", "StopAnimMontage")),
                              ("AbilityTask_PlayMontageAndWait", ("CreatePlayMontageAndWaitProxy",))):
        native_cls = ue.find_class(class_name)
        native[class_name] = {name: ue.describe_function(native_cls, name) for name in names}
    graphs = [{"name": graph.get_name(), "digest": digest_graph(graph), "nodes": [
        dict(name=node.get_name(), type=node.get_class().get_name(), pins=[
            dict(name=pin.name, direction=pin.direction, default=pin.default_value,
                 object=pin.sub_category_object.get_path_name() if pin.sub_category_object else None,
                 links=[other.owning_node.get_name() + ":" + other.name for other in pin.get_linked_to()])
            for pin in node.node_pins()]) for node in graph.Nodes]}
              for graph in ue.blueprint_get_all_graphs(bp)]
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("read-only Emote audit changed an asset")
    return dict(status="passed", runtime_acceptance=False, assets_modified=False,
                assets=[dict(native_class=cls.get_path_name(), defaults=defaults, native_montage_lengths=montages,
                             native_cdo_text=str(cdo_text), signatures=signatures, native_signatures=native, graphs=graphs)],
                reference_hashes=hashes)


report = audit()
Path(arg("UEPEmoteAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_EMOTE_AUDIT_PASSED")
