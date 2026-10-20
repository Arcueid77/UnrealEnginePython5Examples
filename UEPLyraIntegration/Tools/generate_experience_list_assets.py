"""Experience list/entry policy, original opaque FText/focus/delegate/async IO."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent,K2Node_VariableGet,K2Node_CreateDelegate
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud import experience_list_mixin as list_policy,experience_entry_mixin as entry_policy

POLICIES=dict(tile=entry_policy,list=list_policy)
ASSETS={k:'Content/UI/Menu/Experiences/'+p.CLASS.rsplit('/',1)[-1].split('.')[0]+'.uasset' for k,p in POLICIES.items()}
TOTAL=dict(tile=23,list=68)
TRANSPORT=dict(tile=23,list=42)

def group(bp,source,name,members,first=None,last=None,output=None):
    nodes={n.get_name():n for n in source.Nodes};links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in source.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members];graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    if output:result.node_create_pin(0,kind(nodes[output[0]].node_find_pin(output[1])),'ReturnValue')
    for member in members:move_node(source,graph,nodes[member])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    if first:connect(entry,'then',nodes[first],'execute');connect(nodes[last],'then',result,'execute')
    else:connect(entry,'then',result,'execute')
    if output:connect(nodes[output[0]],output[1],result,'ReturnValue')
    return graph

def gate(bp,policy,key,params=(),output=None):
    graph=ue.blueprint_add_function(bp,policy.GATES[key]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for name,pin in params:entry.node_create_pin(1,kind(pin),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for k,policy in POLICIES.items():
        rel=ASSETS[k]
        if hashlib.sha256((stage/rel).read_bytes()).digest()!=hashlib.sha256((official/rel).read_bytes()).digest():raise RuntimeError('fresh original experience list/entry required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,policy.CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,k+'-experience-list-before');tree=visuals(bp,out,k+'-before');graphs={g.get_name():g for g in ue.blueprint_get_all_graphs(bp)};originals=[(g,{n.get_name() for n in g.Nodes}) for g in graphs.values()];total=sum(len(ns) for _,ns in originals)
        if total!=TOTAL[k]:raise RuntimeError('original experience list/entry footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};focus=graphs['OnFocusReceived'];fn={n.get_name():n for n in focus.Nodes};fe=focus.Nodes[0];fr=next(n for n in focus.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');focus_members={n.get_name() for n in focus.Nodes if n not in (fe,fr)};focus_last='K2Node_CallFunction_'+('1' if k=='tile' else '0');groups={policy.NATIVE['focus']:(focus,focus_members,None,None,(focus_last,'ReturnValue'))};points=[]
        if k=='tile':
            source=graphs['Set User Facing Experience'];sn={n.get_name():n for n in source.Nodes};groups[policy.NATIVE['appearance']]=(source,{n.get_name() for n in source.Nodes if n.get_name() not in ('K2Node_FunctionEntry_0','K2Node_VariableSet_0')},'K2Node_CallFunction_2','K2Node_CallFunction_3',None);groups[policy.NATIVE['notify']]=(event,{'K2Node_CallDelegate_0','K2Node_VariableGet_0'},'K2Node_CallDelegate_0','K2Node_CallDelegate_0',None);points=[(source,source.Nodes[0],'then','set',(('Experience',source.Nodes[0].node_find_pin('NewExperience')),)),(event,nodes['K2Node_ComponentBoundEvent_0'],'then','click',())]
        else:
            groups[policy.NATIVE['bind']]=(event,{'K2Node_AddDelegate_0'},'K2Node_AddDelegate_0','K2Node_AddDelegate_0',None);groups[policy.NATIVE['notify']]=(event,{'K2Node_CallDelegate_1'},'K2Node_CallDelegate_1','K2Node_CallDelegate_1',None);groups[policy.NATIVE['complete']]=(event,{'K2Node_CallDelegate_2'},'K2Node_CallDelegate_2','K2Node_CallDelegate_2',None);groups[policy.NATIVE['select']]=(event,{'K2Node_VariableGet_10','K2Node_GetArrayItem_1','K2Node_VariableGet_11','K2Node_CallDelegate_3'},'K2Node_CallDelegate_3','K2Node_CallDelegate_3',None);points=[(event,nodes['K2Node_Event_1'],'then','construct',()),(event,nodes['K2Node_AsyncAction_0'],'Completed','loaded',(('Loaded',nodes['K2Node_AsyncAction_0'].node_find_pin('Loaded')),)),(event,nodes['K2Node_CustomEvent_0'],'then','click',(('Experience',nodes['K2Node_CustomEvent_0'].node_find_pin('ExperienceDef')),)),(event,nodes['K2Node_CustomEvent_2'],'then','first',()),(event,nodes['K2Node_CustomEvent_1'],'then','random',())]
        methods={g.get_name() for g,_ in originals if g.get_name()!='EventGraph' and len(g.Nodes)>1}
        for node in event.Nodes:
            if node.get_class().get_name()=='K2Node_Event':methods.add(str(node.EventReference.MemberName))
            if node.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):methods.add(str(node.CustomFunctionName))
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for graph,node,pin,_,_ in points+[(focus,fe,'then','focus',())]:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        if k=='tile':ignored[source.get_name()].add(('K2Node_VariableSet_0','then'))
        else:ignored[event.get_name()].update((('K2Node_CallArrayFunction_0','then'),('K2Node_CallFunction_3','execute'),('K2Node_MacroInstance_0','Completed')))
        moved={g.get_name():set().union(*(members for src,members,_,_,_ in groups.values() if src==g)) if any(src==g for src,_,_,_,_ in groups.values()) else set() for g,_ in originals};hashes={g.get_name():semantics(g,ns-moved[g.get_name()],ignored[g.get_name()]) for g,ns in originals};group_hash={name:semantics(src,members,set()) for name,(src,members,_,_,_) in groups.items()};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};helpers={name:group(bp,*data[:1],name,*data[1:]) for name,data in groups.items()}
        if k=='tile':
            appearance=helpers[policy.NATIVE['appearance']];getter=appearance.graph_add_node(K2Node_VariableGet);getter.VariableReference=ue.find_struct('MemberReference')(**sn['K2Node_VariableSet_0'].VariableReference.as_dict());appearance.graph_reconstruct_node(getter)
            for name in ('K2Node_VariableGet_1','K2Node_VariableGet_2','K2Node_VariableGet_4','K2Node_VariableGet_6'):connect(getter,'MyUserFacingExperience',sn[name],'self')
        else:
            bind=helpers[policy.NATIVE['bind']];bind.Nodes[0].node_create_pin(1,kind(nodes['K2Node_CreateWidget_0'].node_find_pin('ReturnValue')),'Tile');connect(bind.Nodes[0],'Tile',nodes['K2Node_AddDelegate_0'],'self');delegate=bind.graph_add_node(K2Node_CreateDelegate);connect(delegate,'OutputDelegate',nodes['K2Node_AddDelegate_0'],'Delegate');delegate.SelectedFunctionName='OnTileClicked';delegate.SelectedFunctionGuid=ue.find_struct('Guid')(**nodes['K2Node_CustomEvent_0'].NodeGuid.as_dict())
            notify=helpers[policy.NATIVE['notify']];notify.Nodes[0].node_create_pin(1,kind(nodes['K2Node_CustomEvent_0'].node_find_pin('ExperienceDef')),'Experience');connect(notify.Nodes[0],'Experience',nodes['K2Node_CallDelegate_1'],'ExperienceDef');select=helpers[policy.NATIVE['select']];select.Nodes[0].node_create_pin(1,EdGraphPinType(PinCategory='int'),'Index');connect(select.Nodes[0],'Index',nodes['K2Node_GetArrayItem_1'],'Dimension 1');alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=policy.NATIVE['load'];event.graph_reconstruct_node(alias);connect(alias,'then',nodes['K2Node_CallFunction_4'],'execute')
        for graph,node,pin,key,params in points:gate(bp,policy,key,params)
        gate(bp,policy,'focus',output=fr.node_find_pin('ReturnValue'));ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('native experience IO/gate declaration compile failed')
        if k=='tile':
            call=source.graph_add_node_call_function(getattr(bp.GeneratedClass,policy.NATIVE['appearance']));connect(sn['K2Node_VariableSet_0'],'then',call,'execute');call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,policy.NATIVE['notify']));connect(nodes['K2Node_ComponentBoundEvent_0'],'then',call,'execute')
        else:
            for key,node,pin,last in (('bind','K2Node_CallArrayFunction_0','then','K2Node_CallFunction_3'),('notify','K2Node_CustomEvent_0','then',None),('complete','K2Node_MacroInstance_0','Completed',None),('select','K2Node_CustomEvent_2','then',None)):
                call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,policy.NATIVE[key]));connect(nodes[node],pin,call,'execute')
                if last:connect(call,'then',nodes[last],'execute')
                if key=='bind':connect(nodes['K2Node_Knot_3'],'OutputPin',call,'Tile')
                if key=='notify':connect(nodes['K2Node_CustomEvent_0'],'ExperienceDef',call,'Experience')
        focus_call=focus.graph_add_node_call_function(getattr(bp.GeneratedClass,policy.NATIVE['focus']));connect(fe,'then',focus_call,'execute');connect(focus_call,'then',fr,'execute');connect(focus_call,'ReturnValue',fr,'ReturnValue')
        for graph,node,pin,key,params in points:
            old={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,policy.GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        target,=fe.node_find_pin('then').get_linked_to();call=focus.graph_add_node_call_function(getattr(bp.GeneratedClass,policy.GATES['focus']));branch=focus.graph_add_node(K2Node_IfThenElse);fe.node_find_pin('then').break_link_to(target);connect(fe,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=focus.graph_add_node(K2Node_FunctionResult);early.FunctionReference=fr.FunctionReference;focus.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,'ReturnValue')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset_name='DA_Experience'+('Entry' if k=='tile' else 'List')+'Mixin';asset=ue.create_asset(asset_name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';module='uep_lyra_hud.experience_'+('entry' if k=='tile' else 'list')+'_mixin';name='LyraExperience'+('Entry' if k=='tile' else 'List');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule=module,PythonClass=name+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();current={m:ue.describe_function(bp.GeneratedClass,m) for m in signatures};comparison={m:dict(v) for m,v in current.items()}
        for method in ('OnFocusReceived','Set User Facing Experience'):
            if method not in signatures:continue
            if signatures[method]['flags']^current[method]['flags'] not in (0,0x00800000):raise RuntimeError('unexpected public experience IO signature flags changed')
            comparison[method]['flags']=signatures[method]['flags']
        (out/(k+'-public-signatures.json')).write_text(json.dumps(dict(before=signatures,after=current,only_internal_focus_or_text_frame_hasdefaults_may_move=True),indent=2),encoding='utf-8')
        if int(bp.Status)==2 or comparison!=signatures or snapshot(bp,k+'-experience-list-after')!=before or visuals(bp,out,k+'-after')!=tree:raise RuntimeError('original experience CDO/tree/public ABI changed')
        if any(semantics(g,ns-moved[g.get_name()],ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(semantics(helpers[name],members,set())!=group_hash[name] for name,(_,members,_,_,_) in groups.items()) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('original experience graph partition or GUID changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
        if interface!=5 or transport!=TRANSPORT[k]:raise RuntimeError('experience transport footprint differs: '+k+' '+str(transport))
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(policy.METHODS)):raise RuntimeError('complete experience Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((rel,'Content/UEPMixins/'+asset_name+'.uasset'));rows[k]=dict(original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='experiencelist',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_trees_public_signatures_guids_and_graph_partitions_preserved=True,original_native_text_focus_reply_delegates_and_async_load_payloads_preserved=True,original_default_prepend_filter_and_accumulating_widget_cache_semantics_preserved=True,retained_unwired_tile_preconstruct_and_dispatcher_signature_graphs=True,only_internal_focus_or_text_frame_hasdefaults_may_move=True,widgets=rows,new_business_nodes=0,native_end_adapter_nodes=0,assets=saved)
