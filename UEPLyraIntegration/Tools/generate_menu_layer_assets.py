"""Retain native root stacks, async modal/prompt nodes and terminal map payload."""
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
from uep_lyra_hud.menu_layers_mixin import CLASSES,GATES,PUSH,CONFIRM,TRAVEL

ASSETS={k:'Content/'+v.removeprefix('/Game/').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(layout=10,menu=26,close=5,spinner=3)
TRANSPORT=dict(layout=4,menu=28,close=4,spinner=5)
COUNTS=dict(layout=1,menu=6,close=1,spinner=1)

def gate(bp,label,key,params,output=None):
    g=ue.blueprint_add_function(bp,GATES[label][key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    if key=='focus':entry.set_property('ExtraFlags',int(entry.get_property('ExtraFlags'))|0x40000000)
    for name,p in params:entry.node_create_pin(1,kind(p),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original menu/layer widget required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-layer-before');templates=visuals(bp,output,label+'-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original menu/layer footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[];ret=None
        if label=='layout':points=[(event,nodes['K2Node_Event_1'],'then','initialize',())]
        elif label=='close':points=[(event,nodes['K2Node_ComponentBoundEvent_0'],'then','click',())]
        elif label=='menu':
            points=[(event,nodes['K2Node_Event_0'],'then','activate',()),(event,nodes['K2Node_ComponentBoundEvent_0'],'then','quit',()),(event,nodes['K2Node_ComponentBoundEvent_1'],'then','settings',()),(event,nodes['K2Node_ComponentBoundEvent_2'],'then','exit',()),(event,nodes['K2Node_AsyncAction_3'],'OnResult','result',(('Result',nodes['K2Node_AsyncAction_3'].node_find_pin('Result')),))]
        if label in ('menu','spinner'):
            g=next(g for g,_ in originals if g.get_name()=='BP_GetDesiredFocusTarget');ret=(g,g.Nodes[0],next(n for n in g.Nodes if n.get_class().get_name()=='K2Node_FunctionResult'))
        methods=set()
        for g,_ in originals:
            if g.get_name()!='EventGraph':methods.add(g.get_name())
            for n in g.Nodes:
                if n.get_class().get_name()=='K2Node_Event':methods.add(str(n.EventReference.MemberName))
                if n.get_class().get_name()=='K2Node_ComponentBoundEvent':methods.add(str(n.CustomFunctionName))
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for g,node,pin,key,params in points+([(ret[0],ret[1],'then','focus',())] if ret else []):
            target,=node.node_find_pin(pin).get_linked_to();ignored[g.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        for g,node,pin,key,params in points:gate(bp,label,key,params)
        if ret:gate(bp,label,'focus',(),ret[2].node_find_pin('ReturnValue'))
        if label=='menu':
            for name,target in ((PUSH,'K2Node_AsyncAction_0'),(CONFIRM,'K2Node_AsyncAction_3'),(TRAVEL,'K2Node_CallFunction_7')):
                alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=name;event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('menu native gate/alias declaration compile failed')
        for g,node,pin,key,params in points:
            prior={n.get_name() for n in g.Nodes};insert_gate(g,node,pin,getattr(bp.GeneratedClass,GATES[label][key]));call,=[n for n in g.Nodes if n.get_name() not in prior and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        if ret:
            g,entry,result=ret;target,=entry.node_find_pin('then').get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[label]['focus']));branch=g.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=g.graph_add_node(K2Node_FunctionResult);early.FunctionReference=result.FunctionReference;g.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,'ReturnValue')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset_name='DA_MenuLayer'+label.title()+'Mixin';asset=ue.create_asset(asset_name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.menu_layers_mixin',PythonClass='LyraMenuLayer'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-layer-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('menu/layer CDO/visual/signature changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original menu/layer graphs or GUIDs changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('menu/layer transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete menu/layer Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+asset_name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='menulayers',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_public_signatures_const_focus_node_guids_and_graphs_preserved=True,original_layer_tag_stack_order_and_names_preserved=True,original_async_settings_beforepush_deactivation_and_confirmation_localized_prompt_preserved=True,original_confirmed_frontend_map_asset_experience_name_and_absolute_travel_payload_preserved=True,original_quit_input_reset_preference_and_platform_restrictions_preserved=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
