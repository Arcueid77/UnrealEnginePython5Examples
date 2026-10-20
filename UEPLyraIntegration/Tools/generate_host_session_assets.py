"""Host screen policy with original opaque text, async preparation and delegate IO."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent,K2Node_VariableGet
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node,raw_text
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.host_session_mixin import CLASS,METHODS,GATES,NATIVE

ASSET='Content/UI/Menu/Experiences/W_HostSessionScreen.uasset'
MACRO='Content/UI/Menu/Experiences/UIExperienceMacros.uasset'
TOTAL=75
TRANSPORT=66

def group(bp,source,name,members,first,last):
    nodes={n.get_name():n for n in source.Nodes};links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in source.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members];graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for member in members:move_node(source,graph,nodes[member])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    connect(entry,'then',nodes[first],'execute');connect(nodes[last],'then',result,'execute');return graph

def gate(bp,key,params=(),output=None):
    graph=ue.blueprint_add_function(bp,GATES[key]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    if key=='focus':entry.ExtraFlags=int(entry.ExtraFlags)|0x40000000
    for name,pin in params:entry.node_create_pin(1,kind(pin),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original host screen required')
    macro_hash=hashlib.sha256((stage/MACRO).read_bytes()).hexdigest();ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'host-screen-before');tree=visuals(bp,out,'host-before');graphs={g.get_name():g for g in ue.blueprint_get_all_graphs(bp)};originals=[(g,{n.get_name() for n in g.Nodes}) for g in graphs.values()];total=sum(len(ns) for _,ns in originals)
    if total!=TOTAL:raise RuntimeError('original host footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};mode=graphs['UpdateOnlineModeText'];mn={n.get_name():n for n in mode.Nodes};bots=graphs['UpdateBotsEnabledText'];bn={n.get_name():n for n in bots.Nodes};request=graphs['CreateHostingRequest'];rn={n.get_name():n for n in request.Nodes};focus=graphs['BP_GetDesiredFocusTarget'];fe=focus.Nodes[0];fr=next(n for n in focus.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');rr=next(n for n in request.Nodes if n.get_class().get_name()=='K2Node_FunctionResult')
    if rn['K2Node_CallFunction_0'].node_find_pin('Key').default_value!='NumBots' or rn['K2Node_CallFunction_0'].node_find_pin('Value').default_value!='0':raise RuntimeError('original bot URL override differs')
    points=[(mode,mode.Nodes[0],'then','mode_text',()),(bots,bots.Nodes[0],'then','bots_text',()),(event,nodes['K2Node_Event_1'],'then','activate',()),(event,nodes['K2Node_ComponentBoundEvent_3'],'then','mode_cycle',()),(event,nodes['K2Node_ComponentBoundEvent_1'],'then','bots_toggle',()),(event,nodes['K2Node_ComponentBoundEvent_0'],'then','selected',(('Experience',nodes['K2Node_ComponentBoundEvent_0'].node_find_pin('ExperienceDef')),)),(event,nodes['K2Node_AsyncAction_4'],'OnInitializationComplete','online_result',(('Success',nodes['K2Node_AsyncAction_4'].node_find_pin('bSuccess')),)),(event,nodes['K2Node_AsyncAction_1'],'AfterPush','spinner_pushed',(('Widget',nodes['K2Node_AsyncAction_1'].node_find_pin('UserWidget')),)),(event,nodes['K2Node_MacroInstance_3'],'then','prepared',()),(event,nodes['K2Node_RemoveDelegate_0'],'then','completed',(('Success',nodes['K2Node_BreakStruct_0'].node_find_pin('bWasSuccessful')),))]
    methods={g.get_name() for g,_ in originals if g.get_name()!='EventGraph'}
    for node in event.Nodes:
        if node.get_class().get_name()=='K2Node_Event':methods.add(str(node.EventReference.MemberName))
        if node.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):methods.add(str(node.CustomFunctionName))
    signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};groups={NATIVE['mode_text']:(mode,{n.get_name() for n in mode.Nodes if n!=mode.Nodes[0]},'K2Node_CallFunction_8','K2Node_CallFunction_8'),NATIVE['bots_on']:(bots,{'K2Node_VariableGet_3','K2Node_CallFunction_0'},'K2Node_CallFunction_0','K2Node_CallFunction_0'),NATIVE['bots_off']:(bots,{'K2Node_CallFunction_8'},'K2Node_CallFunction_8','K2Node_CallFunction_8')};text_before={'mode':raw_text(mn['K2Node_Select_2'],out/'mode-text-before.t3d'),'on':raw_text(bn['K2Node_CallFunction_0'],out/'bots-on-before.t3d'),'off':raw_text(bn['K2Node_CallFunction_8'],out/'bots-off-before.t3d')};ignored={g.get_name():set() for g,_ in originals}
    for graph,node,pin,_,_ in points+[(focus,fe,'then','focus',()),(request,request.Nodes[0],'then','request',())]:
        target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
    ignored[bots.get_name()].update((('K2Node_IfThenElse_0','then'),('K2Node_IfThenElse_0','else')));ignored[event.get_name()].update((('K2Node_CallFunction_8','then'),('K2Node_AddDelegate_0','execute'),('K2Node_CallFunction_4','Request')))
    moved={g.get_name():set().union(*(members for src,members,_,_ in groups.values() if src==g)) if any(src==g for src,_,_,_ in groups.values()) else set() for g,_ in originals};hashes={g.get_name():semantics(g,ns-moved[g.get_name()],ignored[g.get_name()]) for g,ns in originals};group_hashes={name:semantics(src,members,set()) for name,(src,members,_,_) in groups.items()};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};text_ref=bn['K2Node_VariableGet_3'].VariableReference.as_dict();helpers={name:group(bp,src,name,members,first,last) for name,(src,members,first,last) in groups.items()}
    off=helpers[NATIVE['bots_off']];getter=off.graph_add_node(K2Node_VariableGet);getter.VariableReference=ue.find_struct('MemberReference')(**text_ref);off.graph_reconstruct_node(getter);connect(getter,'BotsToggleText',bn['K2Node_CallFunction_8'],'self')
    for graph,node,pin,key,params in points:gate(bp,key,params)
    gate(bp,'focus',output=fr.node_find_pin('ReturnValue'));gate(bp,'request',output=rr.node_find_pin('OutputPin'))
    for key,target in (('login','K2Node_AsyncAction_4'),('spinner','K2Node_AsyncAction_1'),('prepare','K2Node_MacroInstance_3'),('failure','K2Node_CallFunction_14'),('submit','K2Node_AddDelegate_0')):
        alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE[key];event.graph_reconstruct_node(alias)
        if key=='submit':alias.node_create_pin(1,kind(nodes['K2Node_CallFunction_8'].node_find_pin('OutputPin')),'Request');nodes['K2Node_CallFunction_8'].node_find_pin('OutputPin').break_link_to(nodes['K2Node_CallFunction_4'].node_find_pin('Request'));connect(alias,'Request',nodes['K2Node_CallFunction_4'],'Request')
        connect(alias,'then',nodes[target],'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2:raise RuntimeError('host native text/async/binding gates compile failed')
    call=mode.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE['mode_text']));connect(mode.Nodes[0],'then',call,'execute')
    for key,pin in (('bots_on','then'),('bots_off','else')):call=bots.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE[key]));connect(bn['K2Node_IfThenElse_0'],pin,call,'execute')
    target,=nodes['K2Node_CallFunction_8'].node_find_pin('then').get_linked_to();nodes['K2Node_CallFunction_8'].node_find_pin('then').break_link_to(target);call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE['submit']));connect(nodes['K2Node_CallFunction_8'],'then',call,'execute');connect(nodes['K2Node_CallFunction_8'],'OutputPin',call,'Request')
    for graph,node,pin,key,params in points:
        previous={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
        for name,p in params:p.make_link_to(call.node_find_pin(name))
    for graph,entry,result,key,output in ((focus,fe,fr,'focus','ReturnValue'),(request,request.Nodes[0],rr,'request','OutputPin')):
        target,=entry.node_find_pin('then').get_linked_to();call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[key]));branch=graph.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=graph.graph_add_node(K2Node_FunctionResult);early.FunctionReference=result.FunctionReference;graph.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,output)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset_name='DA_HostSessionMixin';asset=ue.create_asset(asset_name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.host_session_mixin',PythonClass='LyraHostSession'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();current={m:ue.describe_function(bp.GeneratedClass,m) for m in signatures};comparison={m:dict(v) for m,v in current.items()}
    for method in ('UpdateOnlineModeText','UpdateBotsEnabledText'):
        if signatures[method]['flags']^current[method]['flags'] not in (0,0x00800000):raise RuntimeError('unexpected host public text signature flags changed')
        comparison[method]['flags']=signatures[method]['flags']
    (out/'host-public-signatures.json').write_text(json.dumps(dict(before=signatures,after=current,only_internal_text_frame_hasdefaults_may_move=True),indent=2),encoding='utf-8')
    if int(bp.Status)==2 or comparison!=signatures or snapshot(bp,'host-screen-after')!=before or visuals(bp,out,'host-after')!=tree:raise RuntimeError('host CDO/tree/animation/public ABI changed')
    partition=dict(graphs={g.get_name():dict(before=hashes[g.get_name()],after=semantics(g,ns-moved[g.get_name()],ignored[g.get_name()])) for g,ns in originals},helpers={name:dict(before=group_hashes[name],after=semantics(helpers[name],members,set())) for name,(_,members,_,_) in groups.items()},guid_changes=[n.get_name() for n,value in guids.items() if n.NodeGuid.as_dict()!=value]);(out/'host-partitions.json').write_text(json.dumps(partition,indent=2),encoding='utf-8')
    if any(v['before']!=v['after'] for v in list(partition['graphs'].values())+list(partition['helpers'].values())) or partition['guid_changes']:raise RuntimeError('host original graph/text IO/GUID changed')
    text_after={'mode':raw_text(mn['K2Node_Select_2'],out/'mode-text-after.t3d'),'on':raw_text(bn['K2Node_CallFunction_0'],out/'bots-on-after.t3d'),'off':raw_text(bn['K2Node_CallFunction_8'],out/'bots-off-after.t3d')}
    if text_after!=text_before:raise RuntimeError('host original localized label history changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
    if interface!=5 or transport!=TRANSPORT:raise RuntimeError('host transport footprint differs: '+str(transport))
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS)):raise RuntimeError('complete host Profile family required')
    finally:ue.unregister_all_mixins()
    if hashlib.sha256((stage/MACRO).read_bytes()).hexdigest()!=macro_hash:raise RuntimeError('shared preparation macro changed')
    bp.save_package();asset.save_package();return dict(status='passed',kind='hostsession',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_tree_animations_public_signatures_guids_and_graph_partitions_preserved=True,original_native_localized_mode_and_bot_texts_preserved=True,original_native_login_spinner_loading_macro_and_submit_binding_payloads_preserved=True,original_completion_unbind_before_bool_gate_and_opaque_error_message_preserved=True,original_request_modes_bot_zero_override_and_null_result_preserved=True,shared_macro_definition_unchanged=True,shared_macro_sha256=macro_hash,original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/'+asset_name+'.uasset'])
