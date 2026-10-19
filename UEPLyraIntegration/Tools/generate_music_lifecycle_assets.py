"""Reuse exact native music listener nodes, adding only typed callback transports."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="generate_music_lifecycle_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect,broadcast_graph
from generate_dash_selector_assets import snapshot
from generate_music_manager_assets import RELATIVE,SET,CHILDREN
from uep_lyra_audio.music_manager_mixin import CLASS
from uep_lyra_audio.music_manager_lifecycle_mixin import START,ELIMINATION,DAMAGE,METHODS

PROBE="Content/UEPValidation/BP_MusicListenerProbe.uasset"
def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))
def generate():
    stage=require_authoring_stage(arg("UEPMusicLifecycleStage"),ue.convert_relative_path_to_full(ue.get_content_dir()));baseline=json.loads(Path(arg("UEPMusicControlsBaseline")).read_text(encoding="utf-8-sig"))
    if baseline["status"]!="passed" or baseline["kind"]!="musiccontrols" or len(baseline["assets"])!=2:raise RuntimeError("accepted music controls baseline required")
    for asset in baseline["assets"]:
        for field in ("stage","overlay"):
            if hashlib.sha256(Path(asset[field]).read_bytes()).hexdigest().lower()!=asset["sha256"].lower():raise RuntimeError("music baseline changed")
    if (stage/PROBE).exists():raise RuntimeError("fresh music listener probe required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.rsplit("_C",1)[0]);ue.unregister_all_mixins();before=snapshot(bp,"music-lifecycle-before")
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in METHODS if name not in (ELIMINATION,DAMAGE)}
    graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];graph=bp.UbergraphPages[0]
    sequence,=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_ExecutionSequence" and n.get_name()=="K2Node_ExecutionSequence_0"]
    actions=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_AsyncAction_ListenForGameplayMessages"]
    if len(actions)!=2:raise RuntimeError("two original music async nodes required")
    ignored={(sequence.get_name(),"execute")};selected=[]
    for action in actions:
        channel=action.node_find_pin("Channel").default_value;gate=ELIMINATION if "Lyra.Elimination.Message" in channel else DAMAGE if "Lyra.Damage.Taken.Message" in channel else None
        if gate is None or action.node_find_pin("MatchType").default_value!="ExactMatch":raise RuntimeError("original exact music channel changed")
        destination,=action.node_find_pin("OnMessageReceived").get_linked_to();ignored.update(((action.get_name(),"OnMessageReceived"),(destination.owning_node.get_name(),destination.name)));selected.append((action,gate,channel))
    hashes={g.get_name():semantics(g,names,ignored if g==graph else set()) for g,names in graphs};old_count=sum(len(names) for _,names in graphs)
    child_hashes={relative:hashlib.sha256((stage/relative).read_bytes()).hexdigest() for _,relative in CHILDREN.values()}
    for action,gate,_ in selected:make_gate(bp,gate,"Payload",action.node_find_pin("Payload"))
    start=graph.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName=START;graph.graph_reconstruct_node(start);connect(start,"then",sequence,"execute")
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for action,gate,_ in selected:
        insert_gate(graph,action,"OnMessageReceived",getattr(bp.GeneratedClass,gate));call,=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_CallFunction" and str(n.FunctionReference.MemberName)==gate]
        connect(action,"Payload",call,"Payload")
    mixin=ue.load_object(ue.find_class("UEPPythonMixinSet"),"/Game/UEPMixins/DA_MusicManagerMixin.DA_MusicManagerMixin")
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_audio.music_manager_lifecycle_mixin",PythonClass="LyraMusicLifecycle"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,"music-lifecycle-after")!=before or any(ue.describe_function(bp.GeneratedClass,name)!=sig for name,sig in signatures.items()):raise RuntimeError("music base CDO/signature/compile changed")
    if any(semantics(g,names,ignored if g==graph else set())!=hashes[g.get_name()] for g,names in graphs):raise RuntimeError("original music graph changed beyond callback/entry endpoints")
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-old_count!=9:raise RuntimeError("music typed transport footprint differs")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==bp.GeneratedClass];counts={name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts!=dict(Python=8,BlueprintFallback=8):raise RuntimeError("complete eight-method music family required")
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class("Object"),"/Game/UEPValidation/BP_MusicListenerProbe");broadcast_graph(probe,"Verb",ue.find_struct("LyraVerbMessage"),ue.find_class("GameplayMessageSubsystem"));ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError("typed LyraVerbMessage broadcast probe failed")
    bp.save_package();mixin.save_package();probe.save_package()
    if any(hashlib.sha256((stage/relative).read_bytes()).hexdigest()!=value for relative,value in child_hashes.items()):raise RuntimeError("music child asset bytes changed")
    return dict(status="passed",kind="musiclifecycle",runtime_acceptance=False,full_acceptance=False,original_full_cdo_and_signatures_preserved=True,
        original_business_graphs_preserved_with_dispatch=True,original_graphs=hashes,transport_nodes=9,new_business_nodes=0,native_listener_nodes_reused=2,
        exact_native_channels=[channel for _,_,channel in selected],no_python_subscription_roots=True,native_listener_lifetime_unchanged=True,
        actual_registered_profile_method_counts=counts,child_asset_hashes=child_hashes,implemented_methods=list(METHODS),
        caller_probe=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=[RELATIVE,SET])

try:report=generate()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_MUSIC_LIFECYCLE_ASSETS_PASSED")
