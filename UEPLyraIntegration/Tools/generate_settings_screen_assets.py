"""Preserve native async input/loading/messages and opaque tab descriptors."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.settings_screens_mixin import CLASSES,GATES,REGISTER_NATIVE,ACTIONS

ASSETS={k:'Content/'+v.removeprefix('/Game/').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(gamma=3,hdr=7,screen=37,panel=3)
TRANSPORT=dict(gamma=5,hdr=8,screen=26,panel=4)
COUNTS=dict(gamma=1,hdr=2,screen=5,panel=1)

def gate(bp,label,key,params,output=None):
    g=ue.blueprint_add_function(bp,GATES[label][key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    if label=='gamma':entry.set_property('ExtraFlags',int(entry.get_property('ExtraFlags'))|0x40000000)
    for name,p in params:entry.node_create_pin(1,kind(p),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original settings screen required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-screen-before');templates=visuals(bp,output,label+'-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original settings screen footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};graphs={g.get_name():g for g,_ in originals};points=[];ret=None;moved=set();mi=set()
        if label=='gamma':
            g=graphs['BP_GetDesiredFocusTarget'];entry=g.Nodes[0];result=next(n for n in g.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');ret=(g,entry,result)
        elif label=='hdr':
            points=[(event,nodes['K2Node_Event_0'],'then','construct',()),(event,nodes['K2Node_Event_1'],'then','luminance',(('InMaxLuminance',nodes['K2Node_Event_1'].node_find_pin('InMaxLuminance')),))]
        elif label=='panel':
            g=graphs['OnSettingScreenAnim'];points=[(g,g.Nodes[0],'then','animate',())]
        else:
            g=graphs['RegisterTopLevelTab'];entry=g.Nodes[0];points=[(g,entry,'then','register',(('SettingDevName',entry.node_find_pin('SettingDevName')),)),(event,nodes['K2Node_Event_1'],'then','construct',()),(event,nodes['K2Node_Event_0'],'then','activate',()),(event,nodes['K2Node_ComponentBoundEvent_0'],'then','navigate',(('TabId',nodes['K2Node_ComponentBoundEvent_0'].node_find_pin('TabId')),)),(event,nodes['K2Node_ComponentBoundEvent_1'],'then','action',tuple((n,nodes['K2Node_ComponentBoundEvent_1'].node_find_pin(n)) for n in ('Setting','Action')))]
            tab_nodes={n.get_name():n for n in g.Nodes};moved={'K2Node_VariableGet_0','K2Node_CallFunction_11','K2Node_MakeStruct_1','K2Node_CallFunction_13'};mi={('K2Node_CallFunction_11','execute'),('K2Node_MakeStruct_1','TabId'),('K2Node_MakeStruct_1','bHidden'),('K2Node_CallFunction_13','self')};mh=semantics(g,moved,mi)
        methods=set()
        for graph,_ in originals:
            if graph.get_name()!='EventGraph':methods.add(graph.get_name())
            for n in graph.Nodes:
                if n.get_class().get_name()=='K2Node_Event':methods.add(str(n.EventReference.MemberName))
                if n.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):methods.add(str(n.CustomFunctionName))
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for g,node,pin,key,params in points+([(ret[0],ret[1],'then','focus',())] if ret else []):
            target,=node.node_find_pin(pin).get_linked_to();ignored[g.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n-(moved if label=='screen' and g.get_name()=='RegisterTopLevelTab' else set()),ignored[g.get_name()]) for g,n in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        if moved:
            source=graphs['RegisterTopLevelTab'];writer=ue.blueprint_add_function(bp,REGISTER_NATIVE);entry=writer.Nodes[0];entry.node_create_pin(1,kind(source.Nodes[0].node_find_pin('SettingDevName')),'SettingDevName');entry.node_create_pin(1,kind(tab_nodes['K2Node_CallFunction_10'].node_find_pin('ReturnValue')),'Collection');entry.node_create_pin(1,EdGraphPinType(PinCategory='bool'),'Hidden');result=writer.graph_add_node(K2Node_FunctionResult)
            for name in moved:move_node(source,writer,tab_nodes[name])
            connect(entry,'then',tab_nodes['K2Node_CallFunction_11'],'execute');connect(tab_nodes['K2Node_CallFunction_11'],'then',result,'execute');connect(entry,'SettingDevName',tab_nodes['K2Node_MakeStruct_1'],'TabId');connect(entry,'Collection',tab_nodes['K2Node_CallFunction_13'],'self');connect(entry,'Hidden',tab_nodes['K2Node_MakeStruct_1'],'bHidden');connect(tab_nodes['K2Node_VariableGet_0'],'TopSettingsTabs',tab_nodes['K2Node_CallFunction_11'],'self');connect(tab_nodes['K2Node_CallFunction_13'],'ReturnValue',tab_nodes['K2Node_MakeStruct_1'],'TabText');connect(tab_nodes['K2Node_MakeStruct_1'],'LyraTabDescriptor',tab_nodes['K2Node_CallFunction_11'],'TabDescriptor')
        for g,node,pin,key,params in points:gate(bp,label,key,params)
        if ret:gate(bp,label,'focus',(),ret[2].node_find_pin('ReturnValue'))
        if label=='screen':
            for route,node in (('UEPSettingsScreenPushSafeZone','K2Node_AsyncAction_1'),('UEPSettingsScreenPushGamma','K2Node_AsyncAction_2'),('UEPSettingsScreenPushHDR','K2Node_AsyncAction_0')):
                alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=route;event.graph_reconstruct_node(alias);connect(alias,'then',nodes[node],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('settings screen native gate declaration compile failed: '+label)
        if moved:
            source=graphs['RegisterTopLevelTab'];call=source.graph_add_node_call_function(getattr(bp.GeneratedClass,REGISTER_NATIVE));connect(tab_nodes['K2Node_CallFunction_10'],'then',call,'execute');connect(source.Nodes[0],'SettingDevName',call,'SettingDevName');connect(tab_nodes['K2Node_CallFunction_10'],'ReturnValue',call,'Collection');connect(tab_nodes['K2Node_CallFunction_12'],'ReturnValue',call,'Hidden')
        for g,node,pin,key,params in points:
            prior={n.get_name() for n in g.Nodes};insert_gate(g,node,pin,getattr(bp.GeneratedClass,GATES[label][key]));call,=[n for n in g.Nodes if n.get_name() not in prior and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        if ret:
            g,entry,result=ret;target,=entry.node_find_pin('then').get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[label]['focus']));branch=g.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=g.graph_add_node(K2Node_FunctionResult);early.FunctionReference=result.FunctionReference;g.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,'ReturnValue')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_SettingsScreen'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.settings_screens_mixin',PythonClass='LyraSettingsScreen'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        current_signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in signatures};(output/(label+'-signatures.json')).write_text(json.dumps(dict(before=signatures,after=current_signatures),indent=2),encoding='utf-8')
        compared={m:dict(v) for m,v in current_signatures.items()}
        if label=='screen':
            # FUNC_HasDefaults describes nontrivial local frame storage, which
            # moves with the native FText/descriptor nodes. No public ABI bit,
            # parameter, const/access/net flag or other function may change.
            oldsig=signatures['RegisterTopLevelTab'];newsig=current_signatures['RegisterTopLevelTab']
            if oldsig['flags']^newsig['flags']!=0x00800000:raise RuntimeError('unexpected native tab frame-flag delta')
            compared['RegisterTopLevelTab']['flags']=oldsig['flags']
        if int(bp.Status)==2 or snapshot(bp,label+'-screen-after')!=before or visuals(bp,output,label+'-after')!=templates or compared!=signatures:raise RuntimeError('settings screen CDO/visual/public signature changed: '+label)
        if any(semantics(g,n-(moved if label=='screen' and g.get_name()=='RegisterTopLevelTab' else set()),ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original settings screen graphs/GUIDs changed')
        if moved and semantics(writer,moved,mi)!=mh:raise RuntimeError('opaque native tab descriptor/display-name nodes changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('settings screen transport footprint differs: '+label)
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete settings screen Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='settingsscreens',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_animations_signatures_guids_and_graphs_preserved=True,original_async_soft_class_input_suspension_afterpush_and_interface_payload_paths_retained=True,original_native_tab_descriptor_display_name_icon_brush_and_button_class_preserved=True,original_const_gamma_focus_signature_preserved=True,register_tab_signature_only_internal_hasdefaults_frame_flag_changed=True,settings_apply_save_reset_and_native_calibration_cpp_unchanged=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
