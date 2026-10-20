"""Native timer and localized formatter adapters; Python list/filter/sort policy."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node,raw_text
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.scoreboard_list_mixin import CLASSES,GATES,LIST_TIMER,PING_TIMER,FORMAT

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/UserInterface/ScoreBoard/'+n+'.uasset' for k,n in (('list','W_SB_PlayerList'),('connection','W_UserConnectionStatus'))}


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label in ('list','connection'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh scoreboard list/connection asset required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-sb-list-before');templates=visuals(bp,output,label+'-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!={'list':102,'connection':20}[label]:raise RuntimeError('original list/connection graph footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};graphs={g.get_name():g for g,_ in originals};methods=('Construct','PollPlayerStates','SortPlayerList','PassesFilter','BP_GetDesiredFocusTarget','Update Leaderboard While Active') if label=='list' else ('SetPlayerState','UpdateStatus');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};moved=set();moved_hash=None
        if label=='list':points=[(event,nodes['K2Node_Event_1'],'then','construct',()),(graphs['PollPlayerStates'],graphs['PollPlayerStates'].Nodes[0],'then','poll',()),(graphs['SortPlayerList'],graphs['SortPlayerList'].Nodes[0],'then','sort',())]
        else:points=[(event,nodes['K2Node_Event_0'],'then','set',(('PlayerState',nodes['K2Node_Event_0'].node_find_pin('PlayerState')),)),(event,nodes['K2Node_CustomEvent_0'],'then','update',())]
        ignored={g.get_name():set() for g,_ in originals}
        for graph,node,pin,key,params in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        if label=='list':
            filt=graphs['PassesFilter'];fe=filt.Nodes[0];target,=fe.node_find_pin('then').get_linked_to();ignored[filt.get_name()].update(((fe.get_name(),'then'),(target.owning_node.get_name(),target.name)))
        else:
            fmt=nodes['K2Node_FormatText_1'];moved={fmt.get_name()};mi={(fmt.get_name(),'Ping'),(fmt.get_name(),'Result')};moved_hash=semantics(event,moved,mi);literal=raw_text(fmt,output/'ping-format-before.t3d')
            setter=nodes['K2Node_CallFunction_6'];before_set,=setter.node_find_pin('execute').get_linked_to();ignored[event.get_name()].update(((before_set.owning_node.get_name(),before_set.name),(setter.get_name(),'execute')))
        hashes={g.get_name():semantics(g,n-(moved if g==event else set()),ignored[g.get_name()]) for g,n in originals}
        for graph,node,pin,key,params in points:
            gate=ue.blueprint_add_function(bp,GATES[key]);entry=gate.Nodes[0];result=gate.graph_add_node(K2Node_FunctionResult)
            for n,p in params:entry.node_create_pin(1,kind(p),n)
            result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')
        if label=='list':
            gate=ue.blueprint_add_function(bp,GATES['filter']);ge=gate.Nodes[0];ge.node_create_pin(1,kind(fe.node_find_pin('TestPS')),'TestPS');result=gate.graph_add_node(K2Node_FunctionResult)
            for n in ('UseOriginal','Passes'):result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),n)
            result.node_find_pin('UseOriginal').default_value='true';connect(ge,'then',result,'execute')
        else:
            formatter=ue.blueprint_add_function(bp,FORMAT);entry=formatter.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='text'),'Ping');result=formatter.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='text'),'ReturnValue');connect(entry,'then',result,'execute');move_node(event,formatter,fmt);connect(entry,'Ping',fmt,'Ping');connect(fmt,'Result',result,'ReturnValue')
        start=event.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName=LIST_TIMER if label=='list' else PING_TIMER;event.graph_reconstruct_node(start);connect(start,'then',nodes['K2Node_CallFunction_0'],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for graph,node,pin,key,params in points:
            old={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:connect(p.owning_node,p.name,call,name)
        if label=='list':
            call=filt.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES['filter']));branch=filt.graph_add_node(K2Node_IfThenElse);fe.node_find_pin('then').break_link_to(target);connect(fe,'then',call,'execute');connect(fe,'TestPS',call,'TestPS');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);old_result=next(n for n in filt.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');early=filt.graph_add_node(K2Node_FunctionResult);early.FunctionReference=old_result.FunctionReference;filt.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'Passes',early,'Passes')
        else:
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,FORMAT));connect(nodes['K2Node_CallFunction_5'],'ReturnValue',call,'Ping');connect(call,'ReturnValue',setter,'InText');before_set.break_link_to(setter.node_find_pin('execute'));before_set.make_link_to(call.node_find_pin('execute'));connect(call,'then',setter,'execute')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Scoreboard'+label.title()+'ContainerMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.scoreboard_list_mixin',PythonClass='LyraScoreboard'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-sb-list-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,n)!=v for n,v in signatures.items()):raise RuntimeError('list/connection CDO/trees/signatures changed')
        if any(semantics(g,n-(moved if g==event else set()),ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('original list/connection graphs changed beyond typed transports')
        if label=='connection' and (semantics(formatter,moved,mi)!=moved_hash or raw_text(fmt,output/'ping-format-after.t3d')!=literal):raise RuntimeError('native localized ping formatter changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=18 if label=='list' else 12
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=transport+5:raise RuntimeError('list/connection transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),4 if label=='list' else 2):raise RuntimeError('complete list/connection Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='scoreboardlist',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_visuals_native_timer_delegates_localized_format_and_remaining_graphs_preserved=True,localized_text_roundtripped=False,native_timer_seconds=1.,native_looping=True,list_timer_only_when_filter_not_minus_one=True,new_native_cleanup_added=False,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
