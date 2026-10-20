"""Extract opaque native key/delegate/text IO, route startup/login policy."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent,K2Node_GetSubsystem,K2Node_VariableGet
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node,raw_text
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.startup_login_mixin import CLASSES,METHODS,GATES,ALIASES

TOTAL=dict(startup=35,login=58)
TRANSPORT=dict(startup=39,login=45)
ASSETS={k:'Content/UI/Menu/'+v.rsplit('/',1)[-1].split('.')[0]+'.uasset' for k,v in CLASSES.items()}

def local_specs(entry,file):
    if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(entry,str(file)):raise RuntimeError('native listener locals export failed')
    raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');return [line.strip() for line in text.splitlines() if line.strip().startswith('LocalVariables(')]

def group(bp,source,name,members,first,last):
    nodes={n.get_name():n for n in source.Nodes};links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in source.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members];graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for member in members:move_node(source,graph,nodes[member])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    connect(entry,'then',nodes[first],'execute');connect(nodes[last],'then',result,'execute');return graph

def gate(bp,k,m,params=(),output=None):
    graph=ue.blueprint_add_function(bp,GATES[k][m]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    if output:entry.ExtraFlags=int(entry.ExtraFlags)|0x40000000
    for name,pin in params:entry.node_create_pin(1,kind(pin),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for k,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original startup/login bytes required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[k].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,k+'-startup-login-before');tree=visuals(bp,output,k+'-before');graphs={g.get_name():g for g in ue.blueprint_get_all_graphs(bp)};originals=[(g,{n.get_name() for n in g.Nodes}) for g in graphs.values()];total=sum(len(ns) for _,ns in originals)
        if total!=TOTAL[k]:raise RuntimeError('original startup/login footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[];groups={};helpers={};signatures={};methods=set()
        for graph,_ in originals:
            if graph.get_name()!='EventGraph':methods.add(graph.get_name())
            for node in graph.Nodes:
                if node.get_class().get_name()=='K2Node_Event':methods.add(str(node.EventReference.MemberName))
                if node.get_class().get_name()=='K2Node_ComponentBoundEvent':methods.add(str(node.CustomFunctionName))
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
        for fn,m,param in [('SetListenForLoginInput','listen','bShouldListen' if k=='startup' else 'ShouldListen'),('HandleUserInitialize','initialized','bSuccess' if k=='startup' else None)]+([('SwitchToPressStart','press_start',None),('SwitchToFullMenu','full_menu',None)] if k=='startup' else [('RefreshLoginState','refresh',None)]):
            graph=graphs[fn];entry=graph.Nodes[0];points.append((graph,entry,'then',m,((param,entry.node_find_pin(param)),) if param else ()))
        points.extend([(event,nodes['K2Node_Event_0'],'then','construct',()),(event,nodes['K2Node_ComponentBoundEvent_'+('5' if k=='startup' else '0')],'then','click',())])
        if k=='login':points.append((event,nodes['K2Node_Event_1'],'then','destruct',()))
        retgraph=graphs['BP_GetDesiredFocusTarget' if k=='startup' else 'IsPlayerLoggedIn'];retentry=retgraph.Nodes[0];retresult=next(n for n in retgraph.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');retname='ReturnValue' if k=='startup' else 'Return Value';retkey='focus' if k=='startup' else 'logged_in'
        listen=graphs['SetListenForLoginInput'];ln={n.get_name():n for n in listen.Nodes};locals_before=listen.Nodes[0].get_property('LocalVariables');locals_text=local_specs(listen.Nodes[0],output/(k+'-original-listener-locals.t3d'));primary='K2Node_VariableGet_0';empty='K2Node_VariableGet_1';on={'K2Node_CallFunction_0','K2Node_GetSubsystem_0',primary,empty}|({'K2Node_MakeStruct_1','K2Node_CreateDelegate_1'} if k=='login' else set());groups[ALIASES[k]['listen_on']]=(listen,on,'K2Node_CallFunction_0','K2Node_CallFunction_0');groups[ALIASES[k]['listen_off']]=(listen,{'K2Node_CallFunction_1'},'K2Node_CallFunction_1','K2Node_CallFunction_1')
        if k=='login':
            refresh=graphs['RefreshLoginState'];rn={n.get_name():n for n in refresh.Nodes};groups[ALIASES[k]['text_in']]=(refresh,{'K2Node_VariableGet_4','K2Node_CallFunction_12','K2Node_CallFunction_7'},'K2Node_CallFunction_7','K2Node_CallFunction_7');groups[ALIASES[k]['text_out']]=(refresh,{'K2Node_VariableGet_1','K2Node_CallFunction_5','K2Node_CallFunction_4'},'K2Node_CallFunction_4','K2Node_CallFunction_4');texts={name:raw_text(rn[name],output/(name+'-login-text-before.t3d')) for name in ('K2Node_CallFunction_12','K2Node_CallFunction_5')}
        ignored={g.get_name():set() for g,_ in originals}
        for graph,node,pin,_,_ in points+[(retgraph,retentry,'then',retkey,())]:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        # Replaced edges now call the helpers containing the same original IO.
        ignored[listen.get_name()].update((('K2Node_IfThenElse_0','then'),('K2Node_IfThenElse_0','else')))
        if k=='login':ignored[refresh.get_name()].update((('K2Node_CallFunction_2','then'),('K2Node_CallFunction_0','then'),('K2Node_CallFunction_10','execute'),('K2Node_CallFunction_9','execute')))
        moved={g.get_name():set().union(*(members for src,members,_,_ in groups.values() if src==g)) if any(src==g for src,_,_,_ in groups.values()) else set() for g,_ in originals};hashes={g.get_name():semantics(g,ns-moved[g.get_name()],ignored[g.get_name()]) for g,ns in originals};group_hashes={name:semantics(src,members,set()) for name,(src,members,_,_) in groups.items()};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};binding=None
        if k=='login':binding=(str(ln['K2Node_CreateDelegate_1'].SelectedFunctionName),ln['K2Node_CreateDelegate_1'].SelectedFunctionGuid.as_dict())
        # get_property exposes a live native struct view. Snapshot its fields
        # and construct a fresh reference for each helper; never mutate a view
        # shared with another moved variable node.
        original_local_refs={member:ln[member].get_property('VariableReference').as_dict() for member in (primary,empty)}
        for name,(src,members,first,last) in groups.items():helpers[name]=group(bp,src,name,members,first,last)
        for name in ('listen_on','listen_off'):helpers[ALIASES[k][name]].Nodes[0].set_property('LocalVariables',locals_before)
        for member in (primary,empty):
            values=dict(original_local_refs[member]);values['MemberScope']=ALIASES[k]['listen_on'];ln[member].VariableReference=ue.find_struct('MemberReference')(**values)
        off=helpers[ALIASES[k]['listen_off']];sub=off.graph_add_node(K2Node_GetSubsystem);sub.CustomClass=ue.find_class('CommonUserSubsystem');off.graph_reconstruct_node(sub);key=off.graph_add_node(K2Node_VariableGet);values=dict(original_local_refs[empty]);values['MemberScope']=ALIASES[k]['listen_off'];key.VariableReference=ue.find_struct('MemberReference')(**values);off.graph_reconstruct_node(key)
        # The helper has not entered the generated skeleton yet. Retain the
        # original local variable's typed array pin until the first compile.
        if not any(p.name=='EmptyKeys' for p in key.node_pins()):key.node_create_pin(1,kind(ln[empty].node_find_pin('EmptyKeys')),'EmptyKeys')
        connect(sub,'ReturnValue',ln['K2Node_CallFunction_1'],'self');connect(key,'EmptyKeys',ln['K2Node_CallFunction_1'],'AnyUserKeys');connect(key,'EmptyKeys',ln['K2Node_CallFunction_1'],'NewUserKeys')
        if k=='login':ln['K2Node_CreateDelegate_1'].SelectedFunctionName=binding[0];ln['K2Node_CreateDelegate_1'].SelectedFunctionGuid=ue.find_struct('Guid')(**binding[1])
        for graph,node,pin,m,params in points:gate(bp,k,m,params)
        gate(bp,k,retkey,output=retresult.node_find_pin(retname))
        for alias,target in [('bind','K2Node_AddDelegate_1'),('initialize','K2Node_AsyncAction_4' if k=='startup' else 'K2Node_CallFunction_1')]:
            entry=event.graph_add_node(K2Node_CustomEvent);entry.CustomFunctionName=ALIASES[k][alias];event.graph_reconstruct_node(entry);connect(entry,'then',nodes[target],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('startup/login native IO/helper declaration compile failed')
        for name,branch in (('listen_on','then'),('listen_off','else')):
            call=listen.graph_add_node_call_function(getattr(bp.GeneratedClass,ALIASES[k][name]));connect(ln['K2Node_IfThenElse_0'],branch,call,'execute')
        if k=='login':
            for name,source,last in (('text_in','K2Node_CallFunction_2','K2Node_CallFunction_10'),('text_out','K2Node_CallFunction_0','K2Node_CallFunction_9')):
                call=refresh.graph_add_node_call_function(getattr(bp.GeneratedClass,ALIASES[k][name]));connect(rn[source],'then',call,'execute');connect(call,'then',rn[last],'execute')
        for graph,node,pin,m,params in points:
            old={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[k][m]));call,=[n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        target,=retentry.node_find_pin('then').get_linked_to();call=retgraph.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[k][retkey]));branch=retgraph.graph_add_node(K2Node_IfThenElse);retentry.node_find_pin('then').break_link_to(target);connect(retentry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=retgraph.graph_add_node(K2Node_FunctionResult);early.FunctionReference=retresult.FunctionReference;retgraph.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,retname)
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset_name='DA_StartupLogin'+k.title()+'Mixin';asset=ue.create_asset(asset_name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.startup_login_mixin',PythonClass='LyraStartupLogin'+k.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after={m:ue.describe_function(bp.GeneratedClass,m) for m in signatures};comparison={m:dict(v) for m,v in after.items()};delta=signatures['SetListenForLoginInput']['flags']^after['SetListenForLoginInput']['flags']
        if delta not in (0,0x00800000):raise RuntimeError('unexpected public listener flags changed')
        comparison['SetListenForLoginInput']['flags']=signatures['SetListenForLoginInput']['flags']
        if k=='login':
            refresh_delta=signatures['RefreshLoginState']['flags']^after['RefreshLoginState']['flags']
            if refresh_delta not in (0,0x00800000):raise RuntimeError('unexpected public refresh flags changed')
            comparison['RefreshLoginState']['flags']=signatures['RefreshLoginState']['flags']
        (output/(k+'-public-signatures.json')).write_text(json.dumps(dict(before=signatures,after=after,only_internal_listener_or_refresh_frame_hasdefaults_may_move=True),indent=2),encoding='utf-8')
        if int(bp.Status)==2 or comparison!=signatures or snapshot(bp,k+'-startup-login-after')!=before or visuals(bp,output,k+'-after')!=tree:raise RuntimeError('startup/login CDO/tree/animation/public ABI changed')
        if any(semantics(g,ns-moved[g.get_name()],ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(semantics(helpers[name],members,set())!=group_hashes[name] for name,(_,members,_,_) in groups.items()) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('startup/login original graph partition or GUID changed')
        if any(local_specs(helpers[ALIASES[k][name]].Nodes[0],output/(k+'-'+name+'-locals.t3d'))!=locals_text for name in ('listen_on','listen_off')):raise RuntimeError('opaque native key local definitions changed')
        if k=='login' and (any(raw_text(rn[name],output/(name+'-login-text-after.t3d'))!=value for name,value in texts.items()) or str(ln['K2Node_CreateDelegate_1'].SelectedFunctionName)!=binding[0] or ln['K2Node_CreateDelegate_1'].SelectedFunctionGuid.as_dict()!=binding[1]):raise RuntimeError('native text/delegate identity changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));actual=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
        if interface!=5 or actual!=TRANSPORT[k]:raise RuntimeError('startup/login transport footprint differs: '+str(actual))
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS[k])):raise RuntimeError('complete startup/login Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+asset_name+'.uasset'));rows[k]=dict(original_graph_nodes=total,transport_nodes=actual,interface_nodes=interface,method_counts=counts,native_key_local_specs=locals_text)
    return dict(status='passed',kind='startuplogin',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_trees_public_signatures_guids_and_graph_partitions_preserved=True,original_native_key_arrays_local_defaults_and_delegate_payloads_preserved=True,original_localized_login_text_and_callback_binding_name_guid_preserved=True,only_internal_listener_or_refresh_frame_hasdefaults_may_move=True,widgets=rows,new_business_nodes=0,native_end_adapter_nodes=0,assets=saved)
