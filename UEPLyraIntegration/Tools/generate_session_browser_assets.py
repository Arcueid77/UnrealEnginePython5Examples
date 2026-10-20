"""Keep native DoOnce lock and exact weak search delegate/FText error payload."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.session_browser_mixin import CLASS,METHODS,GATES,NATIVE
ASSET='Content/UI/Menu/Experiences/W_SessionBrowserScreen.uasset'
def gate(bp,key,output=None):
    graph=ue.blueprint_add_function(bp,GATES[key]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    if output:entry.ExtraFlags=int(entry.ExtraFlags)|0x40000000
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(entry,'then',result,'execute')
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original browser screen required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'session-browser-before');tree=visuals(bp,out,'session-browser-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(ns) for _,ns in originals)
    if total!=62:raise RuntimeError('original browser footprint differs')
    focus=next(g for g,_ in originals if g.get_name()=='BP_GetDesiredFocusTarget');fe=focus.Nodes[0];fr=next(n for n in focus.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes}
    points=[(nodes[name],pin,key) for name,pin,key in (('K2Node_Event_0','then','activate'),('K2Node_ComponentBoundEvent_2','then','refresh'),('K2Node_MacroInstance_1','Completed','search'),('K2Node_CustomEvent_2','then','unlock'),('K2Node_Knot_0','OutputPin','results'))]
    methods={'BP_GetDesiredFocusTarget'}
    for n in event.Nodes:
        if n.get_class().get_name()=='K2Node_Event':methods.add(str(n.EventReference.MemberName))
        if n.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):methods.add(str(n.CustomFunctionName))
    signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
    for graph,node,pin in [(event,n,p) for n,p,_ in points]+[(focus,fe,'then')]:
        target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
    for _,_,key in points:gate(bp,key)
    gate(bp,'focus',fr.node_find_pin('ReturnValue'))
    for key,target,pin in (('submit','K2Node_CallFunction_6','execute'),('reset','K2Node_MacroInstance_1','Reset')):
        alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE[key];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],pin)
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for node,pin,key in points:insert_gate(event,node,pin,getattr(bp.GeneratedClass,GATES[key]))
    target,=fe.node_find_pin('then').get_linked_to();call=focus.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES['focus']));branch=focus.graph_add_node(K2Node_IfThenElse);fe.node_find_pin('then').break_link_to(target);connect(fe,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=focus.graph_add_node(K2Node_FunctionResult);early.FunctionReference=fr.FunctionReference;focus.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,'ReturnValue')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_SessionBrowserMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.session_browser_mixin',PythonClass='LyraSessionBrowser'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};(out/'session-browser-public-signatures.json').write_text(json.dumps(dict(before=signatures,after=after),indent=2),encoding='utf-8')
    if int(bp.Status)==2 or signatures!=after or snapshot(bp,'session-browser-after')!=before or visuals(bp,out,'session-browser-after')!=tree:raise RuntimeError('browser CDO/tree/animation/public ABI changed')
    if any(semantics(g,ns,ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('browser original graph/GUID changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
    if interface!=5 or transport!=27:raise RuntimeError('browser transport differs: '+str(transport))
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS)):raise RuntimeError('complete browser Profile family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package();return dict(status='passed',kind='sessionbrowser',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_tree_animations_public_signatures_guids_and_graphs_preserved=True,original_native_do_once_lock_shared_across_profiles_and_reset_preserved=True,original_create_store_bind_find_order_and_weak_completion_delegate_preserved=True,original_failed_search_ftext_system_message_before_results_gate_preserved=True,original_empty_results_visibility_list_focus_unlock_order_preserved=True,original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/'+name+'.uasset'])
