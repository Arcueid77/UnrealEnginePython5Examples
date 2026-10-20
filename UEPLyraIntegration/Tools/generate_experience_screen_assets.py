"""Preserve native async login/push/loading macro and typed request payload IO."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.experience_screen_mixin import CLASS,METHODS,GATES,NATIVE

ASSET='Content/UI/Menu/Experiences/W_ExperienceSelectionScreen.uasset'
MACRO='Content/UI/Menu/Experiences/UIExperienceMacros.uasset'
TOTAL=42
TRANSPORT=49
POINTS=(('K2Node_Event_0','then','activate',None),('K2Node_ComponentBoundEvent_0','then','selected','ExperienceDef'),('K2Node_CustomEvent_0','then','spinner','ShouldShow'),('K2Node_ComponentBoundEvent_1','then','browse',None),('K2Node_ComponentBoundEvent_2','then','host',None),('K2Node_ComponentBoundEvent_3','then','quick',None),('K2Node_AsyncAction_5','OnInitializationComplete','browse_result','bSuccess'),('K2Node_AsyncAction_4','OnInitializationComplete','quick_result','bSuccess'),('K2Node_MacroInstance_2','then','prepared',None))

def payload_rows(nodes,members):
    rows=[]
    for name in sorted(members):
        node=nodes[name];pins=[]
        for pin in node.node_pins():pins.append(dict(name=pin.name,direction=pin.direction,category=pin.category,subcategory=pin.sub_category,type=pin.sub_category_object.get_path_name() if pin.sub_category_object is not None else None,container=pin.container_type,reference=pin.is_reference,const=pin.is_const,default=pin.default_value,text=str(pin.default_text_value),object=pin.default_object.get_path_name() if pin.default_object is not None else None,links=sorted((q.owning_node.get_name(),q.name) for q in pin.get_linked_to() if q.owning_node.get_name() in members)))
        try:ref=node.FunctionReference;function=[str(ref.MemberName),ref.MemberParent.get_path_name() if ref.MemberParent is not None else None,bool(ref.bSelfContext)]
        except Exception:function=None
        rows.append(dict(name=name,function=function,pins=pins))
    return rows

def gate(bp,key,params=(),output=None):
    graph=ue.blueprint_add_function(bp,GATES[key]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    if output:entry.ExtraFlags=int(entry.ExtraFlags)|0x40000000
    for name,pin in params:entry.node_create_pin(1,kind(pin),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original experience selection required')
    macro_hash=hashlib.sha256((stage/MACRO).read_bytes()).hexdigest();ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'experience-screen-before');tree=visuals(bp,out,'screen-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(ns) for _,ns in originals)
    if total!=TOTAL:raise RuntimeError('original selection footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};focus=next(g for g,_ in originals if g.get_name()=='BP_GetDesiredFocusTarget');fe=focus.Nodes[0];fr=next(n for n in focus.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');methods={focus.get_name()}
    for node in event.Nodes:
        if node.get_class().get_name()=='K2Node_Event':methods.add(str(node.EventReference.MemberName))
        if node.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):methods.add(str(node.CustomFunctionName))
    signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals};members={'K2Node_CallFunction_12','K2Node_VariableSet_0'}
    for node,pin,key,param in POINTS:
        target,=nodes[node].node_find_pin(pin).get_linked_to();ignored[event.get_name()].update(((node,pin),(target.owning_node.get_name(),target.name)))
    target,=fe.node_find_pin('then').get_linked_to();ignored[focus.get_name()].update(((fe.get_name(),'then'),(target.owning_node.get_name(),target.name)))
    ignored[event.get_name()].add(('K2Node_CallFunction_8','execute'));hashes={g.get_name():semantics(g,ns-(members if g==event else set()),ignored[g.get_name()]) for g,ns in originals};payload_hash=semantics(event,members,set());payload_before=payload_rows(nodes,members);guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
    proxy={key:dict(factory=str(nodes[name].ProxyFactoryFunctionName),class_name=nodes[name].ProxyClass.get_path_name()) for key,name in (('host','K2Node_AsyncAction_2'),('browse','K2Node_AsyncAction_5'),('quick','K2Node_AsyncAction_4'),('browser','K2Node_AsyncAction_0'))}
    if proxy['browse']['factory']!='LoginForOnlinePlay' or proxy['quick']['factory']!='LoginForOnlinePlay' or proxy['host']['factory']!='PushContentToLayerForPlayer' or proxy['browser']['factory']!='PushContentToLayerForPlayer':raise RuntimeError('original native selection async factories differ')
    # This function retains only typed request construction/constant setter IO.
    # The loading macro stays in EventGraph and its actual Completed edge gates
    # the Python continuation;latent class loading must never be made synchronous.
    request=ue.blueprint_add_function(bp,NATIVE['request']);re=request.Nodes[0];rr=request.graph_add_node(K2Node_FunctionResult);re.node_create_pin(1,kind(nodes['K2Node_CallFunction_12'].node_find_pin('self')),'Experience');rr.node_create_pin(0,kind(nodes['K2Node_CallFunction_12'].node_find_pin('ReturnValue')),'ReturnValue');internal=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members]
    for name in members:move_node(event,request,nodes[name])
    for a,p,b,q in internal:connect(nodes[a],p,nodes[b],q)
    connect(re,'then',nodes['K2Node_CallFunction_12'],'execute');connect(re,'Experience',nodes['K2Node_CallFunction_12'],'self');connect(nodes['K2Node_VariableSet_0'],'then',rr,'execute');connect(nodes['K2Node_CallFunction_12'],'ReturnValue',rr,'ReturnValue')
    for node,pin,key,param in POINTS:gate(bp,key,((param,nodes[node].node_find_pin(param)),) if param else ())
    gate(bp,'focus',output=fr.node_find_pin('ReturnValue'))
    for key,target in (('host','K2Node_AsyncAction_2'),('browse','K2Node_AsyncAction_5'),('quick','K2Node_AsyncAction_4'),('browser','K2Node_AsyncAction_0'),('prepare','K2Node_MacroInstance_2')):
        alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE[key];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2:raise RuntimeError('selection native async/request gate declaration compile failed')
    build=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE['request']));connect(nodes['K2Node_MacroInstance_2'],'then',build,'execute');connect(nodes['K2Node_VariableGet_5'],'SelectedExperience',build,'Experience');connect(build,'then',nodes['K2Node_CallFunction_8'],'execute');connect(build,'ReturnValue',nodes['K2Node_CallFunction_8'],'Request')
    for node,pin,key,param in POINTS:
        previous={n.get_name() for n in event.Nodes};insert_gate(event,nodes[node],pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in event.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
        if param:connect(nodes[node],param,call,param)
    target,=fe.node_find_pin('then').get_linked_to();call=focus.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES['focus']));branch=focus.graph_add_node(K2Node_IfThenElse);fe.node_find_pin('then').break_link_to(target);connect(fe,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=focus.graph_add_node(K2Node_FunctionResult);early.FunctionReference=fr.FunctionReference;focus.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,'ReturnValue')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_ExperienceScreenMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.experience_screen_mixin',PythonClass='LyraExperienceScreen'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();current={m:ue.describe_function(bp.GeneratedClass,m) for m in signatures};(out/'selection-public-signatures.json').write_text(json.dumps(dict(before=signatures,after=current),indent=2),encoding='utf-8')
    if int(bp.Status)==2 or signatures!=current or snapshot(bp,'experience-screen-after')!=before or visuals(bp,out,'screen-after')!=tree:raise RuntimeError('original selection defaults/tree/animation/public ABI changed')
    payload_after=payload_rows(nodes,members);comparison=dict(graphs={g.get_name():dict(before=hashes[g.get_name()],after=semantics(g,ns-(members if g==event else set()),ignored[g.get_name()])) for g,ns in originals},request=dict(before=payload_hash,after=semantics(request,members,set()),original_fixed_online_request_payload=True),guid_changes=[n.get_name() for n,value in guids.items() if n.NodeGuid.as_dict()!=value]);(out/'selection-partition-comparison.json').write_text(json.dumps(comparison,indent=2),encoding='utf-8');(out/'request-node-comparison.json').write_text(json.dumps(dict(before=payload_before,after=payload_after),indent=2),encoding='utf-8')
    if any(v['before']!=v['after'] for v in comparison['graphs'].values()) or comparison['request']['before']!=comparison['request']['after'] or comparison['guid_changes']:raise RuntimeError('original selection graph/native online request payload/GUID changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
    if interface!=5 or transport!=TRANSPORT:raise RuntimeError('selection transport count differs: '+str(transport))
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS)):raise RuntimeError('complete selection Profile family required')
    finally:ue.unregister_all_mixins()
    if hashlib.sha256((stage/MACRO).read_bytes()).hexdigest()!=macro_hash:raise RuntimeError('original shared macro definition changed')
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='experiencescreen',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_tree_animations_public_signatures_guids_and_graphs_preserved=True,original_native_login_push_factories_and_payloads_preserved=True,original_async_preparation_macro_completed_before_request_and_submit_preserved=True,original_browse_both_results_push_browser_quick_success_only_and_hidden_spinner_preserved=True,original_native_typed_request_payload_builder_preserved=True,shared_macro_definition_unchanged=True,shared_macro_sha256=macro_hash,original_async_factories=proxy,original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/'+name+'.uasset'])
