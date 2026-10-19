"""Add base-owned typed gates around original child parent/Delay/listener nodes."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="generate_music_family_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect,broadcast_graph
from generate_dash_selector_assets import snapshot
from generate_music_manager_assets import RELATIVE,SET,CHILDREN
from uep_lyra_audio.music_manager_mixin import CLASS
from uep_lyra_audio.music_manager_lifecycle_mixin import METHODS as BASE_METHODS
from uep_lyra_audio.music_family_mixin import START,AFTER,CAPTURED,DELAY_ENTRY,CP_ENTRY

PROBE="Content/UEPValidation/BP_MusicFamilyProbe.uasset"
def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))
def generate():
    stage=require_authoring_stage(arg("UEPMusicFamilyStage"),ue.convert_relative_path_to_full(ue.get_content_dir()));baseline=json.loads(Path(arg("UEPMusicLifecycleBaseline")).read_text(encoding="utf-8-sig"))
    if baseline["status"]!="passed" or baseline["kind"]!="musiclifecycle" or len(baseline["assets"])!=2:raise RuntimeError("exact music lifecycle baseline required")
    for asset in baseline["assets"]:
        for field in ("stage","overlay"):
            if hashlib.sha256(Path(asset[field]).read_bytes()).hexdigest().lower()!=asset["sha256"].lower():raise RuntimeError("music lifecycle bytes changed")
    if (stage/PROBE).exists():raise RuntimeError("fresh family broadcast probe required")
    ue.unregister_all_mixins();base=ue.load_object(Blueprint,CLASS.rsplit("_C",1)[0]);ue.unregister_all_mixins();before=snapshot(base,"music-family-base-before")
    base_graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(base)];base_hashes={g.get_name():semantics(g,names,set()) for g,names in base_graphs}
    signatures={name:ue.describe_function(base.GeneratedClass,name) for name in BASE_METHODS};children={};proof={};old_total=sum(len(names) for _,names in base_graphs)
    make_gate(base,START,None)
    graph=ue.blueprint_add_function(base,AFTER);entry=graph.Nodes[0]
    for name in ("Menu","ControlPoint"):entry.node_create_pin(1,EdGraphPinType(PinCategory="bool"),name)
    result=graph.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory="bool"),"ReturnValue");result.node_find_pin("ReturnValue").default_value="true";connect(entry,"then",result,"execute")
    make_gate(base,CAPTURED,None);entry=next(g for g in ue.blueprint_get_all_graphs(base) if g.get_name()==CAPTURED).Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory="int"),"OwnerTeamID")
    ue.compile_blueprint(base);ue.unregister_all_mixins()
    for label,(package,relative) in CHILDREN.items():
        source=stage/relative;marker=json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"));official=Path(marker["source"]).parent/relative
        if hashlib.sha256(source.read_bytes()).hexdigest()!=hashlib.sha256(official.read_bytes()).hexdigest():raise RuntimeError("fresh original music child required")
        bp=ue.load_object(Blueprint,package);ue.unregister_all_mixins();children[label]=bp;child_before=snapshot(bp,"music-family-"+label+"-before")
        sig={name:ue.describe_function(bp.GeneratedClass,name) for name in BASE_METHODS};graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];event=bp.UbergraphPages[0]
        parent,=[n for n in event.Nodes if n.get_class().get_name()=="K2Node_CallParentFunction" and str(n.FunctionReference.MemberName)=="ReceiveBeginPlay"]
        delay,=[n for n in event.Nodes if n.get_class().get_name()=="K2Node_CallFunction" and str(n.FunctionReference.MemberName)=="Delay"]
        menu,=[n for n in event.Nodes if n.get_class().get_name()=="K2Node_CallFunction" and str(n.FunctionReference.MemberName)=="SetIsMenu"]
        if float(delay.node_find_pin("Duration").default_value)!=.2:raise RuntimeError("original child Delay changed")
        latent_before=delay.node_find_pin("LatentInfo").default_value;ignored=set()
        for node,pin in ((parent,"then"),(delay,"then")):
            target,=node.node_find_pin(pin).get_linked_to();ignored.update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        actions=[n for n in event.Nodes if n.get_class().get_name()=="K2Node_AsyncAction_ListenForGameplayMessages"]
        if label=="control_point":
            action,=actions
            if "ShooterGame.ControlPoint.Captured.Message" not in action.node_find_pin("Channel").default_value or action.node_find_pin("MatchType").default_value!="ExactMatch":raise RuntimeError("original control-point listener changed")
            target,=action.node_find_pin("OnMessageReceived").get_linked_to();ignored.update(((action.get_name(),"OnMessageReceived"),(target.owning_node.get_name(),target.name),(action.get_name(),"execute")))
        elif actions:raise RuntimeError("unexpected child listener")
        hashes={g.get_name():semantics(g,names,ignored if g==event else set()) for g,names in graphs};old_total+=sum(len(names) for _,names in graphs)
        start=event.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName=DELAY_ENTRY;event.graph_reconstruct_node(start);connect(start,"then",delay,"execute")
        insert_gate(event,parent,"then",getattr(base.GeneratedClass,START));insert_gate(event,delay,"then",getattr(base.GeneratedClass,AFTER))
        after_call,=[n for n in event.Nodes if n.get_class().get_name()=="K2Node_CallFunction" and str(n.FunctionReference.MemberName)==AFTER]
        after_call.node_find_pin("Menu").default_value=menu.node_find_pin("InBool").default_value;after_call.node_find_pin("ControlPoint").default_value="true" if label=="control_point" else "false"
        if label=="control_point":
            start_cp=event.graph_add_node(K2Node_CustomEvent);start_cp.CustomFunctionName=CP_ENTRY;event.graph_reconstruct_node(start_cp);connect(start_cp,"then",action,"execute")
            insert_gate(event,action,"OnMessageReceived",getattr(base.GeneratedClass,CAPTURED));call,=[n for n in event.Nodes if n.get_class().get_name()=="K2Node_CallFunction" and str(n.FunctionReference.MemberName)==CAPTURED]
            connect(action,"Payload_OwnerTeamID",call,"OwnerTeamID")
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,"music-family-"+label+"-after")!=child_before or any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in sig.items()):raise RuntimeError("child compile/CDO/signature changed")
        if any(semantics(g,names,ignored if g==event else set())!=hashes[g.get_name()] for g,names in graphs) or delay.node_find_pin("LatentInfo").default_value!=latent_before:raise RuntimeError("original child graph/latent identity changed")
        proof[label]=dict(original_graphs=hashes,dispatch_endpoints=sorted(ignored),delay_seconds=.2,latent_identity=latent_before,native_parent_calls_preserved=True,child_mixin_or_selector_added=False)
    mixin=ue.load_object(ue.find_class("UEPPythonMixinSet"),"/Game/UEPMixins/DA_MusicManagerMixin.DA_MusicManagerMixin")
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_audio.music_family_mixin",PythonClass="LyraMusicFamily"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.compile_blueprint(base);ue.unregister_all_mixins()
    if int(base.Status)==2 or snapshot(base,"music-family-base-after")!=before or any(ue.describe_function(base.GeneratedClass,name)!=value for name,value in signatures.items()):raise RuntimeError("base CDO/original signatures changed")
    if any(semantics(g,names,set())!=base_hashes[g.get_name()] for g,names in base_graphs):raise RuntimeError("base original listener/control graphs changed")
    new_total=sum(len(g.Nodes) for bp in (base,*children.values()) for g in ue.blueprint_get_all_graphs(bp))
    if new_total-old_total!=24:raise RuntimeError("family transport footprint differs: "+str(new_total-old_total))
    try:
        ue.register_declared_mixin(base.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==base.GeneratedClass];counts={name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts!=dict(Python=11,BlueprintFallback=11):raise RuntimeError("complete eleven-method base-owned family required")
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class("Object"),"/Game/UEPValidation/BP_MusicFamilyProbe");broadcast_graph(probe,"Captured",ue.find_struct("LyraControlPointStatusMessage"),ue.find_class("GameplayMessageSubsystem"));ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError("typed CP broadcast probe failed")
    for bp in (base,*children.values()):bp.save_package()
    mixin.save_package();probe.save_package()
    return dict(status="passed",kind="musicfamily",runtime_acceptance=False,full_acceptance=False,original_full_cdos_and_signatures_preserved=True,
        original_business_graphs_preserved_with_dispatch=True,base_graphs_unchanged=True,children=proof,transport_nodes=24,new_business_nodes=0,
        native_parent_calls_preserved=3,native_delay_nodes_reused=3,native_cp_listener_reused=True,base_owned_mixin_only=True,actual_registered_profile_method_counts=counts,
        caller_probe=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=[RELATIVE,SET,*[v[1] for v in CHILDREN.values()]])

try:report=generate()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_MUSIC_FAMILY_ASSETS_PASSED")
