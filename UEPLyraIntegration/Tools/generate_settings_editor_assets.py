"""Settings presentation gates with native localized text/indexing adapters."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent,K2Node_CallArrayFunction,K2Node_GetArrayItem
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType,MemberReference
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.settings_editors_mixin import CLASSES,GATES,FOCUS,BROADCAST,OPTION_COUNT,OPTION_CREATE

ASSETS={k:'Content/'+v.removeprefix('/Game/').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(background=12,action=20,discrete=14,keyboard=14,missing=8,scalar=24,collection=17,rotator=37,details=13,extension=15)
TRANSPORT=dict(background=10,action=13,discrete=19,keyboard=13,missing=8,scalar=21,collection=13,rotator=12,details=4,extension=15)
COUNTS=dict(background=2,action=3,discrete=4,keyboard=3,missing=2,scalar=5,collection=3,rotator=3,details=1,extension=1)
PROBE='Content/UEPValidation/BP_SettingsEditorProbe.uasset'

def text_probe(stage):
    bp=ue.create_blueprint(ue.find_class('Actor'),'/Game/UEPValidation/BP_SettingsEditorProbe');source=ue.load_class('/ShooterCore/UserInterface/ScoreBoard/W_SB_TeamStat.W_SB_TeamStat_C')
    for label,name in (('details','SetupDetails'),):
        cls=ue.load_class(CLASSES[label]);g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Widget');text=g.graph_add_node_call_function(source.UEPSBLocalizedTeamName);text.node_find_pin('self').default_object=source.get_cdo();text.node_find_pin('Team').default_value='1';call=g.graph_add_node_call_function(getattr(cls,'SetupEntry' if label=='details' else 'OnSettingAssigned'));connect(entry,'then',text,'execute');connect(text,'then',call,'execute');connect(entry,'Widget',call,'self');connect(text,'ReturnValue',call,'Text' if label=='details' else 'ActionText')
        if label=='details':entry.node_create_pin(1,EdGraphPinType(PinCategory='bool'),'Selected');connect(entry,'Selected',call,'Selected')
    ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('localized settings editor probe compile failed')
    bp.save_package();return dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest())

def option_adapters(bp):
    cls=ue.find_class('GameSettingValueDiscrete');details=ue.load_class(CLASSES['details'])
    for name,is_count in ((OPTION_COUNT,True),(OPTION_CREATE,False)):
        g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Setting');result=g.graph_add_node(K2Node_FunctionResult);get=g.graph_add_node_call_function(cls.GetDiscreteOptions);connect(entry,'Setting',get,'self')
        if is_count:
            result.node_create_pin(0,EdGraphPinType(PinCategory='int'),'ReturnValue');length=ue.new_object(K2Node_CallArrayFunction,g);length.FunctionReference=MemberReference(MemberName='Array_Length',MemberParent=ue.find_class('KismetArrayLibrary'),bSelfContext=False);g.graph_add_node(length);connect(get,'ReturnValue',length,'TargetArray');connect(length,'ReturnValue',result,'ReturnValue');connect(entry,'then',result,'execute')
        else:
            entry.node_create_pin(1,EdGraphPinType(PinCategory='int'),'Index');entry.node_create_pin(1,EdGraphPinType(PinCategory='bool'),'Selected');item=g.graph_add_node(K2Node_GetArrayItem);connect(get,'ReturnValue',item,'Array');connect(entry,'Index',item,'Dimension 1');box=g.graph_add_node_variable_get('EnumOptions');create=g.graph_add_node_call_function(ue.find_class('DynamicEntryBox').BP_CreateEntryOfClass);create.node_find_pin('EntryClass').default_object=details;create.node_pin_default_value_changed(create.node_find_pin('EntryClass'));setup=g.graph_add_node_call_function(details.SetupEntry);connect(entry,'then',create,'execute');connect(box,'EnumOptions',create,'self');connect(create,'then',setup,'execute');connect(create,'ReturnValue',setup,'self');connect(item,'Output',setup,'Text');connect(entry,'Selected',setup,'Selected');connect(setup,'then',result,'execute')

def gate(bp,label,key,params,output=None):
    g=ue.blueprint_add_function(bp,GATES[label][key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for name,p in params:entry.node_create_pin(1,kind(p),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original settings editor required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-settings-before');templates=visuals(bp,output,label+'-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original settings editor footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};graphs={g.get_name():g for g,_ in originals};points=[];ret=None
        if label in ('background','action','discrete','keyboard','missing','scalar','collection'):
            for name,key in ((('K2Node_Event_1' if label=='background' else 'K2Node_Event_4'),'enter'),(('K2Node_Event_2' if label=='background' else 'K2Node_Event_5'),'leave')):points.append((event,nodes[name],'then',key,()))
        if label=='discrete':
            for name in ('K2Node_ComponentBoundEvent_0','K2Node_ComponentBoundEvent_1'):points.append((event,nodes[name],'then','sound',()))
        if label=='scalar':
            for name,key,param in (('K2Node_Event_0','value','Value'),('K2Node_Event_2','default','DefaultValue')):points.append((event,nodes[name],'then',key,((param,nodes[name].node_find_pin(param)),)))
        if label=='rotator':
            g=graphs['SetPipsStyle'];entry=g.Nodes[0];points.append((g,entry,'then','style',(('Count',entry.node_find_pin('Count')),)))
            for name,key,param in (('K2Node_Event_1','selected','Index'),('K2Node_Event_2','default','DefaultOptionIndex')):points.append((event,nodes[name],'then',key,((param,nodes[name].node_find_pin(param)),)))
        if label=='details':points.append((event,nodes['K2Node_CallFunction_0'],'then','selected',(('Selected',nodes['K2Node_CustomEvent_0'].node_find_pin('Selected')),)))
        if label=='extension':
            g=graphs['RebuildOptions'];entry=g.Nodes[0];points.append((g,entry,'then','rebuild',(('Setting',entry.node_find_pin('Setting')),)))
        if label in FOCUS:
            g=graphs['GetPrimaryGamepadFocusWidget'];entry=g.Nodes[0];result=next(n for n in g.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');ret=(g,entry,result)
        methods=set()
        for graph,_ in originals:
            if graph.get_name()!='EventGraph':
                try:ue.describe_function(bp.GeneratedClass,graph.get_name());methods.add(graph.get_name())
                except AttributeError:
                    if len(graph.Nodes)!=1 or graph.Nodes[0].get_class().get_name()!='K2Node_FunctionEntry':raise
            for n in graph.Nodes:
                if n.get_class().get_name()=='K2Node_Event':methods.add(str(n.EventReference.MemberName))
                if n.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):methods.add(str(n.CustomFunctionName))
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for graph,node,pin,key,params in points+([(ret[0],ret[1],'then','focus',())] if ret else []):
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals};guids={(g.get_name(),n.get_name()):n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        made=set()
        for g,node,pin,key,params in points:
            if key not in made:gate(bp,label,key,params);made.add(key)
        if ret:gate(bp,label,'focus',(),ret[2].node_find_pin('ReturnValue'))
        if label=='background':
            for key,n in (('enter','K2Node_CallDelegate_1'),('leave','K2Node_CallDelegate_0')):
                alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=BROADCAST[key];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[n],'execute')
        if label=='extension':option_adapters(bp)
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('settings native gate/adapter declaration compile failed: '+label)
        for g,node,pin,key,params in points:
            prior={n.get_name() for n in g.Nodes};insert_gate(g,node,pin,getattr(bp.GeneratedClass,GATES[label][key]));call,=[n for n in g.Nodes if n.get_name() not in prior and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        if ret:
            g,entry,result=ret;target,=entry.node_find_pin('then').get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[label]['focus']));branch=g.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=g.graph_add_node(K2Node_FunctionResult);early.FunctionReference=result.FunctionReference;g.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,'ReturnValue')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_SettingsEditor'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.settings_editors_mixin',PythonClass='LyraSettingsEditor'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-settings-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('settings editor CDO/visual/signature changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or any(n.NodeGuid.as_dict()!=guids[g.get_name(),n.get_name()] for g,names in originals for n in g.Nodes if n.get_name() in names):raise RuntimeError('original settings editor graphs/GUIDs changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('settings editor transport footprint differs: '+label)
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete settings editor Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='settingseditors',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_animations_signatures_guids_and_graphs_preserved=True,native_action_collection_labels_and_details_text_before_boolean_gate_preserved=True,native_enum_count_index_and_localized_text_factory_adapters=True,original_empty_background_delegate_body_retained=True,rotator_count_remains_invocation_local=True,settings_value_read_write_cpp_unchanged=True,fixture=text_probe(stage),new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
