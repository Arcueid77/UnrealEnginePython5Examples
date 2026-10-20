"""Typed base/derived row gates; native stat timers and interface calls remain."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.scoreboard_rows_mixin import CLASSES,GATES,TIMER

ASSETS={k:CLASSES[k].removeprefix('/ShooterCore/').removesuffix('_C').split('.')[0] for k in CLASSES}
ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/'+r+'.uasset' for k,r in ASSETS.items()}
TOTAL=dict(base=9,name=15,icon=3,stat=31,cp=30,tdm=30)
TRANSPORT=dict(base=4,name=8,icon=4,stat=17,cp=17,tdm=17)
COUNTS=dict(base=1,name=2,icon=1,stat=4,cp=5,tdm=5)


def gate(bp,key,params,child_result=None):
    g=ue.blueprint_add_function(bp,GATES[key]);entry=g.Nodes[0];r=g.graph_add_node(K2Node_FunctionResult)
    for n,p in params:entry.node_create_pin(1,kind(p),n)
    r.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if child_result is not None else 'ReturnValue');r.node_find_pin('UseOriginal' if child_result is not None else 'ReturnValue').default_value='true'
    if child_result is not None:r.node_create_pin(0,kind(child_result),'Children')
    connect(entry,'then',r,'execute')


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label in ('base','name','icon','stat','cp','tdm'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original scoreboard row required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-sb-before');templates=visuals(bp,output,label+'-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original scoreboard row footprint differs')
        graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[];methods=['SetPlayerState']
        if label in ('base','name','icon'):
            n=next(n for n in event.Nodes if n.get_class().get_name()=='K2Node_Event');points.append((event,n,'then',label,(('PlayerState',n.node_find_pin('PlayerState')),)))
            if label=='name':g=graphs['SetAsLocalPlayer'];points.append((g,g.Nodes[0],'then','local',()));methods.append('SetAsLocalPlayer')
            if label=='base':methods+=['GetPlayerStateAwareChildren','SetRowColor']
        elif label=='stat':
            points=[(event,nodes['K2Node_Event_2'],'then','stat',(('PlayerState',nodes['K2Node_Event_2'].node_find_pin('PlayerState')),)),(event,nodes['K2Node_CustomEvent_0'],'then','update',()),(event,nodes['K2Node_Event_0'],'then','construct',()),(event,nodes['K2Node_Event_1'],'then','pre',(('IsDesignTime',nodes['K2Node_Event_1'].node_find_pin('IsDesignTime')),))];methods+=['UpdateState','Construct','PreConstruct']
        else:
            c=graphs['SetRowColor'];score=graphs['UpdateIndividualScoreWidget'];se=score.Nodes[0];points=[(event,nodes['K2Node_CallParentFunction_1'],'then','row',()),(c,next(n for n in c.Nodes if n.get_class().get_name()=='K2Node_CallParentFunction'),'then','color',(('IsOddNumberedRow',c.Nodes[0].node_find_pin('IsOddNumberedRow')),)),(score,se,'then','score',tuple((n,se.node_find_pin(n)) for n in ('Widget','ScoreTag')))];methods+=['SetRowColor','GetPlayerStateAwareChildren','UpdateIndividualScoreWidget']
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for graph,node,pin,key,params in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        if label in ('cp','tdm'):
            child=graphs['GetPlayerStateAwareChildren'];ce=child.Nodes[0];target,=ce.node_find_pin('then').get_linked_to();ignored[child.get_name()].update(((ce.get_name(),'then'),(target.owning_node.get_name(),target.name)));child_result=next(n for n in child.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');gate(bp,'children',(),child_result.node_find_pin('Children'))
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals}
        for graph,node,pin,key,params in points:gate(bp,key,params)
        if label=='stat':
            start=event.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName=TIMER;event.graph_reconstruct_node(start);connect(start,'then',nodes['K2Node_CallFunction_0'],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for graph,node,pin,key,params in points:
            old={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:connect(p.owning_node,p.name,call,name)
        if label in ('cp','tdm'):
            call=child.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES['children']));branch=child.graph_add_node(K2Node_IfThenElse);ce.node_find_pin('then').break_link_to(target);connect(ce,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=child.graph_add_node(K2Node_FunctionResult);early.FunctionReference=child_result.FunctionReference;child.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'Children',early,'Children')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Scoreboard'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';profile_kind='Mode' if label in ('cp','tdm') else label.title();asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.scoreboard_rows_mixin',PythonClass='LyraScoreboard'+profile_kind+p+'Profile') for p in ('Python','BlueprintFallback')]
        ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-sb-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,n)!=v for n,v in signatures.items()):raise RuntimeError('scoreboard original CDO/trees/signature/defaults changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('scoreboard original graph changed beyond typed gates')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('scoreboard transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete base/derived scoreboard Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='scoreboardrows',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_widget_trees_signatures_interface_parent_calls_empty_hooks_and_business_graphs_preserved=True,native_stat_timer_seconds=1.,native_stat_timer_looping=True,no_native_timer_or_destruct_cleanup_added=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
