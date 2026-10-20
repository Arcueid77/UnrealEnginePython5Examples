"""Retain original menu graphs/visuals and native latent click continuation."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.menu_buttons_mixin import CLASSES,CHILDREN,GATES,NATIVE_CLICK

ASSETS={k:'Content/UI/Menu/'+p.rsplit('/',1)[-1].split('.')[0]+'.uasset' for k,p in CLASSES.items()}
TOTAL=dict(menu=130,tile=75)
TRANSPORT=62
COUNTS=15

def gate(bp,key,params,output=None):
    g=ue.blueprint_add_function(bp,GATES[key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for name,p in params:entry.node_create_pin(1,kind(p),name)
    field='UseOriginal' if output else 'ReturnValue';result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),field);result.node_find_pin(field).default_value='true'
    if output:result.node_create_pin(0,kind(output),'Progress')
    connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    child_bytes={k:hashlib.sha256((stage/('Content/UI/Menu/'+v.rsplit('/',1)[-1].split('.')[0]+'.uasset')).read_bytes()).hexdigest() for k,v in CHILDREN.items()}
    for label in ('menu','tile'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original menu/tile assets required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-menu-before');templates=visuals(bp,output,label+'-menu-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original menu/tile footprint differs')
        graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[]
        for method,key in [('UpdateTextStyle','textstyle'),('ResetMaterials','reset'),('UpdateButtonStyles' if label=='menu' else 'UpdateTileArt','layout' if label=='menu' else 'art')]:
            g=graphs[method];points.append((g,g.Nodes[0],'then',key,()))
        for node,key in [('K2Node_Event_10','hover'),('K2Node_Event_8','unhover'),('K2Node_Event_11','click'),('K2Node_Event_7','select'),('K2Node_Event_9','deselect'),('K2Node_Event_15','disable'),('K2Node_Event_16','enable')]:points.append((event,nodes[node],'then',key,()))
        pre=nodes['K2Node_Event_12' if label=='menu' else 'K2Node_Event_3'];points.append((event,pre,'then','pre',(('IsDesignTime',pre.node_find_pin('IsDesignTime')),)))
        points.append((event,nodes['K2Node_Event_0' if label=='menu' else 'K2Node_Event_2'],'then','text' if label=='menu' else 'construct',()))
        latent=nodes['K2Node_PlayAnimationTimeRange_0'];points.extend(((event,latent,'then','clicksound',()),(event,latent,'Finished','finished',())))
        methods=('UpdateTextStyle','ResetMaterials','UpdateButtonStyles' if label=='menu' else 'UpdateTileArt','GetPressProgress','PreConstruct','Construct','BP_OnHovered','BP_OnUnhovered','BP_OnClicked','BP_OnSelected','BP_OnDeselected','BP_OnDisabled','BP_OnEnabled')+(('UpdateButtonText',) if label=='menu' else ())
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        g=graphs['GetPressProgress'];entry=g.Nodes[0];result=next(n for n in g.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');ret=(g,entry,result)
        for graph,node,pin,key,params in points+[(g,entry,'then','progress',())]:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals};guids={(g.get_name(),n.get_name()):n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        for graph,node,pin,key,params in points:gate(bp,key,params)
        gate(bp,'progress',(),result.node_find_pin('Progress'))
        native=event.graph_add_node(K2Node_CustomEvent);native.CustomFunctionName=NATIVE_CLICK;event.graph_reconstruct_node(native);connect(native,'then',latent,'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for graph,node,pin,key,params in points:
            previous={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        g,entry,result=ret;target,=entry.node_find_pin('then').get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES['progress']));branch=g.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=g.graph_add_node(K2Node_FunctionResult);early.FunctionReference=result.FunctionReference;g.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'Progress',early,'Progress')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Menu'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.menu_buttons_mixin',PythonClass='LyraMenu'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-menu-after')!=before or visuals(bp,output,label+'-menu-after')!=templates or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('menu/tile CDO/visual/signature changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or any(n.NodeGuid.as_dict()!=guids[g.get_name(),n.get_name()] for g,names in originals for n in g.Nodes if n.get_name() in names):raise RuntimeError('original menu/tile graph semantics/GUIDs changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT+5:raise RuntimeError('menu/tile transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS):raise RuntimeError('complete menu/tile Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT,interface_nodes=interface,method_counts=counts)
    for key,value in CHILDREN.items():
        relative='Content/UI/Menu/'+value.rsplit('/',1)[-1].split('.')[0]+'.uasset'
        if hashlib.sha256((stage/relative).read_bytes()).hexdigest()!=child_bytes[key]:raise RuntimeError('inherited modal/arrow asset changed')
    return dict(status='passed',kind='menubuttons',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_animations_signatures_guids_and_graphs_preserved=True,native_ftext_transport_preserved=True,native_latent_play_time_range_and_finished_retained=True,empty_menu_construct_stays_unconnected=True,fixture=dict(stage_only=True,asset=str(stage/'Content/UEPValidation/BP_FoundationButtonsProbe.uasset'),sha256=hashlib.sha256((stage/'Content/UEPValidation/BP_FoundationButtonsProbe.uasset').read_bytes()).hexdigest()),inherited_modal_arrow_asset_bytes_unchanged=child_bytes,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
