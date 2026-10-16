"""Inventory current 0.9/0.10 native class routers; NOT runtime acceptance.

No Blueprint save/compile, business event execution, migration percentage or
implicit registration count is treated as a gameplay proof.
"""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_runtime_mixin_coverage.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

RETAINED = {"/Game/UI/Hud/W_TouchRegion_Right.W_TouchRegion_Right",
            "/ShooterCore/Input/W_TouchRegion_Left.W_TouchRegion_Left"}


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def valid(value):
    try:
        return value is not None and value.is_valid()
    except Exception:
        return False


def relative_asset(asset):
    package = asset.split(".", 1)[0]
    mount, remainder = package[1:].split("/", 1)
    return Path("Content" if mount == "Game" else "Plugins/GameFeatures/"+mount+"/Content")/(remainder+".uasset")


def wired_entries(asset, python_functions):
    """Read actual staged graph control flow; do not compile or alter a pin."""
    from blueprint_model import ENTRY_CLASSES
    bp = ue.load_object(ue.find_class("Blueprint"), asset)
    rows = []
    for graph in ue.blueprint_get_all_graphs(bp):
        for entry in graph.Nodes:
            kind = entry.get_class().get_name()
            if kind not in ENTRY_CLASSES:
                continue
            try:
                name = str(entry.CustomFunctionName)
            except Exception:
                name = "None"
            if name in ("", "None"):
                name = graph.get_name() if kind == "K2Node_FunctionEntry" else str(entry.EventReference.MemberName)
            pending = [pin.owning_node for output in entry.node_pins() if output.direction == 1 and
                       output.category == "exec" for pin in output.get_linked_to()]
            seen, calls = set(), set()
            while pending:
                node = pending.pop()
                key = node.get_path_name()
                if key in seen:
                    continue
                seen.add(key)
                if node.get_class().get_name() in ("K2Node_CallFunction", "K2Node_CallParentFunction"):
                    calls.add(str(node.FunctionReference.MemberName))
                pending.extend(pin.owning_node for output in node.node_pins() if output.direction == 1 and
                               output.category == "exec" for pin in output.get_linked_to())
            rows.append(dict(entry=name, graph=graph.get_name(), entry_class=kind,
                reachable_execution_nodes=len(seen), calls=sorted(calls),
                calls_python_dispatch=sorted(calls & set(python_functions))))
    return rows


def audit():
    stage = require_authoring_stage(arg("UEPCoverageStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    manifest = Path(script).resolve().parents[1]/"Migration/batches.json"
    selected = [asset for asset in json.loads(manifest.read_text(encoding="utf-8-sig"))["assets"] if asset["version"] in ("0.9.0", "0.10.0")]
    if len(selected) != 37:
        raise RuntimeError("coverage scope changed; review explicit 0.9/0.10 asset list")
    classes, hashes = {}, {str(manifest): hashlib.sha256(manifest.read_bytes()).hexdigest()}
    for asset in selected:
        name = asset["path"]
        cls = ue.load_class(name+"_C")
        if cls is None or cls.get_path_name() != name+"_C":
            raise RuntimeError("original class identity changed/missing: "+name)
        classes[name] = cls
        file = stage/relative_asset(name)
        hashes[str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
    # This scans only loaded declared interfaces; no game-world tickers or
    # manual runtime bootstrap are installed by this read-only commandlet.
    ue.register_loaded_mixin_interfaces()
    routers = {entry["target_class"].get_path_name(): entry for entry in ue.get_registered_mixins()}
    rows = []
    for asset in selected:
        name, cls = asset["path"], classes[asset["path"]]
        entry, current = None, cls
        ancestry = []
        while valid(current):
            key = current.get_path_name()
            ancestry.append(key)
            if key in routers:
                entry = routers[key]
                break
            if key == "/Script/CoreUObject.Object":
                break  # Existing get_super_class raises for the null root parent.
            current = current.get_super_class()
        row = dict(asset=name, version=asset["version"], original_class=cls.get_path_name(), class_identity_preserved=True,
            reflected_properties=sorted(cls.get_cdo().properties()),
            retained_forwarder=name in RETAINED, native_router_class=None, profiles={}, unimplemented_union_methods=[],
            runtime_evidence=asset.get("evidence_run"), runtime_status=asset["status"], ancestry=ancestry)
        if entry is not None:
            row.update(native_router_class=entry["target_class"].get_path_name(), inherited_router=entry["target_class"] != cls,
                default_profile=entry["default_profile"], mixin_set=entry["mixin_set"].get_path_name() if entry.get("mixin_set") else None,
                routed_functions=sorted(entry["functions"]))
            for profile, binding in entry["profiles"].items():
                python_cls = binding["python_class"]
                row["profiles"][profile] = dict(python_class=python_cls.__module__+"."+python_cls.__qualname__,
                                               functions=sorted(binding["functions"]))
            default = row["profiles"].get(entry["default_profile"])
            row["unimplemented_union_methods"] = sorted(set(entry["functions"])-set(default["functions"])) if default else sorted(entry["functions"])
        row["staged_wired_entries"] = wired_entries(name, row["profiles"].get(row.get("default_profile"), {}).get("functions", []))
        rows.append(row)
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("coverage audit input changed")
    return dict(status="passed", runtime_acceptance=False, full_acceptance=False, assets_saved_or_compiled=False,
        coverage_is_registration_not_gameplay=True, current_versions=["0.9.0", "0.10.0"], assets=rows,
        unrouted_business_assets=[row["asset"] for row in rows if not row["retained_forwarder"] and row["native_router_class"] is None],
        partial_profile_assets=[row["asset"] for row in rows if row["unimplemented_union_methods"]], reference_hashes=hashes)


try:
    report = audit()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPCoverageAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_RUNTIME_COVERAGE_AUDIT_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
