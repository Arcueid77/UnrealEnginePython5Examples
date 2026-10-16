"""Retain launcher types/old BP blocks behind one parent Mixin Set."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_FunctionResult, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "generate_launcher_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import make_gate, insert_gate, semantics

NAMES = ("B_Launcher", "B_Launcher_Push", "B_Launcher_Up")
PREFIX = "UEPDispatchLauncher"

def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))

def one(values):
    if len(values) != 1:
        raise RuntimeError("expected exactly one launcher graph/entry")
    return values[0]

def graph(bp, name):
    return one([g for g in bp.FunctionGraphs if g.get_name() == name])

def return_gate(parent, name):
    # -1 is ONLY the explicit native fallback. 0/1 are Python false/true.
    # An exception's zero-initialized result cannot run original BP business.
    g = ue.blueprint_add_function(parent, name)
    result = g.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="int"), "ReturnValue")
    result.node_find_pin("ReturnValue").default_value = "-1"
    g.Nodes[0].node_find_pin("then").make_link_to(result.node_find_pin("execute"))

def insert_return_gate(g, parent, name):
    entry = one([n for n in g.Nodes if n.get_class().get_name() == "K2Node_FunctionEntry"])
    result = one([n for n in g.Nodes if n.get_class().get_name() == "K2Node_FunctionResult"])
    previous = entry.node_find_pin("then").get_linked_to()
    if len(previous) > 1:
        raise RuntimeError("ambiguous original launcher Overlap")
    original = previous[0] if previous else result.node_find_pin("execute")
    if previous:
        entry.node_find_pin("then").break_link_to(original)
    call = g.graph_add_node_call_function(getattr(parent.GeneratedClass, name))
    equal = g.graph_add_node_call_function(ue.find_class("KismetMathLibrary").EqualEqual_IntInt)
    positive = g.graph_add_node_call_function(ue.find_class("KismetMathLibrary").Greater_IntInt)
    branch = g.graph_add_node(K2Node_IfThenElse)
    select = g.graph_add_node_call_function(ue.find_class("KismetMathLibrary").BooleanAND)
    merged = g.graph_add_node_call_function(ue.find_class("KismetMathLibrary").BooleanOR)
    # Reuse the original terminator/signature. Adding an editable result node
    # can mutate a user-defined BP output shared with inherited overrides.
    output = result.node_find_pin("Return")
    sources = output.get_linked_to()
    if len(sources) > 1:
        raise RuntimeError("ambiguous original launcher return")
    if sources:
        output.break_link_to(sources[0])
        sources[0].make_link_to(select.node_find_pin("A"))
    else:
        select.node_find_pin("A").default_value = output.default_value
    entry.node_find_pin("then").make_link_to(call.node_find_pin("execute"))
    call.node_find_pin("then").make_link_to(branch.node_find_pin("execute"))
    call.node_find_pin("ReturnValue").make_link_to(equal.node_find_pin("A"))
    equal.node_find_pin("B").default_value = "-1"
    equal.node_find_pin("ReturnValue").make_link_to(branch.node_find_pin("Condition"))
    equal.node_find_pin("ReturnValue").make_link_to(select.node_find_pin("B"))
    branch.node_find_pin("then").make_link_to(original)
    branch.node_find_pin("else").make_link_to(result.node_find_pin("execute"))
    call.node_find_pin("ReturnValue").make_link_to(positive.node_find_pin("A"))
    positive.node_find_pin("B").default_value = "0"
    positive.node_find_pin("ReturnValue").make_link_to(merged.node_find_pin("B"))
    select.node_find_pin("ReturnValue").make_link_to(merged.node_find_pin("A"))
    merged.node_find_pin("ReturnValue").make_link_to(output)
    for offset, node in enumerate((call, equal, branch, positive, select, merged), 1):
        node.NodePosX, node.NodePosY = entry.NodePosX+offset*240, entry.NodePosY+200

def generate():
    stage = require_authoring_stage(arg("UEPLauncherStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes = {str(reference/"Plugins/GameFeatures/ShooterCore/Content/Blueprint"/(name+".uasset")):
        hashlib.sha256((reference/"Plugins/GameFeatures/ShooterCore/Content/Blueprint"/(name+".uasset")).read_bytes()).hexdigest() for name in NAMES}
    ue.unregister_all_mixins()
    bps = [ue.load_object(Blueprint, "/ShooterCore/Blueprint/"+n+"."+n) for n in NAMES]
    parent, push, up = bps
    class_names = [bp.GeneratedClass.get_name() for bp in bps]
    rpc_signature = ue.describe_function(parent.GeneratedClass, "Activate VFX")
    event = parent.UbergraphPages[0]
    begin = one([n for n in event.Nodes if n.get_class().get_name() == "K2Node_ComponentBoundEvent"])
    cue = one([n for n in event.Nodes if n.get_class().get_name() == "K2Node_CustomEvent"])
    parent_cs, push_cs = graph(parent, "UserConstructionScript"), graph(push, "UserConstructionScript")
    push_parent_call = one([n for n in push_cs.Nodes if n.get_class().get_name() == "K2Node_CallParentFunction"])
    hooks = ((parent_cs, parent_cs.Nodes[0], "Construction", None),
        (push_cs, push_parent_call, "PushConstruction", None),
        (event, begin, "Begin", "OtherActor"), (event, cue, "Cue", None))
    for g, entry, suffix, parameter in hooks:
        make_gate(parent, PREFIX+suffix, parameter, entry.node_find_pin(parameter) if parameter else None)
    for kind in ("Parent", "Push", "Up"):
        return_gate(parent, PREFIX+kind+"Overlap")
    ue.compile_blueprint(parent)
    groups = {}
    for bp in bps:
        for g in list(bp.FunctionGraphs)+list(bp.UbergraphPages):
            if g.get_name() not in ("UserConstructionScript", "Overlap", "EventGraph") or not g.Nodes:
                continue
            key = (bp.get_path_name(), g.get_name())
            groups[key] = {"graph": g, "names": {n.get_name() for n in g.Nodes}, "ignored": set()}
    # Up's empty EventGraph is not business; keep its parent Construction call.
    for g, entry, suffix, parameter in hooks:
        key = next(k for k,v in groups.items() if v["graph"] == g)
        groups[key]["ignored"].add((entry.get_name(), "then"))
    for bp in bps:
        g = graph(bp, "Overlap")
        entry = one([n for n in g.Nodes if n.get_class().get_name() == "K2Node_FunctionEntry"])
        groups[(bp.get_path_name(), "Overlap")]["ignored"].add((entry.get_name(), "then"))
        result = one([n for n in g.Nodes if n.get_class().get_name() == "K2Node_FunctionResult"])
        groups[(bp.get_path_name(), "Overlap")]["ignored"].add((result.get_name(), "Return"))
    for row in groups.values():
        row["before"] = semantics(row["graph"], row["names"], row["ignored"])
    for g, entry, suffix, parameter in hooks:
        insert_gate(g, entry, "then", getattr(parent.GeneratedClass, PREFIX+suffix), parameter, parameter)
    for bp, kind in zip(bps, ("Parent", "Push", "Up")):
        insert_return_gate(graph(bp, "Overlap"), parent, PREFIX+kind+"Overlap")
    set_path = "/Game/UEPMixins/DA_LauncherMixin"
    if ue.find_asset(set_path+".DA_LauncherMixin") is not None:
        raise RuntimeError("fresh launcher authoring required")
    factory = DataAssetFactory();factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset("DA_LauncherMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=p, PythonModule="uep_lyra_world.launcher_mixin",
        PythonClass="LyraLauncher"+p+"Profile") for p in ("Python", "BlueprintFallback")]
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(parent, mixin, "Python", "PythonMixinProfile")
    for bp, expected in zip(bps, class_names):
        ue.unregister_all_mixins();ue.compile_blueprint(bp)
        if int(bp.Status) == 2 or bp.GeneratedClass.get_name() != expected or bp.GeneratedClass.get_cdo().GetPythonMixinSet() != mixin:
            raise RuntimeError("launcher retained class/inherited Set failed")
        if bp.GeneratedClass.get_cdo().get_property("bReplicates"):
            raise RuntimeError("original launcher replication flag changed")
    if ue.describe_function(parent.GeneratedClass, "Activate VFX") != rpc_signature:
        raise RuntimeError("launcher multicast signature/flags changed")
    proofs = []
    for (asset, name), row in groups.items():
        bp = one([bp for bp in bps if bp.get_path_name() == asset])
        current = one([g for g in ue.blueprint_get_all_graphs(bp) if g.get_name() == name])
        if semantics(current, row["names"], row["ignored"]) != row["before"]:
            raise RuntimeError("launcher original business graph changed: "+asset+"/"+name)
        proofs.append({"asset": asset, "graph": name, "original_semantic_digest": row["before"],
                       "dispatch_transport_endpoints": sorted(row["ignored"])})
    for bp in bps+[mixin]:
        bp.save_package()
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("official launcher changed")
    return {"status": "passed", "runtime_acceptance": False, "class_preserved": True,
        "single_parent_interface_set": True, "original_blocks_retained": True, "gate_count": 7,
        "original_graphs": proofs, "rpc_signature": rpc_signature, "original_replication_flag_preserved": True,
        "exception_defaults_to_no_original": True, "reference_hashes": hashes}

try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(arg("UEPGenerateLauncherResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_LAUNCHER_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
