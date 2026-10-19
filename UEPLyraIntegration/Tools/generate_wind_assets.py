"""Keep native MultiGate/array semantics and all original wind graphs behind gates."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_audio.wind_system_mixin import CLASS,PLAYER_ENTRY,SCHEDULE_ENTRY,AFTER_PLAYER,STAGE

RELATIVE="Content/Audio/Blueprints/B_WindSystem.uasset"
SET="Content/UEPMixins/DA_WindSystemMixin.uasset"


def generate(stage):
    marker=json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"));original=Path(marker["source"]).parent/RELATIVE;digest=hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest or (stage/SET).exists():raise RuntimeError("fresh original wind/Set required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.rsplit("_C",1)[0]);ue.unregister_all_mixins();before=snapshot(bp,"wind-before");signature=ue.describe_function(bp.GeneratedClass,"ReceiveTick")
    graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];old_total=sum(len(names) for _,names in graphs)
    if old_total!=62:raise RuntimeError("original full wind footprint differs")
    graph=bp.UbergraphPages[0];array,=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_CallArrayFunction" and str(n.FunctionReference.MemberName)=="Array_Set"]
    schedule,=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_MultiGate"]
    if array.node_find_pin("Index").default_value!="0" or array.node_find_pin("bSizeToFit").default_value!="false" or schedule.node_find_pin("Loop").default_value!="true" or schedule.node_find_pin("StartIndex").default_value!="-1":raise RuntimeError("native array/scheduler baseline differs")
    ignored={(array.get_name(),"execute"),(schedule.get_name(),"execute")}
    for node,pin in ((array,"then"),*[(schedule,"Out "+str(i)) for i in range(5)]):
        target,=node.node_find_pin(pin).get_linked_to();ignored.update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,names,ignored if g==graph else set()) for g,names in graphs}
    make_gate(bp,AFTER_PLAYER,None);make_gate(bp,STAGE,None)
    entry=next(g for g in ue.blueprint_get_all_graphs(bp) if g.get_name()==STAGE).Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory="int"),"Stage")
    for name,target in ((PLAYER_ENTRY,array),(SCHEDULE_ENTRY,schedule)):
        event=graph.graph_add_node(K2Node_CustomEvent);event.CustomFunctionName=name;graph.graph_reconstruct_node(event);connect(event,"then",target,"execute")
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    insert_gate(graph,array,"then",getattr(bp.GeneratedClass,AFTER_PLAYER))
    for i in range(5):
        old_calls={n.get_name() for n in graph.Nodes}
        insert_gate(graph,schedule,"Out "+str(i),getattr(bp.GeneratedClass,STAGE));call,=[n for n in graph.Nodes if n.get_name() not in old_calls and n.get_class().get_name()=="K2Node_CallFunction"]
        call.node_find_pin("Stage").default_value=str(i)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;mixin=ue.create_asset("DA_WindSystemMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_audio.wind_system_mixin",PythonClass="LyraWind"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,"wind-after")!=before or ue.describe_function(bp.GeneratedClass,"ReceiveTick")!=signature:raise RuntimeError("wind CDO/signature/compile changed")
    if any(semantics(g,names,ignored if g==graph else set())!=hashes[g.get_name()] for g,names in graphs):raise RuntimeError("original wind graph changed beyond typed transports")
    added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-old_total
    interface_nodes=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ("GetPythonMixinSet","GetPythonMixinProfile"))
    if added!=23 or interface_nodes!=5:raise RuntimeError("wind transport/interface footprint differs: "+str((added,interface_nodes)))
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==bp.GeneratedClass];counts={name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts!=dict(Python=3,BlueprintFallback=3):raise RuntimeError("wind three-method family required")
    finally:ue.unregister_all_mixins()
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="windsystem",runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,
        original_business_graphs_preserved_with_dispatch=True,original_graph_nodes=62,original_graphs=hashes,transport_nodes=18,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,
        native_multigate_state_reused=True,native_array_set_and_no_resize_preserved=True,actual_registered_profile_method_counts=counts,assets=[RELATIVE,SET])
