"""Keep native CommonInput delegate lifetime, parent forwarding and widget visuals."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.bound_action_mixin import CLASS,GATES,NATIVE_CLICK

ASSET='Content/UI/Foundation/Widgets/BottomBar/W_BoundActionButton.uasset'

def gate(bp,key,params):
    g=ue.blueprint_add_function(bp,GATES[key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for name,p in params:entry.node_create_pin(1,kind(p),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original bound-action widget required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'bound-before');templates=visuals(bp,output,'bound-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
    if total!=82:raise RuntimeError('original bound-action footprint differs')
    graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[]
    for name,key,param in (('UpdateSyleOnInputMethod','style','InputType'),('ResetMaterials','reset',None)):
        g=graphs[name];entry=g.Nodes[0];points.append((g,entry,'then',key,((param,entry.node_find_pin(param)),) if param else ()))
    for name,key in (('K2Node_Event_10','hover'),('K2Node_Event_8','unhover'),('K2Node_Event_11','click'),('K2Node_Event_7','select'),('K2Node_Event_9','deselect'),('K2Node_Event_15','disable'),('K2Node_Event_16','enable')):points.append((event,nodes[name],'then',key,()))
    latent=nodes['K2Node_PlayAnimationTimeRange_0'];points.extend(((event,latent,'then','clicksound',()),(event,latent,'Finished','finished',())))
    methods=('UpdateSyleOnInputMethod','ResetMaterials','PreConstruct','Construct','Destruct','Event Input Method Changed','BP_OnHovered','BP_OnUnhovered','BP_OnClicked','BP_OnSelected','BP_OnDeselected','BP_OnDisabled','BP_OnEnabled');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
    for graph,node,pin,key,params in points:
        target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals};guids={(g.get_name(),n.get_name()):n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
    for graph,node,pin,key,params in points:gate(bp,key,params)
    native=event.graph_add_node(K2Node_CustomEvent);native.CustomFunctionName=NATIVE_CLICK;event.graph_reconstruct_node(native);connect(native,'then',latent,'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for graph,node,pin,key,params in points:
        previous={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
        for name,p in params:p.make_link_to(call.node_find_pin(name))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_BoundActionMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.bound_action_mixin',PythonClass='LyraBoundAction'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'bound-after')!=before or visuals(bp,output,'bound-after')!=templates or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('bound-action CDO/visual/signature changed')
    if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or any(n.NodeGuid.as_dict()!=guids[g.get_name(),n.get_name()] for g,names in originals for n in g.Nodes if n.get_name() in names):raise RuntimeError('original bound-action graphs/GUIDs changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=50:raise RuntimeError('bound-action transport footprint differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),11):raise RuntimeError('complete bound-action Profile family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='boundaction',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_animations_signatures_guids_and_graphs_preserved=True,native_construct_destruct_parent_calls_input_subsystem_factories_and_add_remove_delegates_retained=True,native_latent_play_time_range_and_finished_retained=True,source_break_make_brush_omitted_fields_reset_to_defaults=True,original_graph_nodes=82,transport_nodes=45,interface_nodes=5,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/DA_BoundActionMixin.uasset'])
