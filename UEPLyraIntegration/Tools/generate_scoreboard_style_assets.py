"""Native localized team literals, preserved timer chain and typed style gates."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node,raw_text
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.scoreboard_style_mixin import CLASSES,GATES,NAME

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/'+v.removeprefix('/ShooterCore/').removesuffix('_C').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(team=84,headercp=19,headertdm=19,boardcp=10,boardtdm=10)
TRANSPORT=dict(team=15,headercp=4,headertdm=4,boardcp=4,boardtdm=4)


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label in ('team','headercp','headertdm','boardcp','boardtdm'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original scoreboard style/board asset required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-style-before');templates=visuals(bp,output,label+'-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original scoreboard style graph footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};graphs={g.get_name():g for g,_ in originals};moved=set()
        if label=='team':
            style=graphs['SetTeamStyle'];points=[(style,style.Nodes[0],'then','style'),(event,nodes['K2Node_CustomEvent_0'],'then','update'),(event,nodes['K2Node_CallFunction_4'],'then','goal')];methods=('Construct','SetTeamStyle','UpdateState');sn={n.get_name():n for n in style.Nodes};literal_node=sn['K2Node_Select_0'];moved={literal_node.get_name()};mi={(literal_node.get_name(),'Index'),(literal_node.get_name(),'ReturnValue')};moved_hash=semantics(style,moved,mi);literal=raw_text(literal_node,output/'team-name-before.t3d');setter=sn['K2Node_CallFunction_0'];index_source,=literal_node.node_find_pin('Index').get_linked_to()
        elif label.startswith('header'):
            style=graphs['SetTeamStyle'];points=[(style,style.Nodes[0],'then','header')];methods=('Construct','SetTeamStyle')
        else:points=[(event,nodes['K2Node_Event_0'],'then','activate')];methods=('BP_OnActivated',)
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for graph,node,pin,key in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n-(moved if label=='team' and g==style else set()),ignored[g.get_name()]) for g,n in originals}
        for graph,node,pin,key in points:make_gate(bp,GATES[key],None)
        if label=='team':
            formatter=ue.blueprint_add_function(bp,NAME);entry=formatter.Nodes[0];entry.node_create_pin(1,kind(literal_node.node_find_pin('Index')),'Team');result=formatter.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='text'),'ReturnValue');connect(entry,'then',result,'execute');move_node(style,formatter,literal_node);connect(entry,'Team',literal_node,'Index');connect(literal_node,'ReturnValue',result,'ReturnValue')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for graph,node,pin,key in points:insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]))
        if label=='team':
            call=style.graph_add_node_call_function(getattr(bp.GeneratedClass,NAME));index_source.make_link_to(call.node_find_pin('Team'));connect(call,'ReturnValue',setter,'InText');previous,=setter.node_find_pin('execute').get_linked_to();previous.break_link_to(setter.node_find_pin('execute'));previous.make_link_to(call.node_find_pin('execute'));connect(call,'then',setter,'execute')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_ScoreboardStyle'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';family='Team' if label=='team' else 'Header' if label.startswith('header') else 'Board';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.scoreboard_style_mixin',PythonClass='LyraScoreboard'+family+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-style-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,n)!=v for n,v in signatures.items()):raise RuntimeError('scoreboard style/board CDO/visuals/signatures changed')
        if any(semantics(g,n-(moved if label=='team' and g==style else set()),ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('original style/board graph changed beyond typed/literal transports')
        if label=='team' and (semantics(formatter,moved,mi)!=moved_hash or raw_text(literal_node,output/'team-name-after.t3d')!=literal):raise RuntimeError('original localized team-name node changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('scoreboard style transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),3 if label=='team' else 1):raise RuntimeError('complete style/board Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='scoreboardstyle',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_trees_animations_native_timer_literal_team_names_and_graphs_preserved=True,localized_text_roundtripped=False,native_timer_seconds=1.,construct_target_score_only=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
