"""Preserve native parent/RPC and original random data nodes behind typed ports."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_BreakStruct,K2Node_CallArrayFunction,K2Node_GetArrayItem
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile,MemberReference
from generate_dash_selector_assets import snapshot
from generate_message_widget_assets import move_node
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect,broadcast_graph
from uep_lyra_weapons.character_damage_mixin import CLASS,EXECUTE,RPC,LONG,SIDE,SELECT,ANIMATE,LENS_COUNT,LENS_OBJECT

RELATIVE='Content/GameplayCueNotifies/GCNL_Character_DamageTaken.uasset'
SET='Content/UEPMixins/DA_CharacterDamageMixin.uasset'
PROBE='Content/UEPValidation/BP_CharacterDamageProbe.uasset'
METHODS=('OnExecute','OnBurst','EvaluateWeakSpot','BroadcastDamageTaken',SELECT,ANIMATE,'MontageHit')


def kind(pin):
    return EdGraphPinType(PinCategory=pin.category,PinSubCategory=pin.sub_category,PinSubCategoryObject=pin.sub_category_object,bIsReference=pin.is_reference,bIsConst=pin.is_const)


def gate(bp,name,source,parameters):
    graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for field in parameters:entry.node_create_pin(1,kind(source.node_find_pin(field)),field)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')


def lens_accessors(bp):
    # FScriptInterface arrays are not supported by the generic Python property
    # reader. The VM only indexes/converts; Python still selects effect classes.
    for name,is_count in ((LENS_COUNT,True),(LENS_OBJECT,False)):
        graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='struct',PinSubCategoryObject=ue.find_struct('GameplayCueNotify_SpawnResult')),'SpawnResults')
        result=graph.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='int' if is_count else 'object',PinSubCategoryObject=None if is_count else ue.find_class('Object')),'ReturnValue')
        broken=graph.graph_add_node(K2Node_BreakStruct);broken.StructType=ue.find_struct('GameplayCueNotify_SpawnResult');graph.graph_reconstruct_node(broken)
        connect(entry,'SpawnResults',broken,'GameplayCueNotify_SpawnResult');connect(entry,'then',result,'execute')
        if is_count:
            length=ue.new_object(K2Node_CallArrayFunction,graph);length.FunctionReference=MemberReference(MemberName='Array_Length',MemberParent=ue.find_class('KismetArrayLibrary'),bSelfContext=False);graph.graph_add_node(length)
            connect(broken,'CameraLensEffects',length,'TargetArray');connect(length,'ReturnValue',result,'ReturnValue')
        else:
            entry.node_create_pin(1,EdGraphPinType(PinCategory='int'),'Index');item=graph.graph_add_node(K2Node_GetArrayItem)
            convert=graph.graph_add_node_call_function(ue.find_class('KismetSystemLibrary').Conv_InterfaceToObject)
            connect(broken,'CameraLensEffects',item,'Array');connect(entry,'Index',item,'Dimension 1');connect(item,'Output',convert,'Interface');connect(convert,'ReturnValue',result,'ReturnValue')


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent/RELATIVE
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256(official.read_bytes()).digest():raise RuntimeError('fresh character damage Cue required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'character-damage-before')
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in METHODS}
    if signatures['MontageHit']['flags']&(0x40|0x80|0x4000)!=(0x40|0x4000):raise RuntimeError('original unreliable multicast MontageHit required')
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    if sum(len(keys) for _,keys in originals)!=160:raise RuntimeError('original full character damage footprint differs')
    graphs={g.get_name():g for g,_ in originals};sg=graphs[SELECT];sn={n.get_name():n for n in sg.Nodes}
    groups=((LONG,['K2Node_Select_1','K2Node_Select_2','K2Node_Select_3','K2Node_CallFunction_4','K2Node_CallFunction_3'],'K2Node_PromotableOperator_3','K2Node_VariableSet_7'),
        (SIDE,['K2Node_Select_0','K2Node_Select_4','K2Node_Select_5','K2Node_CallFunction_5'],'K2Node_PromotableOperator_2','K2Node_VariableSet_6'))
    moved_names={n for _,names,_,_ in groups for n in names};rng_hashes={};moved_ignored={}
    for name,names,_,_ in groups:
        ignored={(names[0],'Index'),(names[0],'ReturnValue')};moved_ignored[name]=ignored;rng_hashes[name]=semantics(sg,set(names),ignored)
    eg=graphs['EventGraph'];en={n.get_name():n for n in eg.Nodes};execute=graphs['OnExecute'];xn={n.get_name():n for n in execute.Nodes}
    parent=xn['K2Node_CallParentFunction_0'];rpc=en['K2Node_CustomEvent_1'];ignored_by_graph={}
    for graph,node in ((execute,parent),(eg,rpc)):
        target,=node.node_find_pin('then').get_linked_to();ignored_by_graph[graph.get_name()]={(node.get_name(),'then'),(target.owning_node.get_name(),target.name)}
    hashes={g.get_name():semantics(g,keys-moved_names if g==sg else keys,ignored_by_graph.get(g.get_name(),set())) for g,keys in originals}
    helper_graphs={}
    for name,names,_,_ in groups:
        graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='bool'),'Positive')
        result=graph.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,kind(sn[names[0]].node_find_pin('ReturnValue')),'ReturnValue')
        for node_name in names:move_node(sg,graph,sn[node_name])
        # Restore the complete original pure RNG/select data topology.
        if name==LONG:
            connect(sn[names[1]],'ReturnValue',sn[names[0]],'Option 1');connect(sn[names[2]],'ReturnValue',sn[names[0]],'Option 0')
            connect(sn[names[3]],'ReturnValue',sn[names[1]],'Index');connect(sn[names[4]],'ReturnValue',sn[names[2]],'Index')
        else:
            connect(sn[names[1]],'ReturnValue',sn[names[0]],'Option 1');connect(sn[names[2]],'ReturnValue',sn[names[0]],'Option 0')
            connect(sn[names[3]],'ReturnValue',sn[names[1]],'Index');connect(sn[names[3]],'ReturnValue',sn[names[2]],'Index')
        connect(entry,'Positive',sn[names[0]],'Index');connect(sn[names[0]],'ReturnValue',result,'ReturnValue');connect(entry,'then',result,'execute');helper_graphs[name]=graph
    gate(bp,EXECUTE,xn['K2Node_FunctionEntry_0'],('MyTarget','Parameters'));gate(bp,RPC,rpc,('Character','Montage'))
    broadcast_graph(bp,'DamageVerb',ue.find_struct('LyraVerbMessage'),ue.find_class('GameplayMessageSubsystem'))
    lens_accessors(bp)
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for name,graph in helper_graphs.items():graph.Nodes[0].node_function_entry_set_pure(True)
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for name,names,condition,target in groups:
        call=sg.graph_add_node_call_function(getattr(bp.GeneratedClass,name));connect(sn[condition],'ReturnValue',call,'Positive');connect(call,'ReturnValue',sn[target],'Hit Montage Pick')
    for graph,node,method,source,fields in ((execute,parent,EXECUTE,xn['K2Node_FunctionEntry_0'],('MyTarget','Parameters')),(eg,rpc,RPC,rpc,('Character','Montage'))):
        old={n.get_name() for n in graph.Nodes};insert_gate(graph,node,'then',getattr(bp.GeneratedClass,method));call,=[n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction']
        for field in fields:connect(source,field,call,field)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_CharacterDamageMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python'
    asset.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule='uep_lyra_weapons.character_damage_mixin',PythonClass='LyraCharacterDamage'+name+'Profile') for name in ('Python','BlueprintFallback')]
    ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'character-damage-after')!=before or any(ue.describe_function(bp.GeneratedClass,n)!=v for n,v in signatures.items()):raise RuntimeError('original damage CDO/ABI/RPC changed')
    if any(semantics(g,keys-moved_names if g==sg else keys,ignored_by_graph.get(g.get_name(),set()))!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('original damage graph changed outside transports')
    if any(semantics(helper_graphs[name],set(names),moved_ignored[name])!=rng_hashes[name] for name,names,_,_ in groups):raise RuntimeError('original native RNG/select data topology changed')
    interface_nodes=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-160!=25+interface_nodes:raise RuntimeError('damage transport footprint differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={n:len(v['functions']) for n,v in row['profiles'].items()}
        if counts!=dict(Python=7,BlueprintFallback=7):raise RuntimeError('seven-method damage family required')
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_CharacterDamageProbe')
    for name,method,inputs,out_name in (('Weak','EvaluateWeakSpot',('Object',),'DidHitWeakSpot'),('Select',SELECT,('Hit Normal','Hit Actor'),'Hit Montage')):
        graph=ue.blueprint_add_function(probe,name);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=bp.GeneratedClass),'Cue')
        call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,method));result=graph.graph_add_node(K2Node_FunctionResult)
        connect(entry,'Cue',call,'self');connect(entry,'then',call,'execute');connect(call,'then',result,'execute')
        for field in inputs:entry.node_create_pin(1,kind(call.node_find_pin(field)),field.replace(' ',''));connect(entry,field.replace(' ',''),call,field)
        result.node_create_pin(0,kind(call.node_find_pin(out_name)),'Value');connect(call,out_name,result,'Value')
    ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('typed damage helper callers failed')
    for value in (bp,asset,probe):value.save_package()
    return dict(status='passed',kind='characterdamage',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdo_event_signatures_business_and_rpc_preserved=True,original_graph_nodes=160,transport_nodes=25,interface_nodes=interface_nodes,new_business_nodes=0,native_end_adapter_nodes=0,
        native_parent_burst_effects_and_lifetime_timer_preserved=True,original_unreliable_multicast_shell_preserved=True,rpc_function_overridden=False,
        original_native_rng_nodes_ranges_and_select_topology_retained=True,typed_native_message_thunk_adapter=True,generic_native_interface_array_count_and_object_accessors=True,actual_registered_profile_method_counts=counts,
        caller_probe=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=[RELATIVE,SET])
