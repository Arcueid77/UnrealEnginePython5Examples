"""Confirm empty/parent-only touch BP shells; native game C++ is later scope."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "audit_touch_regions.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics

ASSETS = (("/Game/UI/Hud/W_TouchRegion_Base.W_TouchRegion_Base", "Content/UI/Hud/W_TouchRegion_Base.uasset"),
          ("/Game/UI/Hud/W_TouchRegion_Right.W_TouchRegion_Right", "Content/UI/Hud/W_TouchRegion_Right.uasset"),
          ("/ShooterCore/Input/W_TouchRegion_Left.W_TouchRegion_Left", "Plugins/GameFeatures/ShooterCore/Content/Input/W_TouchRegion_Left.uasset"))


def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))


def audit():
    stage = require_authoring_stage(arg("UEPTouchRegionsStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes, assets = {}, []
    for object_path, relative in ASSETS:
        pair = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (stage, reference)}
        if len(set(pair.values())) != 1:
            raise RuntimeError("original touch region input required")
        hashes.update(pair)
        bp = ue.load_object(ue.find_class("Blueprint"), object_path)
        graphs = []
        for graph in list(bp.FunctionGraphs)+list(bp.UbergraphPages):
            nodes = [n for n in graph.Nodes if n.get_class().get_name() != "EdGraphNode_Comment"]
            if any(n.get_class().get_name() not in ("K2Node_Event", "K2Node_CallParentFunction") for n in nodes):
                raise RuntimeError("touch region contains non-forwarding BP business")
            events = [n for n in nodes if n.get_class().get_name() == "K2Node_Event"]
            calls = [n for n in nodes if n.get_class().get_name() == "K2Node_CallParentFunction"]
            if len(events) != len(calls):
                raise RuntimeError("unpaired touch region forwarder")
            for event in events:
                links = event.node_find_pin("then").get_linked_to()
                if len(links) != 1 or links[0].owning_node not in calls:
                    raise RuntimeError("touch region execution is not direct parent forwarding")
            graphs.append(dict(name=graph.get_name(), nodes=len(nodes), parent_forwarders=len(calls),
                semantic_digest=semantics(graph, {n.get_name() for n in graph.Nodes}, set())))
        assets.append(dict(asset=object_path, parent=bp.ParentClass.get_path_name(), graphs=graphs,
            runtime_bp_business_nodes=0, disposition="retain_configuration_and_parent_forwarders",
            native_game_project_cpp_migrated=False))
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("read-only touch region changed")
    return dict(status="passed", runtime_acceptance=False, assets=assets, reference_hashes=hashes,
                scope_decision="No BP business to translate. Native LyraTouchRegion remains a separate game-project C++ phase.")


try:
    report = audit()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPTouchRegionsAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_TOUCH_REGIONS_AUDIT_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
