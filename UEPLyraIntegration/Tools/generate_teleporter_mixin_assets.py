"""Keep original teleporter type/graphs behind five fail-closed policy gates."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "generate_teleporter_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import make_gate, insert_gate, semantics

PREFIX = "UEPDispatchTeleporter"


def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))


def one(values):
    if len(values) != 1:
        raise RuntimeError("one teleporter graph/entry required")
    return values[0]


def generate():
    stage = require_authoring_stage(arg("UEPTeleporterStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    path = reference/"Plugins/GameFeatures/ShooterCore/Content/Blueprint/B_Teleport.uasset"
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, "/ShooterCore/Blueprint/B_Teleport.B_Teleport")
    cls_name = bp.GeneratedClass.get_name()
    signatures = {n: ue.describe_function(bp.GeneratedClass, n) for n in
        ("Set Teleporter Destination", "Teleport Audio for Pawn", "Teleport Audio for Grenade", "UserConstructionScript")}
    graphs = list(bp.FunctionGraphs)+list(bp.UbergraphPages)+list(bp.MacroGraphs)
    cs = one([g for g in graphs if g.get_name() == "UserConstructionScript"])
    event = one([g for g in graphs if g.get_name() == "EventGraph"])
    dest = one([g for g in graphs if g.get_name() == "Set Teleporter Destination"])
    parent_call = one([n for n in cs.Nodes if n.get_class().get_name() == "K2Node_CallParentFunction"])
    begin = one([n for n in event.Nodes if n.get_class().get_name() == "K2Node_ComponentBoundEvent"])
    audio = [n for n in event.Nodes if n.get_class().get_name() == "K2Node_CustomEvent"]
    pawn = one([n for n in audio if str(n.CustomFunctionName) == "Teleport Audio for Pawn"])
    grenade = one([n for n in audio if str(n.CustomFunctionName) == "Teleport Audio for Grenade"])
    hooks = ((cs, parent_call, "Construction", None, None),
             (dest, dest.Nodes[0], "Destination", None, None),
             (event, begin, "Begin", "OtherActor", "OtherActor"),
             (event, pawn, "PawnAudio", "AudioLocation", "Audio Location"),
             (event, grenade, "GrenadeAudio", "AudioLocation", "Audio Location"))
    for graph, entry, suffix, parameter, source in hooks:
        make_gate(bp, PREFIX+suffix, parameter, entry.node_find_pin(source) if source else None)
    ue.compile_blueprint(bp)
    groups = {g.get_name(): dict(graph=g, names={n.get_name() for n in g.Nodes}, ignored=set()) for g in graphs}
    for graph, entry, suffix, parameter, source in hooks:
        groups[graph.get_name()]["ignored"].add((entry.get_name(), "then"))
    for row in groups.values():
        row["before"] = semantics(row["graph"], row["names"], row["ignored"])
    for graph, entry, suffix, parameter, source in hooks:
        insert_gate(graph, entry, "then", getattr(bp.GeneratedClass, PREFIX+suffix), parameter, source)
    set_path = "/Game/UEPMixins/DA_TeleporterMixin"
    if ue.find_asset(set_path+".DA_TeleporterMixin") is not None:
        raise RuntimeError("fresh teleporter authoring required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset("DA_TeleporterMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=p, PythonModule="uep_lyra_world.teleporter_mixin",
        PythonClass="LyraTeleporter"+p+"Profile") for p in ("Python", "BlueprintFallback")]
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.unregister_all_mixins(); ue.compile_blueprint(bp)
    if int(bp.Status) == 2 or bp.GeneratedClass.get_name() != cls_name or bp.GeneratedClass.get_cdo().GetPythonMixinSet() != mixin:
        raise RuntimeError("teleporter original class/Set failed")
    if bp.GeneratedClass.get_cdo().get_property("bReplicates"):
        raise RuntimeError("original teleporter replication flag changed")
    if any(ue.describe_function(bp.GeneratedClass, n) != signature for n, signature in signatures.items()):
        raise RuntimeError("original teleporter signature/flags changed")
    proofs = []
    for name, row in groups.items():
        current = one([g for g in ue.blueprint_get_all_graphs(bp) if g.get_name() == name])
        if semantics(current, row["names"], row["ignored"]) != row["before"]:
            raise RuntimeError("teleporter original graph changed: "+name)
        proofs.append(dict(graph=name, original_semantic_digest=row["before"], dispatch_transport_endpoints=sorted(row["ignored"])))
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(path.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("official teleporter changed")
    return dict(status="passed", runtime_acceptance=False, class_preserved=True, single_parent_interface_set=True,
        original_blocks_retained=True, gate_count=5, original_graphs=proofs,
        original_replication_flag_preserved=True, original_signatures_preserved=True,
        exception_defaults_to_no_original=True, reference_hashes={str(path): original_hash})


try:
    report = generate()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPGenerateTeleporterResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_TELEPORTER_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
