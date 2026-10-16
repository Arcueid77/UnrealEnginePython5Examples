"""Configure example-owned Dash UI; only ownership/cleanup BP plumbing added."""

import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import (Blueprint, DataAssetFactory, UEPPythonMixinSet,
                                  K2Node_CreateDelegate, K2Node_RemoveDelegate, K2Node_Self)
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_dash_cooldown_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass generator to Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

ASSET = "/ShooterCore/Game/Dash/W_DashCooldown.W_DashCooldown"
PROXY, RESUME = "UEPOriginalDashProxy", "UEPResumeDashObservation"
CLEANUP = "UEPRemoveOriginalDashDeathBinding"


def argument(name):
    return next((arg[len(name) + 2:] for arg in sys.argv if arg.startswith("-" + name + "=")), None)


def connect(source, source_pin, target, target_pin):
    source.node_find_pin(source_pin).connect(target.node_find_pin(target_pin))


def configure_ownership(bp):
    if PROXY not in {str(variable.VarName) for variable in bp.NewVariables}:
        ue.blueprint_add_member_variable(bp, PROXY, EdGraphPinType(
            PinCategory="object", PinSubCategoryObject=ue.find_class("AsyncAction_ListenForGameplayMessage")))
        ue.compile_blueprint(bp)
        actions = [node for graph in bp.UbergraphPages for node in graph.Nodes
                   if node.get_class().get_name() == "K2Node_AsyncAction_ListenForGameplayMessages"]
        if len(actions) != 1 or actions[0].node_find_pin("then").get_linked_to():
            raise RuntimeError("Dash original listener topology differs")
        graph, action = bp.UbergraphPages[0], actions[0]
        setter = graph.graph_add_node_variable_set(PROXY)
        connect(action, "then", setter, "execute")
        connect(action, "AsyncTaskProxy", setter, PROXY)
    if RESUME not in {graph.get_name() for graph in bp.FunctionGraphs}:
        ue.blueprint_add_function(bp, RESUME)
    existing = [graph for graph in bp.FunctionGraphs if graph.get_name() == CLEANUP]
    if existing:
        if len(existing) != 1 or len(existing[0].Nodes) != 4:
            raise RuntimeError("Dash cleanup transport differs")
        return existing[0]
    original = next(node for graph in bp.UbergraphPages for node in graph.Nodes if node.is_a(K2Node_RemoveDelegate))
    graph = ue.blueprint_add_function(bp, CLEANUP)
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("LyraHealthComponent")), "Health")
    remove = graph.graph_add_node(K2Node_RemoveDelegate)
    remove.DelegateReference = original.DelegateReference
    graph.graph_reconstruct_node(remove)
    delegate, owner = graph.graph_add_node(K2Node_CreateDelegate), graph.graph_add_node(K2Node_Self)
    connect(entry, "then", remove, "execute")
    connect(entry, "Health", remove, "self")
    connect(owner, "self", delegate, "self")
    connect(delegate, "OutputDelegate", remove, "Delegate")
    delegate.SelectedFunctionName = "OnDeathStarted"
    return graph


def generate():
    stage = require_authoring_stage(argument("UEPDashStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference_root = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = reference_root / "Plugins/GameFeatures/ShooterCore/Content/Game/Dash/W_DashCooldown.uasset"
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    adapter_bp = ue.load_object(Blueprint, "/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages")
    if not {"ReadDuration", "BroadcastDuration"}.issubset({graph.get_name() for graph in adapter_bp.FunctionGraphs}):
        raise RuntimeError("accepted duration adapter required")
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, ASSET)
    ue.unregister_all_mixins()
    helper = configure_ownership(bp)
    if "PythonMessageAdapterClass" not in {str(variable.VarName) for variable in bp.NewVariables}:
        ue.blueprint_add_member_variable(bp, "PythonMessageAdapterClass", EdGraphPinType(
            PinCategory="class", PinSubCategoryObject=ue.find_class("Object")))
    ue.compile_blueprint(bp)
    name = "DA_W_DashCooldownMixin"
    mixin = ue.find_asset("/Game/UEPMixins/" + name + "." + name)
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.dash_cooldown_mixin", PythonClass=cls)
                      for profile, cls in (("Python", "LyraDashCooldownPythonProfile"),
                                           ("BlueprintFallback", "LyraDashCooldownBlueprintFallbackProfile"))]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.unregister_all_mixins()
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    cdo.PythonMessageAdapterClass = adapter_bp.GeneratedClass
    if int(bp.Status) == 2 or cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
        raise RuntimeError("Dash Interface/CDO postcondition differs")
    if not cdo.bHasScriptImplementedTick or bp.GeneratedClass.get_name() != "W_DashCooldown_C":
        raise RuntimeError("Dash class or original Tick changed")
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != digest:
        raise RuntimeError("official Dash asset changed")
    return {"status": "passed", "class_preserved": True, "reference_sha256": digest,
            "original_proxy_stored": True, "explicit_resume": RESUME,
            "cleanup_nodes": len(helper.Nodes), "cleanup_business_logic": False,
            "existing_transport_reused": True, "runtime_acceptance": False}


result = argument("UEPGenerateDashResult")
if result is None:
    raise RuntimeError("UEPGenerateDashResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_DASH_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
