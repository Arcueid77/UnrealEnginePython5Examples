"""Configure an example-owned reticle host and a four-node VM cleanup helper."""

import hashlib
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import (Blueprint, DataAssetFactory, UEPPythonMixinSet,
                                  K2Node_CreateDelegate, K2Node_RemoveDelegate, K2Node_Self)
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_reticle_host_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass the generator to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

HELPER = "UEPRemoveOriginalDeathBinding"


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


def connect(source, source_pin, target, target_pin):
    source.node_find_pin(source_pin).connect(target.node_find_pin(target_pin))


def cleanup_helper(bp):
    graphs = [graph for graph in bp.FunctionGraphs if graph.get_name() == HELPER]
    if graphs:
        if len(graphs) != 1 or len(graphs[0].Nodes) != 4:
            raise RuntimeError("existing cleanup helper differs")
        return graphs[0]
    original = next(node for graph in bp.UbergraphPages for node in graph.Nodes if node.is_a(K2Node_RemoveDelegate))
    graph = ue.blueprint_add_function(bp, HELPER)
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("LyraHealthComponent")), "Health")
    remove = graph.graph_add_node(K2Node_RemoveDelegate)
    remove.DelegateReference = original.DelegateReference
    graph.graph_reconstruct_node(remove)
    delegate = graph.graph_add_node(K2Node_CreateDelegate)
    owner = graph.graph_add_node(K2Node_Self)
    connect(entry, "then", remove, "execute")
    connect(entry, "Health", remove, "self")
    connect(owner, "self", delegate, "self")
    connect(delegate, "OutputDelegate", remove, "Delegate")
    # CreateDelegate clears its selection while it has no inferred signature.
    # Select only after both object/signature connections are established.
    delegate.SelectedFunctionName = "OnDeathStarted"
    return graph


def generate():
    stage = require_authoring_stage(argument("UEPReticleHostStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = source / "Plugins/GameFeatures/ShooterCore/Content/UserInterface/HUD/W_WeaponReticleHost.uasset"
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, "/ShooterCore/UserInterface/HUD/W_WeaponReticleHost.W_WeaponReticleHost")
    helper = cleanup_helper(bp)
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2:
        raise RuntimeError("native delegate cleanup helper did not compile")
    name = "DA_W_WeaponReticleHostMixin"
    mixin = ue.find_asset("/Game/UEPMixins/" + name + "." + name)
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.reticle_host_mixin", PythonClass=python_class)
                      for profile, python_class in (("Python", "LyraReticleHostPythonProfile"), ("BlueprintFallback", "LyraReticleHostBlueprintFallbackProfile"))]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    if int(bp.Status) == 2 or cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
        raise RuntimeError("reticle host Interface/CDO postcondition differs")
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != digest:
        raise RuntimeError("official reticle host changed")
    return {"status": "passed", "asset": bp.get_path_name(), "class_preserved": bp.GeneratedClass.get_name() == "W_WeaponReticleHost_C",
            "reference_sha256": digest, "cleanup_helper_nodes": len(helper.Nodes), "cleanup_helper_business_logic": False,
            "runtime_acceptance": False}


result = argument("UEPGenerateReticleHostResult")
if result is None:
    raise RuntimeError("UEPGenerateReticleHostResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_RETICLE_HOST_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
