"""Configure the example-owned nameplate; typed delegates, not BP policy."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import (Blueprint, DataAssetFactory, UEPPythonMixinSet,
                                  K2Node_CreateDelegate, K2Node_RemoveDelegate, K2Node_Self)
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_nameplate_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass generator to Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import connect

ASSET = "/Game/UI/Indicators/W_Nameplate.W_Nameplate"
PROXY = "UEPOriginalNameplateTeamProxy"
RESUME = "UEPResumeNameplateObservation"
INIT_BIND = "UEPRegisterNameplateInitState"
INIT_UNBIND = "UEPUnregisterNameplateInitState"
HEALTH_CLEANUP = "UEPRemoveOriginalNameplateHealthBindings"


def argument(name):
    return next((arg[len(name)+2:] for arg in sys.argv if arg.startswith("-"+name+"=")), None)


def init_state_graph(bp, name, binding):
    existing = [graph for graph in bp.FunctionGraphs if graph.get_name() == name]
    if existing:
        if len(existing) != 1 or len(existing[0].Nodes) != 4:
            raise RuntimeError("nameplate init-state transport differs")
        return existing[0]
    graph = ue.blueprint_add_function(bp, name)
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("LyraPawnExtensionComponent")), "Extension")
    function = "RegisterAndCallForInitStateChange" if binding else "UnregisterInitStateDelegate"
    call = graph.graph_add_node_call_function(getattr(ue.find_class("GameFrameworkInitStateInterface"), function))
    owner = graph.graph_add_node(K2Node_Self)
    delegate = graph.graph_add_node(K2Node_CreateDelegate)
    connect(entry, "then", call, "execute")
    connect(entry, "Extension", call, "self")
    connect(owner, "self", delegate, "self")
    connect(delegate, "OutputDelegate", call, "Delegate")
    delegate.SelectedFunctionName = "PawnReadyEvent"
    if binding:
        call.node_find_pin("RequiredState").default_value = '(TagName="InitState.GameplayReady")'
        call.node_find_pin("bCallImmediately").default_value = "true"
    return graph


def health_cleanup(bp):
    existing = [graph for graph in bp.FunctionGraphs if graph.get_name() == HEALTH_CLEANUP]
    if existing:
        if len(existing) != 1 or len(existing[0].Nodes) != 6:
            raise RuntimeError("nameplate original health transport differs")
        return existing[0]
    original = [node for graph in bp.UbergraphPages for node in graph.Nodes if node.is_a(K2Node_RemoveDelegate)]
    if len(original) != 2:
        raise RuntimeError("nameplate original two health delegate removals required")
    graph = ue.blueprint_add_function(bp, HEALTH_CLEANUP)
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("LyraHealthComponent")), "Health")
    owner, previous = graph.graph_add_node(K2Node_Self), entry
    for source in original:
        name = str(source.DelegateReference.MemberName)
        event = {"OnHealthChanged": "Health Changed", "OnDeathStarted": "DeathStarted"}.get(name)
        if event is None:
            raise RuntimeError("unexpected original nameplate delegate: "+name)
        remove = graph.graph_add_node(K2Node_RemoveDelegate)
        remove.DelegateReference = source.DelegateReference
        graph.graph_reconstruct_node(remove)
        delegate = graph.graph_add_node(K2Node_CreateDelegate)
        connect(previous, "then", remove, "execute")
        connect(entry, "Health", remove, "self")
        connect(owner, "self", delegate, "self")
        connect(delegate, "OutputDelegate", remove, "Delegate")
        delegate.SelectedFunctionName = event
        previous = remove
    return graph


def store_original_proxy(bp):
    if PROXY in {str(variable.VarName) for variable in bp.NewVariables}:
        return
    ue.blueprint_add_member_variable(bp, PROXY, EdGraphPinType(
        PinCategory="object", PinSubCategoryObject=ue.find_class("AsyncAction_ObserveTeam")))
    ue.compile_blueprint(bp)
    actions = [node for graph in bp.UbergraphPages for node in graph.Nodes
               if node.get_class().get_name() == "K2Node_AsyncAction" and
               any(pin.name == "OnTeamChanged" for pin in node.node_pins())]
    if len(actions) != 1 or actions[0].node_find_pin("then").get_linked_to():
        raise RuntimeError("original nameplate ObserveTeam proxy topology differs")
    setter = bp.UbergraphPages[0].graph_add_node_variable_set(PROXY)
    connect(actions[0], "then", setter, "execute")
    connect(actions[0], "AsyncTaskProxy", setter, PROXY)


def generate():
    stage = require_authoring_stage(argument("UEPNameplateStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = source/"Content/UI/Indicators/W_Nameplate.uasset"
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, ASSET)
    ue.unregister_all_mixins()
    old_tick = bool(bp.GeneratedClass.get_cdo().bHasScriptImplementedTick)
    store_original_proxy(bp)
    bind, unbind, health = init_state_graph(bp, INIT_BIND, True), init_state_graph(bp, INIT_UNBIND, False), health_cleanup(bp)
    if RESUME not in {graph.get_name() for graph in bp.FunctionGraphs}:
        ue.blueprint_add_function(bp, RESUME)
    ue.compile_blueprint(bp)
    name = "DA_W_NameplateMixin"
    mixin = ue.find_asset("/Game/UEPMixins/"+name+"."+name)
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.nameplate_mixin", PythonClass=cls)
                      for profile, cls in (("Python", "LyraNameplatePythonProfile"), ("BlueprintFallback", "LyraNameplateBlueprintFallbackProfile"))]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.unregister_all_mixins()
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    if int(bp.Status) == 2 or cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
        raise RuntimeError("nameplate Interface/CDO postcondition differs")
    if bp.GeneratedClass.get_name() != "W_Nameplate_C" or bool(cdo.bHasScriptImplementedTick) != old_tick:
        raise RuntimeError("nameplate class/original Tick changed")
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != digest:
        raise RuntimeError("official nameplate changed")
    return {"status": "passed", "class_preserved": True, "reference_sha256": digest,
            "original_widget_tick_retained": True, "original_proxy_stored": True, "explicit_resume": RESUME,
            "init_state_transport_nodes": [len(bind.Nodes), len(unbind.Nodes)], "cleanup_nodes": len(health.Nodes),
            "cleanup_business_logic": False, "existing_transport_reused": True, "runtime_acceptance": False}


result = argument("UEPGenerateNameplateResult")
if result is None:
    raise RuntimeError("UEPGenerateNameplateResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_NAMEPLATE_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
