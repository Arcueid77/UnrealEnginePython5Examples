"""Preserve exposed-before-BeginPlay spawn,offline payload and original delays."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import kind
from generate_message_widget_assets import move_node
from generate_experience_screen_assets import payload_rows
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud import editor_experience_list_mixin as list_policy,editor_experience_portal_mixin as portal_policy
ASSETS={'list':'Content/System/DefaultEditorMap/B_ExperienceList3D.uasset','portal':'Content/System/DefaultEditorMap/B_TeleportToUserFacingExperience.uasset'}
def templates(bp,out,label):
    values={};scs=bp.get_property('SimpleConstructionScript')
    for n in scs.AllNodes:
        if n.ComponentTemplate is not None:
            file=out/(label+'-'+n.get_name()+'.t3d');ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(n.ComponentTemplate,str(file));values[n.get_name()]=file.read_bytes()
    return values
def declare(bp,name,params):
    graph=ue.blueprint_add_function(bp,name);start=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for param,pin in params:
        p=kind(pin)
        if pin.container_type:p.bIsReference=False;p.bIsConst=True
        start.node_create_pin(1,p,param)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(start,'then',result,'execute')
def native_group(bp,event,name,members,inputs,output,first,last):
    nodes={n.get_name():n for n in event.Nodes};links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members];graph=ue.blueprint_add_function(bp,name);start=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for param,(node,pin) in inputs.items():start.node_create_pin(1,kind(nodes[node].node_find_pin(pin)),param)
    result.node_create_pin(0,kind(nodes[output[0]].node_find_pin(output[1])),'ReturnValue')
    for n in members:move_node(event,graph,nodes[n])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    connect(start,'then',nodes[first],'execute');connect(nodes[last],'then',result,'execute');connect(nodes[output[0]],output[1],result,'ReturnValue')
    for param,(node,pin) in inputs.items():connect(start,param,nodes[node],pin)
    return graph
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[];pending=[]
    for label,policy,total,transport in (('portal',portal_policy,38,26),('list',list_policy,42,12)):
        if hashlib.sha256((stage/ASSETS[label]).read_bytes()).digest()!=hashlib.sha256((official/ASSETS[label]).read_bytes()).digest():raise RuntimeError('fresh default-editor actors required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,policy.CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-editor-before');components=templates(bp,out,label+'-editor-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes}
        if sum(len(ns) for _,ns in originals)!=total:raise RuntimeError('original default-editor footprint differs')
        names={'ReceiveBeginPlay'} if label=='list' else {'ReceiveBeginPlay','ReceiveActorBeginOverlap','LoadIntoExperience'};signatures={n:ue.describe_function(bp.GeneratedClass,n) for n in names};ignored={g.get_name():set() for g,_ in originals}
        if label=='list':
            moved={'K2Node_SpawnActorFromClass_0'};spawn=nodes['K2Node_SpawnActorFromClass_0'];points=[(nodes['K2Node_Event_0'],'then','begin',()),(nodes['K2Node_AsyncAction_0'],'Completed','loaded',(('Loaded',nodes['K2Node_AsyncAction_0'].node_find_pin('Loaded')),))];ignored[event.get_name()].update((('K2Node_MacroInstance_0','LoopBody'),('K2Node_CallArrayFunction_3','execute'),('K2Node_CallArrayFunction_3','NewItem')));inputs={'Experience':(spawn.get_name(),'UserFacingExperienceToLoad'),'Location':(spawn.get_name(),'SpawnTransform_Location'),'Rotation':(spawn.get_name(),'SpawnTransform_Rotation')};output=(spawn.get_name(),'ReturnValue');first=last=spawn.get_name();helper_name=policy.NATIVE['spawn']
        else:
            moved={'K2Node_CallFunction_12','K2Node_VariableSet_0','K2Node_Knot_18','K2Node_Knot_19'};points=[(nodes[n],pin,key,params) for n,pin,key,params in (('K2Node_DynamicCast_5','then','widget',(('Tile',nodes['K2Node_DynamicCast_5'].node_find_pin('AsW Experience Tile')),)),('K2Node_ExecutionSequence_1','then_1','color',(('Default',nodes['K2Node_VariableGet_5'].node_find_pin('bIsDefaultExperience')),)),('K2Node_Event_1','then','overlap',(('Other',nodes['K2Node_Event_1'].node_find_pin('OtherActor')),)),('K2Node_CustomEvent_2','then','load',(('ForPlayer',nodes['K2Node_CustomEvent_2'].node_find_pin('ForPlayer')),)),('K2Node_AsyncAction_1','AfterPush','pushed',(('ForPlayer',nodes['K2Node_Knot_22'].node_find_pin('OutputPin')),)))];ignored[event.get_name()].update((('K2Node_CallFunction_4','execute'),('K2Node_CallFunction_4','Request')));inputs={'Experience':('K2Node_CallFunction_12','self')};output=('K2Node_CallFunction_12','ReturnValue');first='K2Node_CallFunction_12';last='K2Node_VariableSet_0';helper_name=policy.NATIVE['request']
        for node,pin,_,_ in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[event.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,ns-(moved if g==event else set()),ignored[g.get_name()]) for g,ns in originals};group_hash=semantics(event,moved,set());group_before=payload_rows(nodes,moved);guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};scale_method=nodes['K2Node_SpawnActorFromClass_0'].node_find_pin('TransformScaleMethod').default_value if label=='list' else None;helper=native_group(bp,event,helper_name,moved,inputs,output,first,last)
        if label=='list':nodes['K2Node_SpawnActorFromClass_0'].node_find_pin('TransformScaleMethod').default_value=scale_method
        for _,_,key,params in points:declare(bp,policy.GATES[key],params)
        for key,target in ((('load','K2Node_CallFunction_4'),) if label=='list' else (('delay','K2Node_CallFunction_3'),('color','K2Node_CallFunction_5'),('push','K2Node_AsyncAction_1'))):
            alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=policy.NATIVE[key];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins();call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,helper_name))
        if label=='list':
            connect(nodes['K2Node_MacroInstance_0'],'LoopBody',call,'execute');connect(nodes['K2Node_MacroInstance_0'],'Array Element',call,'Experience');connect(nodes['K2Node_CallFunction_15'],'ReturnValue',call,'Location');connect(nodes['K2Node_CallFunction_22'],'ReturnValue',call,'Rotation');connect(call,'then',nodes['K2Node_CallArrayFunction_3'],'execute');connect(call,'ReturnValue',nodes['K2Node_CallArrayFunction_3'],'NewItem')
        else:
            connect(nodes['K2Node_AsyncAction_1'],'AfterPush',call,'execute');connect(nodes['K2Node_VariableGet_20'],'UserFacingExperienceToLoad',call,'Experience');connect(call,'then',nodes['K2Node_CallFunction_4'],'execute');connect(call,'ReturnValue',nodes['K2Node_CallFunction_4'],'Request')
        for node,pin,key,params in points:
            previous={n.get_name() for n in event.Nodes};insert_gate(event,node,pin,getattr(bp.GeneratedClass,policy.GATES[key]));gate,=[n for n in event.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(gate.node_find_pin(name))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset_name='DA_EditorExperience'+('List' if label=='list' else 'Portal')+'Mixin';asset=ue.create_asset(asset_name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';prefix='LyraEditorExperience'+('List' if label=='list' else 'Portal');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.editor_experience_'+('list' if label=='list' else 'portal')+'_mixin',PythonClass=prefix+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after={n:ue.describe_function(bp.GeneratedClass,n) for n in names};(out/(label+'-editor-signatures.json')).write_text(json.dumps(dict(before=signatures,after=after),indent=2),encoding='utf-8')
        if int(bp.Status)==2 or signatures!=after or snapshot(bp,label+'-editor-after')!=before or templates(bp,out,label+'-editor-after')!=components:raise RuntimeError('default-editor actor CDO/components/public ABI changed: '+label)
        comparison=dict(graphs={g.get_name():dict(before=hashes[g.get_name()],after=semantics(g,ns-(moved if g==event else set()),ignored[g.get_name()])) for g,ns in originals},helper=dict(before=group_hash,after=semantics(helper,moved,set())),guid_changes=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/(label+'-editor-partitions.json')).write_text(json.dumps(comparison,indent=2),encoding='utf-8');(out/(label+'-editor-native-payload.json')).write_text(json.dumps(dict(before=group_before,after=payload_rows(nodes,moved)),indent=2),encoding='utf-8')
        if any(v['before']!=v['after'] for v in comparison['graphs'].values()) or comparison['helper']['before']!=comparison['helper']['after'] or comparison['guid_changes']:raise RuntimeError('default-editor graph partitions/GUID changed: '+label)
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));actual=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
        if interface!=5 or actual!=transport:raise RuntimeError('default-editor transport differs: '+repr((label,actual)))
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(policy.METHODS)):raise RuntimeError('complete default-editor Profile family required')
        finally:ue.unregister_all_mixins()
        rows[label]=dict(original_nodes=total,transport_nodes=actual,interface_nodes=interface,method_counts=counts,original_cdos_scs_public_signatures_guids_graph_partitions_preserved=True);pending.extend([bp,asset]);saved.extend([ASSETS[label],'Content/UEPMixins/'+asset_name+'.uasset'])
    for obj in pending:obj.save_package()
    return dict(status='passed',kind='editorexperiences',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_native_empty_bundle_primary_async_and_expose_before_beginplay_spawn_preserved=True,original_additional_prepend_hidden_showall_and_accumulating_portal_cache_semantics_preserved=True,original_native_widget_delay_color_spinner_and_offline_request_payload_preserved=True,original_local_player_overlap_and_current_experience_afterpush_preserved=True,widgets=rows,new_business_nodes=0,native_end_adapter_nodes=0,assets=saved)
