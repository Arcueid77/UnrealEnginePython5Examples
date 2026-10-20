"""Preserve original widget graphs and localized FText nodes behind typed gates."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node,raw_text
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.foundation_widgets_mixin import CLASSES,GATES,NATIVE_REASON

ASSETS={k:'Content/'+v.removeprefix('/Game/').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(dialog=3,reason=8,loading=15,aspect=8,spinner=4)
TRANSPORT=dict(dialog=4,reason=9,loading=4,aspect=6,spinner=4)

def gate(bp,key,params):
    g=ue.blueprint_add_function(bp,GATES[key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for name,p in params:entry.node_create_pin(1,kind(p),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original foundation widget required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-foundation-widget-before');templates=visuals(bp,output,label+'-before');event=bp.UbergraphPages[0];names={n.get_name() for n in event.Nodes};nodes={n.get_name():n for n in event.Nodes};total=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))
        if total!=TOTAL[label]:raise RuntimeError('original foundation widget footprint differs')
        if label=='dialog':points=[(nodes['K2Node_Event_0'],'then')];params=();methods=('BP_OnActivated',)
        elif label=='reason':points=[(nodes['K2Node_Event_1'],'then'),(nodes['K2Node_Event_2'],'then')];params=();methods=('Construct','Tick')
        elif label=='loading':points=[(nodes['K2Node_CustomEvent_0'],'then')];params=(('NewWidgetClass',nodes['K2Node_CustomEvent_0'].node_find_pin('NewWidgetClass')),);methods=('Construct','OnLoadingScreenWidgetChanged')
        elif label=='aspect':points=[(nodes['K2Node_Event_0'],'then'),(nodes['K2Node_Event_1'],'then')];params=();methods=('Construct','PreConstruct')
        else:points=[(nodes['K2Node_Event_0'],'then')];params=(('IsDesignTime',nodes['K2Node_Event_0'].node_find_pin('IsDesignTime')),);methods=('PreConstruct',)
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored=set()
        for node,pin in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored.update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        moved={'K2Node_CallFunction_1','K2Node_CallFunction_2','K2Node_FormatText_0','K2Node_VariableGet_0'} if label=='reason' else set();moved_ignore={('K2Node_CallFunction_1','execute'),('K2Node_CallFunction_2','InString')};moved_hash=semantics(event,moved,moved_ignore) if moved else None;original=semantics(event,names-moved,ignored);guids={n.get_name():n.NodeGuid.as_dict() for n in event.Nodes};literal=raw_text(nodes['K2Node_FormatText_0'],output/'reason-format-before.t3d') if moved else None
        if moved:
            writer=ue.blueprint_add_function(bp,NATIVE_REASON);entry=writer.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='string'),'Reason');result=writer.graph_add_node(K2Node_FunctionResult)
            for name in moved:move_node(event,writer,nodes[name])
            connect(entry,'then',nodes['K2Node_CallFunction_1'],'execute');connect(nodes['K2Node_CallFunction_1'],'then',result,'execute');connect(entry,'Reason',nodes['K2Node_CallFunction_2'],'InString');connect(nodes['K2Node_CallFunction_2'],'ReturnValue',nodes['K2Node_FormatText_0'],'Reason');connect(nodes['K2Node_FormatText_0'],'Result',nodes['K2Node_CallFunction_1'],'InText');connect(nodes['K2Node_VariableGet_0'],'ReasonTextWidget',nodes['K2Node_CallFunction_1'],'self')
        gate(bp,label,params);ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if moved:
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE_REASON));connect(nodes['K2Node_CallFunction_0'],'ReturnValue',call,'Reason')
            for node,pin in points:connect(node,pin,call,'execute')
        for node,pin in points:
            prior={n.get_name() for n in event.Nodes};insert_gate(event,node,pin,getattr(bp.GeneratedClass,GATES[label]));call,=[n for n in event.Nodes if n.get_name() not in prior and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_FoundationWidget'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.foundation_widgets_mixin',PythonClass='LyraFoundationWidget'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-foundation-widget-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('foundation widget CDO/visual/signature changed')
        if semantics(event,names-moved,ignored)!=original or any(n.NodeGuid.as_dict()!=guids[n.get_name()] for n in nodes.values()):raise RuntimeError('original foundation widget graph/GUID changed')
        if moved and (semantics(writer,moved,moved_ignore)!=moved_hash or raw_text(nodes['K2Node_FormatText_0'],output/'reason-format-after.t3d')!=literal):raise RuntimeError('native localized reason formatter changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('foundation widget transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),1):raise RuntimeError('complete foundation widget Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='foundationwidgets',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_animations_signatures_guids_and_graphs_preserved=True,native_localized_reason_format_and_setter_preserved_without_ftext_marshalling=True,loading_construct_factory_delegate_and_original_absence_of_destruct_unbind_preserved=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
