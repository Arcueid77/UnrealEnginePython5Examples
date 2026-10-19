"""Configure five base music methods without changing original graphs/listeners."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_weapon_audio_math_assets import kind
from message_payload_graphs import connect
from mixin_graph_gates import semantics
from uep_lyra_audio.music_manager_mixin import CLASS,METHODS

RELATIVE="Content/Audio/Blueprints/B_MusicManagerComponent_Base.uasset"
SET="Content/UEPMixins/DA_MusicManagerMixin.uasset"
PROBE="Content/UEPValidation/BP_MusicManagerCaller.uasset"
CHILDREN={
    "front_end":("/Game/Audio/Blueprints/B_MusicManagerComponent_FE.B_MusicManagerComponent_FE","Content/Audio/Blueprints/B_MusicManagerComponent_FE.uasset"),
    "elimination":("/ShooterCore/Elimination/B_MusicManagerComponent_Elimination.B_MusicManagerComponent_Elimination","Plugins/GameFeatures/ShooterCore/Content/Elimination/B_MusicManagerComponent_Elimination.uasset"),
    "control_point":("/ShooterCore/ControlPoint/B_MusicManagerComponent_ControlPoint.B_MusicManagerComponent_ControlPoint","Plugins/GameFeatures/ShooterCore/Content/ControlPoint/B_MusicManagerComponent_ControlPoint.uasset")}


def generate(stage):
    official=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE;digest=hashlib.sha256(official.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest or (stage/SET).exists() or (stage/PROBE).exists():raise RuntimeError("fresh original music-manager base/Set/caller required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.rsplit("_C",1)[0]);ue.unregister_all_mixins()
    before=snapshot(bp,"music-controls-before");class_name=bp.GeneratedClass.get_path_name();graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    if sum(len(names) for _,names in graphs)!=99:raise RuntimeError("original music graph footprint differs")
    hashes={g.get_name():semantics(g,names,set()) for g,names in graphs};signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in (*METHODS,"ReceiveBeginPlay")}
    children={};child_signatures={};child_defaults={};child_hashes={}
    for label,(package,relative) in CHILDREN.items():
        child=ue.load_object(Blueprint,package);ue.unregister_all_mixins();children[label]=child;child_defaults[label]=snapshot(child,"music-child-"+label+"-before")
        child_signatures[label]={name:ue.describe_function(child.GeneratedClass,name) for name in signatures};child_hashes[relative]=hashlib.sha256((stage/relative).read_bytes()).hexdigest()
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_MusicManagerMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_audio.music_manager_mixin",PythonClass="LyraMusicManager"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=class_name or snapshot(bp,"music-controls-after")!=before:raise RuntimeError("original base full CDO/class changed")
    if any(ue.describe_function(bp.GeneratedClass,name)!=sig for name,sig in signatures.items()) or any(semantics(g,names,set())!=hashes[g.get_name()] for g,names in graphs):raise RuntimeError("original music graph/signature/listener wiring changed")
    for label,child in children.items():
        if snapshot(child,"music-child-"+label+"-after")!=child_defaults[label] or any(ue.describe_function(child.GeneratedClass,name)!=sig for name,sig in child_signatures[label].items()):raise RuntimeError("music descendant defaults/signatures changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts!=dict(Python=5,BlueprintFallback=5):raise RuntimeError("five music methods/Profile required")
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class("Object"),"/Game/UEPValidation/BP_MusicManagerCaller")
    for index,name in enumerate(METHODS):
        if name=="ReceiveTick":continue
        graph=ue.blueprint_add_function(probe,"Call"+str(index));entry=graph.Nodes[0]
        call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,name));result=graph.graph_add_node(K2Node_FunctionResult)
        entry.node_create_pin(1,kind(call.node_find_pin("self")),"Target");connect(entry,"Target",call,"self")
        for pin in call.node_pins():
            if pin.category in ("exec","delegate") or pin.name=="self":continue
            if pin.direction!=0:raise RuntimeError("void music function gained output")
            entry.node_create_pin(1,kind(pin),pin.name);connect(entry,pin.name,call,pin.name)
        connect(entry,"then",call,"execute");connect(call,"then",result,"execute")
    ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError("music-manager typed Blueprint caller failed")
    bp.save_package();mixin.save_package();probe.save_package()
    if any(hashlib.sha256((stage/relative).read_bytes()).hexdigest()!=value for relative,value in child_hashes.items()):raise RuntimeError("music child asset bytes changed")
    return dict(status="passed",kind="musiccontrols",runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdo_preserved=True,original_graphs_unmodified=True,original_graph_nodes=99,original_begin_play_listeners_preserved=True,
        child_cdos_signatures_and_asset_bytes_preserved=True,actual_registered_profile_method_counts=counts,native_end_adapter_nodes=0,transport_nodes=0,new_business_nodes=0,
        implemented_methods=list(METHODS),remaining_methods=["ReceiveBeginPlay"],original_graphs=hashes,signatures=signatures,child_asset_hashes=child_hashes,
        caller_probe=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest(),callable_methods=4,tick_is_native_event_not_blueprint_callable=True),assets=[RELATIVE,SET])
