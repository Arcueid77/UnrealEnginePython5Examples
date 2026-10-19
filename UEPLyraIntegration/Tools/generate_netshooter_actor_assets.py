"""Preserve native Hit authority/DoOnce, reliable RPC, weak overlap and Delay."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile
from message_payload_graphs import connect
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from uep_lyra_weapons.netshooter_actor_mixin import HIT,BODY,DELAY,AFTER,BIND

PACKAGE="/ShooterCore/Weapons/NetShooter_PROTO/B_NetShooter.B_NetShooter"
RELATIVE="Plugins/GameFeatures/ShooterCore/Content/Weapons/NetShooter_PROTO/B_NetShooter.uasset"


def generate(stage):
    official=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    digest=hashlib.sha256(official.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest:raise RuntimeError("fresh original NetShooter Actor required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"netshooter-actor-before");class_name=bp.GeneratedClass.get_path_name()
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in ("ReceiveHit","SpawnComponents","OverlapRays")}
    if signatures["SpawnComponents"]["flags"]&(0x40|0x80|0x4000)!=(0x40|0x80|0x4000):raise RuntimeError("original reliable multicast SpawnComponents required")
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    if {g.get_name():len(keys) for g,keys in originals}!={"UserConstructionScript":1,"EventGraph":46}:raise RuntimeError("original NetShooter graph footprint differs")
    graph,=[g for g,_ in originals if g.get_name()=="EventGraph"];nodes={n.get_name():n for n in graph.Nodes}
    once,start,rpc,add,delay,destroy,hit=[nodes[name] for name in ("K2Node_MacroInstance_1","K2Node_VariableSet_3","K2Node_CustomEvent_1","K2Node_AddComponent_0","K2Node_CallFunction_41","K2Node_CallFunction_43","K2Node_Event_3")]
    ignored={(once.get_name(),"Completed"),(start.get_name(),"execute"),(rpc.get_name(),"then"),(rpc.get_name(),"HitResult"),(add.get_name(),"execute"),(delay.get_name(),"execute"),(delay.get_name(),"then"),(destroy.get_name(),"execute"),(hit.get_name(),"HitLocation"),(hit.get_name(),"HitNormal")}
    original_data={(node.get_name(),pin):{(p.owning_node.get_name(),p.name) for p in node.node_find_pin(pin).get_linked_to()} for node,pin in ((hit,"HitLocation"),(hit,"HitNormal"),(rpc,"HitResult"))}
    hashes={g.get_name():semantics(g,keys,ignored if g==graph else set()) for g,keys in originals}
    def event(name,target,parameters=()):
        node=graph.graph_add_node(K2Node_CustomEvent);node.CustomFunctionName=name;graph.graph_reconstruct_node(node)
        for pin,kind,typ in parameters:node.node_create_pin(1,EdGraphPinType(PinCategory=kind,PinSubCategoryObject=typ),pin)
        connect(node,"then",target,"execute");return node
    event(HIT,start,(("HitLocation","struct",ue.find_struct("Vector")),("HitNormal","struct",ue.find_struct("Vector"))))
    event(BODY,add,(("HitResult","struct",ue.find_struct("HitResult")),));event(DELAY,delay);event(AFTER,destroy)
    bind_graph=ue.blueprint_add_function(bp,BIND);entry=bind_graph.Nodes[0];component_class=ue.find_class("PrimitiveComponent")
    entry.node_create_pin(1,EdGraphPinType(PinCategory="object",PinSubCategoryObject=component_class),"Ray")
    bind=bind_graph.graph_add_node(K2Node_AddDelegate);bind.DelegateReference=MemberReference(MemberName="OnComponentBeginOverlap",MemberParent=component_class,bSelfContext=False);bind_graph.graph_reconstruct_node(bind)
    delegate=bind_graph.graph_add_node(K2Node_CreateDelegate);owner=bind_graph.graph_add_node(K2Node_Self)
    connect(entry,"then",bind,"execute");connect(entry,"Ray",bind,"self");connect(owner,"self",delegate,"self");connect(delegate,"OutputDelegate",bind,"Delegate");delegate.SelectedFunctionName="OverlapRays"
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_NetShooterActorMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.netshooter_actor_mixin",PythonClass="LyraNetShooterActor"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    calls=[]
    for source,output,target,method in ((once,"Completed",start,HIT),(rpc,"then",add,BODY),(delay,"then",destroy,AFTER)):
        call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,method));source.node_find_pin(output).break_link_to(target.node_find_pin("execute"));connect(source,output,call,"execute");calls.append(call)
    connect(hit,"HitLocation",calls[0],"HitLocation");connect(hit,"HitNormal",calls[0],"HitNormal");connect(rpc,"HitResult",calls[1],"HitResult")
    for (name,pin),links in original_data.items():
        current={(p.owning_node.get_name(),p.name) for p in nodes[name].node_find_pin(pin).get_linked_to() if p.owning_node not in calls}
        if current!=links:raise RuntimeError("original NetShooter data consumer disconnected")
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=class_name or snapshot(bp,"netshooter-actor-after")!=before:raise RuntimeError("original NetShooter class/full CDO changed")
    if len(graph.Nodes)!=53 or len(bind_graph.Nodes)!=4 or any(semantics(g,keys,ignored if g==graph else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError("original NetShooter graph changed outside transport endpoints")
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()):raise RuntimeError("original NetShooter signatures/RPC flags changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==bp.GeneratedClass]
        counts={key:len(value["functions"]) for key,value in row["profiles"].items()}
        if counts!=dict(Python=4,BlueprintFallback=4):raise RuntimeError("four Actor policy methods/Profile required")
    finally:ue.unregister_all_mixins()
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="netshooteractor",runtime_acceptance=False,full_acceptance=False,original_class=class_name,
        original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,original_business_graphs_preserved_with_dispatch=True,
        original_graphs_unmodified=False,original_graphs=hashes,original_graph_nodes=47,transport_nodes=11,new_business_nodes=0,native_end_adapter_nodes=0,
        original_rpc_flags_and_entry_preserved=True,rpc_function_overridden=False,original_native_authority_do_once_preserved=True,original_native_delay_node_uuid_preserved=True,
        native_overlap_weak_named_delegate_preserved=True,original_component_template_reused=True,actual_registered_profile_method_counts=counts,native_register_restore_passed=True,
        extra_signatures=signatures,assets=[RELATIVE,"Content/UEPMixins/DA_NetShooterActorMixin.uasset"],reference_hashes={str(official):digest})
