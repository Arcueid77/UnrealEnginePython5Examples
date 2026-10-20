"""Keep original inventory-message proxy/split payload; add typed policy gate."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals
from generate_message_widget_assets import set_asset,method_counts
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect,broadcast_graph
from uep_lyra_hud.explorer_grid_mixin import CLASS,LISTEN,MESSAGE,CHANNEL

RELATIVE='Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_InventoryGrid.uasset'
PROBE='Content/UEPValidation/BP_ExplorerGridMessageProbe.uasset'

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh original Explorer inventory grid required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'grid-before');design=visuals(bp,out,'grid-before');shape=ue.describe_function(bp.GeneratedClass,'Construct');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};action=nodes['K2Node_AsyncAction_ListenForGameplayMessages_0'];ignored={(action.get_name(),'OnMessageReceived'),('K2Node_IfThenElse_0','execute')}
    if sum(len(ns) for _,ns in original)!=22:raise RuntimeError('original Explorer grid footprint differs')
    if action.node_find_pin('Channel').default_value!='(TagName="'+CHANNEL+'")' or action.node_find_pin('PayloadType').default_object!=ue.find_struct('LyraInventoryChangeMessage') or action.node_find_pin('MatchType').default_value!='ExactMatch':raise RuntimeError('original exact typed inventory listener required')
    hashes={g.get_name():semantics(g,ns,ignored if g==event else set()) for g,ns in original}
    make_gate(bp,MESSAGE,None);gate=next(g for g in bp.FunctionGraphs if g.get_name()==MESSAGE)
    for name,source in (('Instance','Payload_Instance'),('NewCount','Payload_NewCount'),('Delta','Payload_Delta')):
        pin=action.node_find_pin(source);gate.Nodes[0].node_create_pin(1,EdGraphPinType(PinCategory=pin.category,PinSubCategory=pin.sub_category,PinSubCategoryObject=pin.sub_category_object),name)
    listen=event.graph_add_node(K2Node_CustomEvent);listen.CustomFunctionName=LISTEN;event.graph_reconstruct_node(listen);connect(listen,'then',action,'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    old=set(n.get_name() for n in event.Nodes);insert_gate(event,action,'OnMessageReceived',getattr(bp.GeneratedClass,MESSAGE));call,=[n for n in event.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction']
    for name,source in (('Instance','Payload_Instance'),('NewCount','Payload_NewCount'),('Delta','Payload_Delta')):connect(action,source,call,name)
    asset=set_asset(bp,'DA_ExplorerInventoryGridMixin','uep_lyra_hud.explorer_grid_mixin','LyraExplorerGrid');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    after=snapshot(bp,'grid-after');after_design=visuals(bp,out,'grid-after');after_shape=ue.describe_function(bp.GeneratedClass,'Construct');after_hashes={g.get_name():semantics(g,ns,ignored if g==event else set()) for g,ns in original}
    if int(bp.Status)==2 or after!=before or after_design!=design or after_shape!=shape or after_hashes!=hashes or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original grid CDO/visual/signature/node GUID/graph payload changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-22
    if interface!=5 or added!=10:raise RuntimeError('grid typed transport/interface footprint differs')
    counts=method_counts(bp,2);probe=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_ExplorerGridMessageProbe');broadcast_graph(probe,'Inventory',ue.find_struct('LyraInventoryChangeMessage'),ue.find_class('GameplayMessageSubsystem'));ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('typed native inventory message probe compile failed')
    for obj in (bp,asset,probe):obj.save_package()
    preservation=dict(cdo_before=before,cdo_after=after,signature_before=shape,signature_after=after_shape,graph_hashes_before=hashes,graph_hashes_after=after_hashes,node_guids_preserved=True,original_nodes=22,transport_nodes=5,interface_nodes=5,method_counts=counts);(out/'grid-preservation.json').write_text(json.dumps(preservation,indent=2))
    return dict(status='passed',kind='explorergrid',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_tree_animations_public_signature_all_nodes_guids_and_graph_payloads_preserved=True,original_native_exact_inventory_message_proxy_and_split_payload_reused=True,original_clear_snapshot_then_listen_order_and_unfiltered_message_branch_order_preserved=True,transport_nodes=5,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,method_counts=counts,fixture=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest(),package='/Game/UEPValidation/BP_ExplorerGridMessageProbe.BP_ExplorerGridMessageProbe_C'),assets=[RELATIVE,'Content/UEPMixins/DA_ExplorerInventoryGridMixin.uasset'])
