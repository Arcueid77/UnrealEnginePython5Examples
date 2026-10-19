"""Retain the static GeneralAudio ABI and eight original nodes behind one typed gate."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_weapon_audio_math_assets import kind,renamed
from generate_dash_selector_assets import snapshot
from message_payload_graphs import connect
from mixin_graph_gates import semantics
from uep_lyra_audio.general_audio_mixin import CLASS,METHOD

PACKAGE="/Game/Audio/Blueprints/GeneralAudioFunctions.GeneralAudioFunctions"
RELATIVE="Content/Audio/Blueprints/GeneralAudioFunctions.uasset"
HELPER="Content/UEPMixins/BP_GeneralAudioRouter.uasset"
SET="Content/UEPMixins/DA_GeneralAudioMixin.uasset"
PROBE="Content/UEPValidation/BP_GeneralAudioCaller.uasset"


def generate(stage):
    marker=json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"));original=Path(marker["source"]).parent/RELATIVE;digest=hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest or any((stage/path).exists() for path in (HELPER,SET,PROBE)):raise RuntimeError("fresh original GeneralAudio/router/Set/caller required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"general-audio-before");signature=ue.describe_function(bp.GeneratedClass,"FireStinger")
    if not signature["flags"]&0x2000:raise RuntimeError("original static flag missing")
    graph,=ue.blueprint_get_all_graphs(bp);names={n.get_name() for n in graph.Nodes}
    if len(names)!=8:raise RuntimeError("original GeneralAudio footprint differs")
    entry,=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_FunctionEntry"];first,=entry.node_find_pin("then").get_linked_to();ignored={(entry.get_name(),"then"),(first.owning_node.get_name(),first.name)};before_graph=semantics(graph,names,ignored)
    helper=ue.create_blueprint(ue.find_class("Object"),CLASS.split(".")[0]);route=ue.blueprint_add_function(helper,METHOD);route_entry=route.Nodes[0];result=route.graph_add_node(K2Node_FunctionResult)
    for pin in entry.node_pins():
        if pin.category not in ("exec","delegate"):route_entry.node_create_pin(1,kind(pin),renamed(pin.name))
    result.node_create_pin(0,EdGraphPinType(PinCategory="bool"),"UseOriginal");result.node_find_pin("UseOriginal").default_value="true";connect(route_entry,"then",result,"execute")
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;mixin=ue.create_asset("DA_GeneralAudioMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_audio.general_audio_mixin",PythonClass="LyraGeneralAudio"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(helper,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(helper);ue.unregister_all_mixins()
    if int(helper.Status)==2:raise RuntimeError("typed GeneralAudio helper compile failed")
    call=graph.graph_add_node_call_function(getattr(helper.GeneratedClass,METHOD));call.node_find_pin("self").default_object=helper.GeneratedClass.get_cdo();branch=graph.graph_add_node(K2Node_IfThenElse);ret=graph.graph_add_node(K2Node_FunctionResult)
    entry.node_find_pin("then").break_link_to(first);connect(entry,"then",call,"execute");connect(call,"then",branch,"execute");connect(call,"UseOriginal",branch,"Condition");branch.node_find_pin("then").make_link_to(first);connect(branch,"else",ret,"execute")
    for pin in entry.node_pins():
        if pin.category not in ("exec","delegate"):connect(entry,pin.name,call,renamed(pin.name))
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,"general-audio-after")!=before or ue.describe_function(bp.GeneratedClass,"FireStinger")!=signature or semantics(graph,names,ignored)!=before_graph or len(graph.Nodes)!=11:raise RuntimeError("GeneralAudio CDO/ABI/original graph changed")
    try:
        ue.register_declared_mixin(helper.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==helper.GeneratedClass];counts={name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts!=dict(Python=1,BlueprintFallback=1):raise RuntimeError("one ordinary helper method/Profile required")
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class("Object"),"/Game/UEPValidation/BP_GeneralAudioCaller");g=ue.blueprint_add_function(probe,"CallStinger");e=g.Nodes[0];c=g.graph_add_node_call_function(bp.GeneratedClass.FireStinger);r=g.graph_add_node(K2Node_FunctionResult)
    for pin in c.node_pins():
        if pin.category not in ("exec","delegate") and pin.name!="self":e.node_create_pin(1,kind(pin),renamed(pin.name));connect(e,renamed(pin.name),c,pin.name)
    connect(e,"then",c,"execute");connect(c,"then",r,"execute");ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError("GeneralAudio static Blueprint caller failed")
    for asset in (bp,helper,mixin,probe):asset.save_package()
    return dict(status="passed",kind="generalaudio",runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdo_preserved=True,original_static_signature_flags_preserved=True,original_business_graph_preserved_with_dispatch=True,original_graph_nodes=8,
        transport_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,static_functions_registered_as_mixins=False,actual_registered_profile_method_counts=counts,
        caller_probe=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=[RELATIVE,HELPER,SET])
