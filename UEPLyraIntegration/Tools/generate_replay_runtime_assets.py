"""Retain original component/widget defaults and opaque mouse/Handled ABI."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.replay_runtime_mixin import CLASSES,METHODS,GATES,NATIVE_CREATE
ASSETS={'handler':'Plugins/GameFeatures/ShooterCore/Content/Game/B_HandleShooterReplays.uasset','hud':'Plugins/GameFeatures/ShooterCore/Content/UserInterface/Replays/W_ShooterReplayHUD.uasset','scrub':'Plugins/GameFeatures/ShooterCore/Content/UserInterface/Replays/W_Replay_ScrubBar.uasset'}
def declare(bp,name,params):
    graph=ue.blueprint_add_function(bp,name);start=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for param,pin in params:start.node_create_pin(1,kind(pin),param)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(start,'then',result,'execute')
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[];pending=[]
    for label,total,transport,prefix in (('handler',14,5,'Handler'),('hud',2,4,'HUD'),('scrub',19,8,'Scrub')):
        if hashlib.sha256((stage/ASSETS[label]).read_bytes()).digest()!=hashlib.sha256((official/ASSETS[label]).read_bytes()).digest():raise RuntimeError('fresh original replay runtime family required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-replay-runtime-before');tree=visuals(bp,out,label+'-runtime-before') if label!='handler' else None;originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};names=set();points=[]
        if sum(len(ns) for _,ns in originals)!=total:raise RuntimeError('original replay runtime footprint differs')
        for graph,_ in originals:
            if graph.get_name()!='EventGraph':names.add(graph.get_name())
            for node in graph.Nodes:
                if node.get_class().get_name()=='K2Node_Event':names.add(str(node.EventReference.MemberName))
        signatures={n:ue.describe_function(bp.GeneratedClass,n) for n in names};ignored={g.get_name():set() for g,_ in originals}
        if label=='handler':points=[(event,nodes['K2Node_Event_0'],'then','begin',())]
        elif label=='hud':points=[(event,nodes['K2Node_Event_3'],'then','construct',())]
        else:
            points.append((event,nodes['K2Node_CallFunction_2'],'then','tick',(('Current',nodes['K2Node_CallFunction_0'].node_find_pin('ReturnValue')),('Length',nodes['K2Node_CallFunction_2'].node_find_pin('ReturnValue')))))
            mouse=next(g for g,_ in originals if g.get_name()=='OnMouseButtonDown_0');mn={n.get_name():n for n in mouse.Nodes};local,=mn['K2Node_PromotableOperator_0'].node_find_pin('A').get_linked_to();width,=mn['K2Node_PromotableOperator_0'].node_find_pin('B').get_linked_to();points.append((mouse,mn['K2Node_CallFunction_7'],'then','seek',(('Length',mn['K2Node_CallFunction_7'].node_find_pin('ReturnValue')),('LocalX',local),('Width',width))))
        for graph,node,pin,_,_ in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        for _,_,_,key,params in points:declare(bp,GATES[label][key],params)
        if label=='handler':alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE_CREATE;event.graph_reconstruct_node(alias);connect(alias,'then',nodes['K2Node_CreateWidget_0'],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for graph,node,pin,key,params in points:
            previous={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[label][key]));call,=[n for n in graph.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction'];branch,=[n for n in graph.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_IfThenElse']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
            if key=='seek':result=next(n for n in graph.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');branch.node_find_pin('else').make_link_to(result.node_find_pin('execute'))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Replay'+prefix+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.replay_runtime_mixin',PythonClass='LyraReplay'+prefix+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after={n:ue.describe_function(bp.GeneratedClass,n) for n in names};(out/(label+'-runtime-signatures.json')).write_text(json.dumps(dict(before=signatures,after=after),indent=2),encoding='utf-8')
        if int(bp.Status)==2 or signatures!=after or snapshot(bp,label+'-replay-runtime-after')!=before or (tree is not None and visuals(bp,out,label+'-runtime-after')!=tree):raise RuntimeError('original replay runtime CDO/visual/public ABI changed: '+label)
        if any(semantics(g,ns,ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original replay runtime graph/GUID changed: '+label)
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));actual=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
        if interface!=5 or actual!=transport:raise RuntimeError('replay runtime transport differs: '+repr((label,actual)))
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS[label])):raise RuntimeError('complete replay runtime Profile family required')
        finally:ue.unregister_all_mixins()
        rows[label]=dict(original_nodes=total,transport_nodes=actual,interface_nodes=interface,method_counts=counts,original_cdo_visuals_public_signatures_guids_graphs_preserved=True);pending.extend([bp,asset]);saved.extend([ASSETS[label],'Content/UEPMixins/'+name+'.uasset'])
    for obj in pending:obj.save_package()
    return dict(status='passed',kind='replayruntime',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_native_component_beginplay_and_widget_creation_payload_preserved=True,original_native_umg_tick_and_current_length_getter_order_preserved=True,original_mouse_geometry_pointer_and_handled_reply_entirely_native=True,original_unclamped_ratio_and_native_zero_divide_diagnostic_preserved=True,assets=saved,widgets=rows,new_business_nodes=0,native_end_adapter_nodes=0)
