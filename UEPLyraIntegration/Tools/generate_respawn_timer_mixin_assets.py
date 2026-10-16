"""Configure the example-owned respawn UI and exact animation-delegate cleanup."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_CreateDelegate, K2Node_Self
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_respawn_timer_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass generator to Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

ASSET = "/ShooterCore/Game/Respawn/W_RespawnTimer.W_RespawnTimer"
RESUME, CLEANUP = "UEPResumeRespawnObservation", "UEPRemoveOriginalRespawnAnimationBinding"
SOUND = "/Game/Audio/MetaSounds/sfx_Character_RespawnTimer_meta.sfx_Character_RespawnTimer_meta"


def argument(name):
    return next((arg[len(name)+2:] for arg in sys.argv if arg.startswith("-"+name+"=")), None)


def connect(source, source_pin, target, target_pin):
    source.node_find_pin(source_pin).connect(target.node_find_pin(target_pin))


def generate():
    stage = require_authoring_stage(argument("UEPRespawnStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference_root = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = reference_root / "Plugins/GameFeatures/ShooterCore/Content/Game/Respawn/W_RespawnTimer.uasset"
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    adapter = ue.load_object(Blueprint, "/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages")
    if not {"ReadDuration", "ReadVerb", "BroadcastDuration", "BroadcastVerb"}.issubset({graph.get_name() for graph in adapter.FunctionGraphs}):
        raise RuntimeError("accepted duration/verb adapter required")
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, ASSET)
    ue.unregister_all_mixins()
    if RESUME not in {graph.get_name() for graph in bp.FunctionGraphs}:
        ue.blueprint_add_function(bp, RESUME)
    graphs = [graph for graph in bp.FunctionGraphs if graph.get_name() == CLEANUP]
    if not graphs:
        graph = ue.blueprint_add_function(bp, CLEANUP)
        entry = graph.Nodes[0]
        owner = graph.graph_add_node(K2Node_Self)
        animation = graph.graph_add_node_variable_get("Outro")
        remove = graph.graph_add_node_call_function(ue.find_class("UserWidget").UnbindFromAnimationFinished)
        delegate = graph.graph_add_node(K2Node_CreateDelegate)
        connect(entry, "then", remove, "execute")
        connect(owner, "self", remove, "self")
        connect(owner, "self", delegate, "self")
        connect(animation, "Outro", remove, "Animation")
        connect(delegate, "OutputDelegate", remove, "Delegate")
        delegate.SelectedFunctionName = "OnTimerFinished"
        graphs = [graph]
    if len(graphs) != 1 or len(graphs[0].Nodes) != 5:
        raise RuntimeError("respawn cleanup graph differs")
    variables = {str(variable.VarName) for variable in bp.NewVariables}
    for name, category, cls in (("PythonMessageAdapterClass", "class", "Object"), ("PythonCountdownSound", "object", "SoundBase")):
        if name not in variables:
            ue.blueprint_add_member_variable(bp, name, EdGraphPinType(PinCategory=category, PinSubCategoryObject=ue.find_class(cls)))
    ue.compile_blueprint(bp)
    name = "DA_W_RespawnTimerMixin"
    mixin = ue.find_asset("/Game/UEPMixins/"+name+"."+name)
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.respawn_timer_mixin", PythonClass=cls)
                      for profile, cls in (("Python", "LyraRespawnTimerPythonProfile"), ("BlueprintFallback", "LyraRespawnTimerBlueprintFallbackProfile"))]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.unregister_all_mixins()
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    cdo.PythonMessageAdapterClass = adapter.GeneratedClass
    cdo.PythonCountdownSound = ue.load_object(ue.find_class("SoundBase"), SOUND)
    if int(bp.Status) == 2 or cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python" or cdo.PythonCountdownSound is None:
        raise RuntimeError("respawn Interface/CDO postcondition differs")
    if bp.GeneratedClass.get_name() != "W_RespawnTimer_C":
        raise RuntimeError("respawn class changed")
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != digest:
        raise RuntimeError("official respawn asset changed")
    return {"status": "passed", "class_preserved": True, "reference_sha256": digest,
            "original_proxy_stored": all(cdo.has_property(name) for name in ("RespawnDurationAsyncAction", "RespawnCompletedAsyncAction")),
            "explicit_resume": RESUME, "cleanup_nodes": 5, "cleanup_business_logic": False,
            "existing_transport_reused": True, "runtime_acceptance": False}


result = argument("UEPGenerateRespawnResult")
if result is None:
    raise RuntimeError("UEPGenerateRespawnResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_RESPAWN_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
