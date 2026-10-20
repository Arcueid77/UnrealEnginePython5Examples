"""Retain native localized text nodes, timer factory/binding and original expiry."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals
from generate_message_widget_assets import set_asset,method_counts,move_node
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_hud.explorer_toast_mixin import CLASS,ENTRY,WRITE,START

RELATIVE='Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_ItemAcquiredToastRow.uasset'
PROBE='Content/UEPValidation/BP_ExplorerToastNativeProbe.uasset'
TEXT={'K2Node_VariableGet_0','K2Node_VariableGet_3','K2Node_CallFunction_1','K2Node_Knot_0','K2Node_Knot_1'}
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh original Explorer toast row required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'toast-before');design=visuals(bp,out,'toast-before');methods=('OnListItemObjectSet','SetIcon','OnTimerElapsed');shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};ignored={('K2Node_CallFunction_3','then'),('K2Node_CallFunction_2','execute'),('K2Node_VariableGet_2','self')}
    if sum(len(ns) for _,ns in original)!=25:raise RuntimeError('original toast row footprint differs')
    timer=nodes['K2Node_CallFunction_2'];binding=nodes['K2Node_CustomEvent_0'];text_hash=semantics(event,TEXT,set());hashes={g.get_name():semantics(g,ns-TEXT if g==event else ns,ignored if g==event else set()) for g,ns in original}
    if str(timer.FunctionReference.MemberName)!='K2_SetTimerDelegate' or str(binding.CustomFunctionName)!='OnTimerElapsed' or timer.node_find_pin('Delegate').get_linked_to()[0].owning_node!=binding or timer.node_find_pin('bLooping').default_value!='false':raise RuntimeError('original one-shot native timer delegate required')
    entry_cls=ue.load_class(ENTRY);writer=ue.blueprint_add_function(bp,WRITE);entry=writer.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=entry_cls),'Entry');result=writer.graph_add_node(K2Node_FunctionResult);links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in TEXT for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in TEXT]
    for name in TEXT:move_node(event,writer,nodes[name])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    connect(entry,'Entry',nodes['K2Node_VariableGet_0'],'self');connect(entry,'then',nodes['K2Node_CallFunction_1'],'execute');connect(nodes['K2Node_CallFunction_1'],'then',result,'execute')
    start=event.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName=START;event.graph_reconstruct_node(start);start.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=entry_cls),'Entry');nodes['K2Node_VariableGet_2'].node_find_pin('self').break_all_pin_links(True);connect(start,'Entry',nodes['K2Node_VariableGet_2'],'self');connect(start,'then',timer,'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    write_call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,WRITE));start_call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,START));connect(nodes['K2Node_CallFunction_3'],'then',write_call,'execute');connect(write_call,'then',start_call,'execute')
    for call in (write_call,start_call):connect(nodes['K2Node_DynamicCast_0'],'AsItem Acquired Toast Entry',call,'Entry')
    asset=set_asset(bp,'DA_ExplorerToastRowMixin','uep_lyra_hud.explorer_toast_mixin','LyraExplorerToast');ue.compile_blueprint(bp);ue.unregister_all_mixins();after=snapshot(bp,'toast-after');after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};after_hashes={g.get_name():semantics(g,ns-TEXT if g==event else ns,ignored if g==event else set()) for g,ns in original}
    diagnostics=dict(status=int(bp.Status),cdo_equal=before==after,visuals_equal=visuals(bp,out,'toast-after')==design,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,text_before=text_hash,text_after=semantics(writer,TEXT,set()),bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'toast-preservation.json').write_text(json.dumps(diagnostics,indent=2))
    if int(bp.Status)==2 or not diagnostics['cdo_equal'] or not diagnostics['visuals_equal'] or shapes!=after_shapes or hashes!=after_hashes or diagnostics['text_before']!=diagnostics['text_after'] or diagnostics['bad_guids']:raise RuntimeError('original toast CDO/visual/public signature/text/timer graph partition or GUID changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-25
    if interface!=5 or added!=10:raise RuntimeError('toast original-node typed transport/interface footprint differs')
    counts=method_counts(bp,3);probe=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_ExplorerToastNativeProbe');g=ue.blueprint_add_function(probe,'SeedLocalizedEntry');e=g.Nodes[0];e.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=entry_cls),'Entry');e.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('LyraInventoryItemDefinition')),'Definition');getter=g.graph_add_node_variable_get('DisplayName',ue.find_class('LyraInventoryItemDefinition'));setter=g.graph_add_node_variable_set('TextToShow',entry_cls);connect(e,'then',setter,'execute');connect(e,'Entry',setter,'self');connect(e,'Definition',getter,'self');connect(getter,'DisplayName',setter,'TextToShow');ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('native localized toast fixture compile failed')
    for obj in (bp,asset,probe):obj.save_package()
    return dict(status='passed',kind='explorertoast',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_tree_animations_public_signatures_node_guids_and_graph_partitions_preserved=True,original_native_ftext_property_to_textblock_path_preserved=True,original_timer_factory_delegate_name_guid_one_shot_and_defaults_preserved=True,original_current_item_delegate_broadcast_retained_on_fallback=True,transport_nodes=5,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,method_counts=counts,fixture=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=[RELATIVE,'Content/UEPMixins/DA_ExplorerToastRowMixin.uasset'])
