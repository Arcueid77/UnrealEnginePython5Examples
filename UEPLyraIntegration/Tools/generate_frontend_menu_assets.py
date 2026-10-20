"""Route frontend policy while retaining original async prompts/session/UI nodes."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.frontend_menu_mixin import CLASS,METHODS,GATES,ALIASES

ASSET='Content/UI/Menu/W_LyraFrontEnd.uasset'
TRANSPORT=53
POINTS=(('K2Node_Event_1','then','activate'),('K2Node_ComponentBoundEvent_0','then','start'),('K2Node_ComponentBoundEvent_1','then','options'),('K2Node_ComponentBoundEvent_2','then','quit'),('K2Node_ComponentBoundEvent_3','then','credits'),('K2Node_ComponentBoundEvent_4','then','replays'),('K2Node_ComponentBoundEvent_5','then','logout'),('K2Node_AsyncAction_6','OnResult','quit_result'),('K2Node_AsyncAction_3','OnResult','logout_result'),('K2Node_AsyncAction_5','OnSuccess','logout_success'))
NATIVE_TARGETS=dict(start='K2Node_AsyncAction_2',options='K2Node_AsyncAction_1',credits='K2Node_AsyncAction_4',replays='K2Node_AsyncAction_7',quit='K2Node_AsyncAction_6',logout='K2Node_AsyncAction_3',destroy_session='K2Node_AsyncAction_5',startup='K2Node_AsyncAction_0')

def gate(bp,name,params,focus_output=None):
    graph=ue.blueprint_add_function(bp,GATES[name]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    if focus_output:entry.set_property('ExtraFlags',int(entry.get_property('ExtraFlags'))|0x40000000)
    for label,pin in params:entry.node_create_pin(1,kind(pin),label)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if focus_output else 'ReturnValue');result.node_find_pin('UseOriginal' if focus_output else 'ReturnValue').default_value='true'
    if focus_output:result.node_create_pin(0,kind(focus_output),'ReturnValue')
    connect(entry,'then',result,'execute')

def generate(stage):
    # Some source sections have Easing=None but still own empty default easing
    # subobjects constructed on load. Compile GC can collect those unreferenced
    # inners between exports. Keep the original objects alive for exact visual
    # comparison, then release only the roots owned by this authoring scope.
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'))
    prefix=bp.get_path_name()+':'
    roots=[obj for obj in ue.tobject_iterator(ue.find_class('MovieSceneBuiltInEasingFunction')) if obj.get_path_name().startswith(prefix) and not obj.is_rooted()]
    for obj in roots:obj.add_to_root()
    try:report=_generate(stage)
    finally:
        for obj in roots:obj.remove_from_root()
    if any(obj.is_rooted() for obj in roots):raise RuntimeError('frontend temporary easing roots leaked')
    report['original_native_easing_subobjects_temporarily_rooted_for_exact_export']=len(roots)
    report['temporary_authoring_easing_roots_released']=True
    return report

def _generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    output=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original frontend required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'frontend-menu-before');tree=visuals(bp,output,'frontend-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(ns) for _,ns in originals)
    if total!=34:raise RuntimeError('original frontend footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};focus=next(g for g,_ in originals if g.get_name()=='BP_GetDesiredFocusTarget');focus_entry=focus.Nodes[0];focus_result=next(n for n in focus.Nodes if n.get_class().get_name()=='K2Node_FunctionResult')
    methods={g.get_name() for g,_ in originals if g.get_name()!='EventGraph'}
    for node in event.Nodes:
        if node.get_class().get_name()=='K2Node_Event':methods.add(str(node.EventReference.MemberName))
        if node.get_class().get_name()=='K2Node_ComponentBoundEvent':methods.add(str(node.CustomFunctionName))
    signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
    for graph,node,pin in [(event,nodes[n],p) for n,p,_ in POINTS]+[(focus,focus_entry,'then')]:
        target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
    for node,pin,name in POINTS:gate(bp,name,(('Result',nodes[node].node_find_pin('Result')),) if name.endswith('_result') else ())
    gate(bp,'focus',(),focus_result.node_find_pin('ReturnValue'))
    for name,target in NATIVE_TARGETS.items():
        alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=ALIASES[name];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2:raise RuntimeError('frontend native gate/alias compile failed')
    for node,pin,name in POINTS:
        previous={n.get_name() for n in event.Nodes};insert_gate(event,nodes[node],pin,getattr(bp.GeneratedClass,GATES[name]));call,=[n for n in event.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
        if name.endswith('_result'):nodes[node].node_find_pin('Result').make_link_to(call.node_find_pin('Result'))
    target,=focus_entry.node_find_pin('then').get_linked_to();call=focus.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES['focus']));branch=focus.graph_add_node(K2Node_IfThenElse);focus_entry.node_find_pin('then').break_link_to(target);connect(focus_entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=focus.graph_add_node(K2Node_FunctionResult);early.FunctionReference=focus_result.FunctionReference;focus.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,'ReturnValue')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset_name='DA_FrontendMenuMixin';asset=ue.create_asset(asset_name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.frontend_menu_mixin',PythonClass='LyraFrontendMenu'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    after_signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in signatures};(output/'frontend-public-signatures.json').write_text(json.dumps(dict(before=signatures,after=after_signatures),indent=2),encoding='utf-8')
    if int(bp.Status)==2 or snapshot(bp,'frontend-menu-after')!=before or visuals(bp,output,'frontend-after')!=tree or after_signatures!=signatures:raise RuntimeError('original frontend defaults/tree/animation/public signatures changed')
    if any(semantics(g,ns,ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original frontend graph semantics or GUIDs changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT+5:raise RuntimeError('frontend transport footprint differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS)):raise RuntimeError('frontend complete Profile family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='frontendmenu',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_tree_animations_public_signatures_const_focus_guids_and_graphs_preserved=True,original_four_async_menu_classes_layer_tags_input_suspension_and_native_prompts_preserved=True,original_confirmed_quit_and_logout_destroy_session_success_order_payloads_preserved=True,original_unused_destroy_player_true_logout_node_retained_unconnected=True,original_graph_nodes=total,transport_nodes=TRANSPORT,interface_nodes=interface,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/'+asset_name+'.uasset'])
