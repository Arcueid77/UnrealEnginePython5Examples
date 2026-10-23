"""Inventory current native class routers; NOT runtime acceptance.

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


def wired_entries(asset, python_functions, include_targets=False):
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
            seen, calls, targets, kinds = set(), set(), [], set()
            while pending:
                node = pending.pop()
                key = node.get_path_name()
                if key in seen:
                    continue
                seen.add(key)
                kinds.add(node.get_class().get_name())
                if node.get_class().get_name() in ("K2Node_CallFunction", "K2Node_CallParentFunction"):
                    calls.add(str(node.FunctionReference.MemberName))
                    if include_targets:
                        owner = node.FunctionReference.MemberParent
                        try: target = node.node_find_pin("self").default_object
                        except (AttributeError, RuntimeError): target = None
                        targets.append(dict(method=str(node.FunctionReference.MemberName),
                            owner_class=owner.get_path_name() if valid(owner) else None,
                            default_target_class=target.get_class().get_path_name() if valid(target) else None))
                pending.extend(pin.owning_node for output in node.node_pins() if output.direction == 1 and
                               output.category == "exec" for pin in output.get_linked_to())
            rows.append(dict(entry=name, graph=graph.get_name(), entry_class=kind,
                reachable_execution_nodes=len(seen), calls=sorted(calls),
                calls_python_dispatch=sorted(calls & set(python_functions))))
            if include_targets: rows[-1].update(call_targets=targets, reachable_node_classes=sorted(kinds))
    return rows


def audit():
    stage = require_authoring_stage(arg("UEPCoverageStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    manifest = Path(script).resolve().parents[1]/"Migration/batches.json"
    all_candidates = "-UEPCoverageAllCandidates" in sys.argv
    inventory = json.loads(manifest.read_text(encoding="utf-8-sig"))["assets"]
    selected = [asset for asset in inventory if all_candidates or asset["version"] in ("0.9.0", "0.10.0")]
    if len(selected) != (246 if all_candidates else 37) or len({asset["path"] for asset in selected}) != len(selected):
        raise RuntimeError("coverage scope changed; review exact original candidate inventory")
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
        inherited_bindings = []
        ancestry = []
        while valid(current):
            key = current.get_path_name()
            ancestry.append(key)
            if key in routers:
                if entry is None: entry = routers[key]
                inherited_bindings.append(dict(target_class=key, default_profile=routers[key]["default_profile"],
                    profiles={name: sorted(profile["functions"]) for name, profile in routers[key]["profiles"].items()}))
                if not all_candidates: break
            if key == "/Script/CoreUObject.Object":
                break  # Existing get_super_class raises for the null root parent.
            current = current.get_super_class()
        row = dict(asset=name, version=asset["version"], original_class=cls.get_path_name(), class_identity_preserved=True,
            reflected_properties=sorted(cls.get_cdo().properties()),
            retained_forwarder=name in RETAINED, native_router_class=None, profiles={}, unimplemented_union_methods=[],
            runtime_evidence=asset.get("evidence_run"), runtime_status=asset["status"], ancestry=ancestry)
        if all_candidates:
            row.update(all_ancestor_bindings=inherited_bindings, declared_scope_review=asset.get("scope_review"),
                declared_evidence_ledger=asset.get("evidence_ledger"))
        if entry is not None:
            row.update(native_router_class=entry["target_class"].get_path_name(), inherited_router=entry["target_class"] != cls,
                default_profile=entry["default_profile"], mixin_set=entry["mixin_set"].get_path_name() if entry.get("mixin_set") else None,
                routed_functions=sorted(entry["functions"]))
            for profile, binding in entry["profiles"].items():
                python_cls = binding["python_class"]
                row["profiles"][profile] = dict(python_class=python_cls.__module__+"."+python_cls.__qualname__,
                                               functions=sorted(binding["functions"]))
            selected_profile = str(ue.get_mixin_profile(cls.get_cdo())) if all_candidates else entry["default_profile"]
            if all_candidates: row["effective_cdo_profile"] = selected_profile
            default = row["profiles"].get(selected_profile)
            row["unimplemented_union_methods"] = sorted(set(entry["functions"])-set(default["functions"])) if default else sorted(entry["functions"])
        row["staged_wired_entries"] = wired_entries(name, row["profiles"].get(row.get("effective_cdo_profile", row.get("default_profile")), {}).get("functions", []), all_candidates)
        if all_candidates:
            bridges = []
            for graph in row["staged_wired_entries"]:
                for call in graph["call_targets"]:
                    for target in dict.fromkeys((call["owner_class"], call["default_target_class"])):
                        binding = routers.get(target)
                        if binding is not None and call["method"] in binding["functions"]:
                            bridges.append(dict(entry=graph["entry"], method=call["method"], target=target,
                                default_profile=binding["default_profile"],
                                profiles={profile:dict(python_class=value["python_class"].__module__+"."+value["python_class"].__qualname__,
                                    functions=sorted(value["functions"])) for profile, value in binding["profiles"].items()}))
            row["typed_dispatch_bridges"] = bridges
        rows.append(row)
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("coverage audit input changed")
    return dict(status="passed", runtime_acceptance=False, full_acceptance=False, assets_saved_or_compiled=False,
        coverage_is_registration_not_gameplay=True, all_original_candidates=all_candidates,
        current_versions=list(dict.fromkeys(asset["version"] for asset in selected)), assets=rows,
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
