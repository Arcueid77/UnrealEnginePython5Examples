"""Replay query UI and row policy with opaque localized text/confirmation IO."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node,raw_text
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud import replay_browser_mixin as browser,replay_entry_mixin as entry_policy
ASSETS={'browser':'Content/UI/Menu/Replays/W_ReplayBrowserScreen.uasset','entry':'Content/UI/Menu/Replays/W_ReplayListEntry.uasset'}
def declare(bp,name,params=(),output=None):
    graph=ue.blueprint_add_function(bp,name);start=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    if output:start.ExtraFlags=int(start.ExtraFlags)|0x40000000
    for param,pin in params:start.node_create_pin(1,kind(pin),param)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue')
    connect(start,'then',result,'execute')
def profile(bp,label,policy):
    name='DA_Replay'+('Browser' if label=='browser' else 'Entry')+'Mixin';factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';prefix='LyraReplay'+('Browser' if label=='browser' else 'Entry');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.replay_'+('browser' if label=='browser' else 'entry')+'_mixin',PythonClass=prefix+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');return asset,name
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[];pending=[]
    for label,policy,total,transport in (('browser',browser,21,27),('entry',entry_policy,16,16)):
        if hashlib.sha256((stage/ASSETS[label]).read_bytes()).digest()!=hashlib.sha256((official/ASSETS[label]).read_bytes()).digest():raise RuntimeError('fresh original replay widgets required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,policy.CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-replay-before');tree=visuals(bp,out,label+'-replay-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes}
        if sum(len(ns) for _,ns in originals)!=total:raise RuntimeError('original replay footprint differs')
        names=set()
        for graph,_ in originals:
            if graph.get_name()!='EventGraph':names.add(graph.get_name())
            for node in graph.Nodes:
                if node.get_class().get_name()=='K2Node_Event':names.add(str(node.EventReference.MemberName))
                if node.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):names.add(str(node.CustomFunctionName))
        signatures={n:ue.describe_function(bp.GeneratedClass,n) for n in names};ignored={g.get_name():set() for g,_ in originals};moved=set();helper=None;group_hash=None;raw_before={};refs={};points=[]
        if label=='browser':
            focus=next(g for g,_ in originals if g.get_name()=='BP_GetDesiredFocusTarget');fe=focus.Nodes[0];fr=next(n for n in focus.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');target,=fe.node_find_pin('then').get_linked_to();ignored[focus.get_name()].update(((fe.get_name(),'then'),(target.owning_node.get_name(),target.name)))
            points=[(nodes[n],p,k,params) for n,p,k,params in (('K2Node_Event_0','then','activate',()),('K2Node_ComponentBoundEvent_2','then','refresh',()),('K2Node_MacroInstance_1','Completed','search',()),('K2Node_CustomEvent_2','then','unlock',()),('K2Node_AsyncAction_0','QueryComplete','results',(('Results',nodes['K2Node_AsyncAction_0'].node_find_pin('Results')),)))];proxy_before=dict(factory=str(nodes['K2Node_AsyncAction_0'].ProxyFactoryFunctionName),cls=nodes['K2Node_AsyncAction_0'].ProxyClass.get_path_name())
            if proxy_before['factory']!='QueryReplays':raise RuntimeError('original native replay query factory required')
        else:
            moved={'K2Node_VariableSet_1','K2Node_CallFunction_1','K2Node_CallFunction_3','K2Node_CallFunction_4','K2Node_FormatText_0','K2Node_VariableGet_0','K2Node_CallFunction_2'};group_hash=semantics(event,moved,set());refs={name:nodes[name].VariableReference.as_dict() for name in ('K2Node_VariableSet_1','K2Node_VariableGet_0')};raw_before={n:raw_text(nodes[n],out/('replay-'+n+'-before.t3d')) for n in ('K2Node_FormatText_0','K2Node_AsyncAction_0')};ignored[event.get_name()].update((('K2Node_DynamicCast_1','then'),))
            points=[(nodes[n],p,k,params) for n,p,k,params in (('K2Node_Event_3','then','item',(('Item',nodes['K2Node_Event_3'].node_find_pin('ListItemObject')),)),('K2Node_ComponentBoundEvent_0','then','click',()),('K2Node_AsyncAction_0','OnResult','result',(('Result',nodes['K2Node_AsyncAction_0'].node_find_pin('Result')),)))];proxy_before=dict(factory=str(nodes['K2Node_AsyncAction_0'].ProxyFactoryFunctionName),cls=nodes['K2Node_AsyncAction_0'].ProxyClass.get_path_name());require_confirmed=nodes['K2Node_EnumEquality_0'].node_find_pin('B').default_value
            if require_confirmed!='Confirmed':raise RuntimeError('original Confirmed-only replay input required')
        for node,pin,_,_ in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[event.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,ns-(moved if g==event else set()),ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        if label=='entry':
            links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in moved for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in moved];helper=ue.blueprint_add_function(bp,policy.NATIVE['item']);start=helper.Nodes[0];start.node_create_pin(1,kind(nodes['K2Node_DynamicCast_1'].node_find_pin('AsLyra Replay List Entry')),'Replay');result=helper.graph_add_node(K2Node_FunctionResult)
            for name in moved:move_node(event,helper,nodes[name])
            for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
            for name,ref in refs.items():nodes[name].VariableReference=ue.find_struct('MemberReference')(**ref)
            connect(start,'then',nodes['K2Node_VariableSet_1'],'execute');connect(start,'Replay',nodes['K2Node_VariableSet_1'],'As Lyra Replay List Entry');connect(start,'Replay',nodes['K2Node_CallFunction_1'],'self');connect(start,'Replay',nodes['K2Node_CallFunction_3'],'self');connect(nodes['K2Node_CallFunction_2'],'then',result,'execute')
        for _,_,key,params in points:declare(bp,policy.GATES[key],params)
        if label=='browser':declare(bp,policy.GATES['focus'],output=fr.node_find_pin('ReturnValue'))
        for key,target,pin in ((('query','K2Node_AsyncAction_0','execute'),('reset','K2Node_MacroInstance_1','Reset')) if label=='browser' else (('dialog','K2Node_AsyncAction_0','execute'),)):
            alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=policy.NATIVE[key];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],pin)
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if label=='entry':
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,policy.NATIVE['item']));connect(nodes['K2Node_DynamicCast_1'],'then',call,'execute');connect(nodes['K2Node_DynamicCast_1'],'AsLyra Replay List Entry',call,'Replay')
        for node,pin,key,params in points:
            previous={n.get_name() for n in event.Nodes};insert_gate(event,node,pin,getattr(bp.GeneratedClass,policy.GATES[key]));call,=[n for n in event.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        if label=='browser':
            target,=fe.node_find_pin('then').get_linked_to();call=focus.graph_add_node_call_function(getattr(bp.GeneratedClass,policy.GATES['focus']));branch=focus.graph_add_node(K2Node_IfThenElse);fe.node_find_pin('then').break_link_to(target);connect(fe,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=focus.graph_add_node(K2Node_FunctionResult);early.FunctionReference=fr.FunctionReference;focus.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue',early,'ReturnValue')
        asset,name=profile(bp,label,policy);ue.compile_blueprint(bp);ue.unregister_all_mixins();after={n:ue.describe_function(bp.GeneratedClass,n) for n in names};(out/(label+'-replay-signatures.json')).write_text(json.dumps(dict(before=signatures,after=after),indent=2),encoding='utf-8')
        if int(bp.Status)==2 or after!=signatures or snapshot(bp,label+'-replay-after')!=before or visuals(bp,out,label+'-replay-after')!=tree:raise RuntimeError('original replay CDO/tree/animation/public ABI changed: '+label)
        if any(semantics(g,ns-(moved if g==event else set()),ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original replay graph/GUID changed: '+label)
        if helper is not None:
            if semantics(helper,moved,set())!=group_hash or any(nodes[n].VariableReference.as_dict()!=ref for n,ref in refs.items()) or {n:raw_text(nodes[n],out/('replay-'+n+'-after.t3d')) for n in raw_before}!=raw_before:raise RuntimeError('opaque replay native text/frame payload changed')
        proxy_after=dict(factory=str(nodes['K2Node_AsyncAction_0'].ProxyFactoryFunctionName),cls=nodes['K2Node_AsyncAction_0'].ProxyClass.get_path_name())
        if proxy_after!=proxy_before:raise RuntimeError('native replay query/confirmation proxy changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));actual=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
        if interface!=5 or actual!=transport:raise RuntimeError('replay transport differs: '+repr((label,actual)))
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(policy.METHODS)):raise RuntimeError('complete replay Profile family required')
        finally:ue.unregister_all_mixins()
        pending.extend([bp,asset]);saved.extend([ASSETS[label],'Content/UEPMixins/'+name+'.uasset']);rows[label]=dict(original_nodes=total,transport_nodes=actual,interface_nodes=interface,method_counts=counts,native_proxy=proxy_before,original_cdo_tree_public_signatures_guids_and_graph_partitions_preserved=True)
    for obj in pending:obj.save_package()
    return dict(status='passed',kind='replaybrowser',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_native_do_once_query_and_result_identity_order_preserved=True,original_native_localized_duration_text_and_confirmation_payloads_preserved=True,original_confirmed_only_play_uses_current_entry_after_dialog=True,widgets=rows,new_business_nodes=0,native_end_adapter_nodes=0,assets=saved)
