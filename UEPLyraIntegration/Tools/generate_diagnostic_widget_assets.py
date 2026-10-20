"""Move original FText/number-format nodes intact into native rendering helpers."""
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
from uep_lyra_hud.diagnostic_widgets_mixin import CLASSES,GATES,NATIVE_PRE,NATIVE_VALUE,NATIVE_BUILD,NATIVE_NAME,NATIVE_USER,NATIVE_MISSING

ASSETS={k:'Content/'+v.removeprefix('/Game/').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(graph=22,text=23,build=6,watermark=24)
TRANSPORT=dict(graph=14,text=14,build=7,watermark=14)
COUNTS=dict(graph=2,text=2,build=1,watermark=1)
PRE={'K2Node_CallFunction_4','K2Node_VariableGet_3','K2Node_VariableGet_4','K2Node_FormatText_0','K2Node_CallFunction_7','K2Node_VariableGet_9','K2Node_VariableGet_5','K2Node_VariableGet_6','K2Node_CallFunction_5'}
VALUE={'K2Node_FormatText_1','K2Node_CallFunction_8','K2Node_VariableGet_10','K2Node_VariableGet_7','K2Node_VariableGet_8','K2Node_CallFunction_6'}
NAME={'K2Node_Knot_0','K2Node_FormatText_0','K2Node_VariableGet_6','K2Node_VariableGet_0','K2Node_CallFunction_2'}
USER={'K2Node_CallFunction_9','K2Node_VariableSet_0','K2Node_VariableGet_4','K2Node_CallFunction_11','K2Node_CallFunction_13'}
MISSING={'K2Node_VariableSet_1','K2Node_VariableGet_3','K2Node_CallFunction_10'}

def gate(bp,label,key):
    g=ue.blueprint_add_function(bp,GATES[label][key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')

def render_group(bp,event,nodes,name,members,params):
    links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members]
    g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for field,p in params:entry.node_create_pin(1,kind(p),field)
    for member in members:move_node(event,g,nodes[member])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    return g,entry,result

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original diagnostic widget required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-diagnostic-before');templates=visuals(bp,output,label+'-before');event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};names=set(nodes);total=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))
        if total!=TOTAL[label]:raise RuntimeError('original diagnostic widget footprint differs')
        groups={};points=[];ignored=set();params={};literals={}
        if label in ('graph','text'):
            groups={NATIVE_PRE:PRE,NATIVE_VALUE:VALUE};points=[(nodes['K2Node_Event_3'],'pre'),(nodes['K2Node_Event_2'],'tick')];params={NATIVE_PRE:(),NATIVE_VALUE:(('Value',nodes['K2Node_CallFunction_8'].node_find_pin('Value')),)}
        elif label=='build':
            groups={NATIVE_BUILD:{'K2Node_FormatText_0','K2Node_VariableGet_0','K2Node_CallFunction_2'}};points=[(nodes['K2Node_Event_1'],'construct')];params={NATIVE_BUILD:tuple((n,nodes['K2Node_FormatText_0'].node_find_pin(n)) for n in ('BuildVer','BuildConfig'))};literals['K2Node_FormatText_0']=raw_text(nodes['K2Node_FormatText_0'],output/'build-format-before.t3d')
        else:
            groups={NATIVE_NAME:NAME,NATIVE_USER:USER,NATIVE_MISSING:MISSING};points=[(nodes['K2Node_Event_3'],'tick')];number=nodes['K2Node_PromotableOperator_0'].node_find_pin('ReturnValue');params={NATIVE_NAME:(('PlayerNum',number),),NATIVE_USER:(('Nickname',nodes['K2Node_CallFunction_5'].node_find_pin('ReturnValue')),('Debug',nodes['K2Node_CallFunction_12'].node_find_pin('ReturnValue')),('PlayerNum',number)),NATIVE_MISSING:(('PlayerNum',number),)}
            for name in ('K2Node_FormatText_0','K2Node_VariableSet_1'):literals[name]=raw_text(nodes[name],output/(name+'-before.t3d'))
        moved=set().union(*groups.values());remaining=names-moved
        for node,key in points:
            target,=node.node_find_pin('then').get_linked_to();ignored.update(((node.get_name(),'then'),(target.owning_node.get_name(),target.name)))
        partitions={'remaining':remaining,**groups};hashes={key:semantics(event,members,ignored if key=='remaining' else set()) for key,members in partitions.items()};guids={n:n.NodeGuid.as_dict() for n in event.Nodes};signatures={}
        for node,_ in points:signatures[str(node.EventReference.MemberName)]=ue.describe_function(bp.GeneratedClass,str(node.EventReference.MemberName))
        helper={name:render_group(bp,event,nodes,name,members,params[name]) for name,members in groups.items()}
        if label in ('graph','text'):
            g,e,r=helper[NATIVE_PRE];connect(e,'then',nodes['K2Node_CallFunction_4'],'execute');connect(nodes['K2Node_CallFunction_5'],'then',r,'execute');g,e,r=helper[NATIVE_VALUE];connect(e,'then',nodes['K2Node_CallFunction_6'],'execute');connect(e,'Value',nodes['K2Node_CallFunction_8'],'Value');connect(nodes['K2Node_CallFunction_6'],'then',r,'execute')
        elif label=='build':
            g,e,r=helper[NATIVE_BUILD];connect(e,'then',nodes['K2Node_CallFunction_2'],'execute');connect(nodes['K2Node_CallFunction_2'],'then',r,'execute')
            for name in ('BuildVer','BuildConfig'):connect(e,name,nodes['K2Node_FormatText_0'],name)
        else:
            g,e,r=helper[NATIVE_NAME];connect(e,'then',nodes['K2Node_Knot_0'],'InputPin');connect(e,'PlayerNum',nodes['K2Node_FormatText_0'],'PlayerNum');connect(nodes['K2Node_CallFunction_2'],'then',r,'execute');g,e,r=helper[NATIVE_USER];connect(e,'then',nodes['K2Node_VariableSet_0'],'execute');connect(e,'Nickname',nodes['K2Node_CallFunction_9'],'InString');connect(e,'Debug',nodes['K2Node_CallFunction_13'],'InString');g,e,r=helper[NATIVE_MISSING];connect(e,'then',nodes['K2Node_VariableSet_1'],'execute')
        for node,key in points:gate(bp,label,key)
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('diagnostic native formatter declaration compile failed: '+label)
        if label in ('graph','text'):
            pre=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE_PRE));connect(nodes['K2Node_Event_3'],'then',pre,'execute')
            if label=='text':connect(pre,'then',nodes['K2Node_CallFunction_10'],'execute')
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE_VALUE));connect(nodes['K2Node_PromotableOperator_0'],'ReturnValue',call,'Value')
            if label=='graph':connect(nodes['K2Node_CallFunction_1'],'then',call,'execute')
            else:connect(nodes['K2Node_Event_2'],'then',call,'execute')
        elif label=='build':
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE_BUILD));connect(nodes['K2Node_Event_1'],'then',call,'execute');connect(nodes['K2Node_CallFunction_0'],'ReturnValue',call,'BuildVer');connect(nodes['K2Node_CallFunction_1'],'ReturnValue',call,'BuildConfig')
        else:
            for name,last in ((NATIVE_USER,'K2Node_CallFunction_11'),(NATIVE_MISSING,'K2Node_CallFunction_10')):
                g,e,r=helper[name];call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE_NAME));connect(nodes[last],'then',call,'execute');connect(e,'PlayerNum',call,'PlayerNum');connect(call,'then',r,'execute')
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE_USER));connect(nodes['K2Node_MacroInstance_1'],'Is Valid',call,'execute');connect(nodes['K2Node_CallFunction_5'],'ReturnValue',call,'Nickname');connect(nodes['K2Node_CallFunction_12'],'ReturnValue',call,'Debug');connect(nodes['K2Node_PromotableOperator_0'],'ReturnValue',call,'PlayerNum');missing=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE_MISSING));connect(nodes['K2Node_MacroInstance_0'],'Is Not Valid',missing,'execute');connect(nodes['K2Node_MacroInstance_1'],'Is Not Valid',missing,'execute');connect(nodes['K2Node_PromotableOperator_0'],'ReturnValue',missing,'PlayerNum')
        for node,key in points:insert_gate(event,node,'then',getattr(bp.GeneratedClass,GATES[label][key]))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Diagnostic'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.diagnostic_widgets_mixin',PythonClass='LyraDiagnostic'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-diagnostic-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('diagnostic widget CDO/visual/signature changed: '+label)
        current_hashes={'remaining':semantics(event,remaining,ignored),**{name:semantics(helper[name][0],members,set()) for name,members in groups.items()}};bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v];(output/(label+'-partition-checks.json')).write_text(json.dumps(dict(before=hashes,after=current_hashes,bad_guids=bad_guids),indent=2),encoding='utf-8')
        if current_hashes!=hashes or bad_guids:raise RuntimeError('original diagnostic node partition/GUID changed: '+label)
        for literal_name,value in literals.items():
            if raw_text(nodes[literal_name],output/(literal_name+'-after.t3d'))!=value:raise RuntimeError('original diagnostic localized literal changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('diagnostic widget transport footprint differs: '+label)
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete diagnostic Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='diagnosticwidgets',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_signatures_node_guids_and_native_format_node_partitions_preserved=True,original_numeric_grouping_rounding_fractional_digits_and_ftext_formats_preserved=True,original_missing_user_localized_status_and_name_format_preserved=True,performance_graph_native_update_before_fetch_and_numeric_scale_preserved=True,native_user_subsystem_getters_context_game_and_int32_player_display_number_preserved=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
