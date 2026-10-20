"""Typed CommonUI policy gates preserve native parents, text and widget visuals."""
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
from uep_lyra_hud.foundation_buttons_mixin import CLASSES,GATES,BIND

ASSETS={k:'Content/'+v.removeprefix('/Game/').removesuffix('_C').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(base=65,tab=30,tabs=70)
TRANSPORT=dict(base=45,tab=20,tabs=17)
COUNTS=dict(base=11,tab=5,tabs=4)
PROBE='Content/UEPValidation/BP_FoundationButtonsProbe.uasset'


def localized_probe(stage):
    source=ue.load_class('/ShooterCore/UserInterface/ScoreBoard/W_SB_TeamStat.W_SB_TeamStat_C');probe=ue.create_blueprint(ue.find_class('Actor'),'/Game/UEPValidation/BP_FoundationButtonsProbe')
    for name in ('SetLocalized','MakeTab'):
        g=ue.blueprint_add_function(probe,name);entry=g.Nodes[0];get=g.graph_add_node_call_function(source.UEPSBLocalizedTeamName);get.node_find_pin('self').default_object=source.get_cdo();get.node_find_pin('Team').default_value='1';connect(entry,'then',get,'execute');result=g.graph_add_node(K2Node_FunctionResult)
        if name=='SetLocalized':
            entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('LyraButtonBase')),'Button');call=g.graph_add_node_call_function(ue.find_class('LyraButtonBase').SetButtonText);connect(get,'then',call,'execute');connect(entry,'Button',call,'self');connect(get,'ReturnValue',call,'InText');connect(call,'then',result,'execute')
        else:
            entry.node_create_pin(1,EdGraphPinType(PinCategory='name'),'TabId');node=g.graph_add_node(ue.find_class('K2Node_MakeStruct'));node.StructType=ue.find_struct('LyraTabDescriptor');g.graph_reconstruct_node(node);connect(get,'ReturnValue',node,'TabText');result.node_create_pin(0,EdGraphPinType(PinCategory='struct',PinSubCategoryObject=ue.find_struct('LyraTabDescriptor')),'Descriptor');connect(get,'then',result,'execute');connect(node,'LyraTabDescriptor',result,'Descriptor')
    ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('native localized button/descriptor probe compile failed')
    probe.save_package();return dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest())


def gate(bp,key,params,output=None):
    g=ue.blueprint_add_function(bp,GATES[key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for name,p in params:entry.node_create_pin(1,kind(p),name)
    field='UseOriginal' if output else 'ReturnValue';result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),field);result.node_find_pin(field).default_value='true'
    if output:result.node_create_pin(0,kind(output),'Progress')
    connect(entry,'then',result,'execute')


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label in ('base','tab','tabs'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original foundation button family required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-foundation-before');templates=visuals(bp,output,label+'-foundation-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original foundation button footprint differs')
        graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[];ret=None
        if label=='base':
            pairs=(('UpdateTextAndStyle','combined','InputType'),('SetControllerStyle','controller','ControllerInputStyle'),('UpdateStyle','style','UsingGamepad'),('SetMouseKeyboardStyle','mouse','ControllerInputStyle'),('UpdateContentAlignment','alignupdate',None),('SetContentAlignment','align','ContentAlignment'),('UpdateTextStyle','textstyle',None))
            for method,key,param in pairs:
                g=graphs[method];entry=g.Nodes[0];points.append((g,entry,'then',key,((param,entry.node_find_pin(param)),) if param else ()))
            for name,key,param in (('K2Node_Event_4','pre','IsDesignTime'),('K2Node_Event_2151','held','HeldPercent'),('K2Node_Event_1','text',None)):
                node=nodes[name];points.append((event,node,'then',key,((param,node.node_find_pin(param)),) if param else ()))
            g=graphs['GetPressProgress'];entry=g.Nodes[0];result=next(n for n in g.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');ret=(g,entry,result);gate(bp,'progress',(),result.node_find_pin('Progress'));methods=tuple(m for m,_,_ in pairs)+('GetPressProgress','PreConstruct','OnActionProgress','UpdateButtonText','UpdateButtonStyle','OnCurrentTextStyleChanged','OnActionComplete')
        elif label=='tab':
            for name,key,param in (('K2Node_Event_1','tabtext',None),('K2Node_Event_2','hover',None),('K2Node_Event_3','unhover',None),('K2Node_Event_4','select',None),('K2Node_Event_5','deselect',None)):
                node=nodes[name];points.append((event,node,'then',key,((param,node.node_find_pin(param)),) if param else ()))
            methods=('UpdateButtonText','BP_OnHovered','BP_OnUnhovered','BP_OnSelected','BP_OnDeselected')
        else:
            for method,key,param in (('UpdateTabStyles','tabstyle','ButtonWidget'),('DebugCreateTabsForDesigner','debug',None)):
                g=graphs[method];entry=g.Nodes[0];points.append((g,entry,'then',key,((param,entry.node_find_pin(param)),) if param else ()))
            points.extend(((event,nodes['K2Node_CallParentFunction_2'],'then','tabpre',(('IsDesignTime',nodes['K2Node_Event_42'].node_find_pin('IsDesignTime')),)),(event,nodes['K2Node_CustomEvent_14'],'then','refresh',())));methods=('UpdateTabStyles','DebugCreateTabsForDesigner','PreConstruct','Refresh Next/Previous Visibility','HandleTabCreation','HandleTabRemoval','Construct','CustomEvent_0','CustomEvent_1')
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for g,node,pin,key,params in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[g.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        if ret:
            g,entry,_=ret;target,=entry.node_find_pin('then').get_linked_to();ignored[g.get_name()].update(((entry.get_name(),'then'),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals};guids={(g.get_name(),n.get_name()):n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        for g,node,pin,key,params in points:gate(bp,key,params)
        if label=='tabs':
            bind=event.graph_add_node(K2Node_CustomEvent);bind.CustomFunctionName=BIND;event.graph_reconstruct_node(bind);connect(bind,'then',nodes['K2Node_AssignDelegate_0'],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for g,node,pin,key,params in points:
            previous={n.get_name() for n in g.Nodes};insert_gate(g,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in g.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        if ret:
            g,entry,result=ret;target,=entry.node_find_pin('then').get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES['progress']));branch=g.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=g.graph_add_node(K2Node_FunctionResult);early.FunctionReference=result.FunctionReference;g.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'Progress',early,'Progress')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Foundation'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.foundation_buttons_mixin',PythonClass='LyraFoundation'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-foundation-after')!=before or visuals(bp,output,label+'-foundation-after')!=templates or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('foundation CDO/widget trees/animations/signatures changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or any(n.NodeGuid.as_dict()!=guids[g.get_name(),n.get_name()] for g,names in originals for n in g.Nodes if n.get_name() in names):raise RuntimeError('original foundation graphs/FText/parent calls/GUIDs changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('foundation transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete foundation Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='foundationbuttons',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_animations_ftext_parent_calls_delegates_and_graphs_preserved=True,native_text_forwarders_preserve_ftext_without_python_marshalling=True,empty_action_complete_stays_unconnected=True,fixture=localized_probe(stage),new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
