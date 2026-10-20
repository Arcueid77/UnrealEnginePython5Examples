"""Keep original CP graphs/async factories/Delay/UMG data behind typed gates."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals
from mixin_graph_gates import semantics,make_gate,insert_gate
from uep_lyra_hud.control_point_widgets_mixin import CLASSES,GATES

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/'+v.removeprefix('/ShooterCore/').removesuffix('_C').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(score=118,marker=113,status=32)
TRANSPORT=dict(score=20,marker=26,status=8)
COUNTS=dict(score=5,marker=6,status=2)


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label in ('marker','score','status'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original control-point widget required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-cp-before');templates=visuals(bp,output,label+'-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original control-point widget footprint differs: '+label)
        graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[]
        if label=='marker':
            methods=('SetDynamicMaterial','UpdateControlPointStatus','PointOwnerChanged','IsPointOwned','IsPointOccupied','Construct','PreConstruct')
            for method,key,param in (('SetDynamicMaterial','materials',None),('UpdateControlPointStatus','marker','ControlPointVolume'),('PointOwnerChanged','owner','ControlPointVolume'),('IsPointOwned','owned',None),('IsPointOccupied','occupied','ControlPointVolume')):
                graph=graphs[method];entry=graph.Nodes[0];points.append((graph,entry,'then',key,param,entry.node_find_pin(param) if param else None))
            for n in ('K2Node_Event_0','K2Node_Event_1'):points.append((event,nodes[n],'then','initialize',None,None))
        elif label=='score':
            methods=('UpdateStyleSides','UpdateTeamStyles','EvaluateSound_RoundEnding','UpdateScore','Construct','Tick')
            for method,key,param in (('UpdateStyleSides','sides',None),('UpdateTeamStyles','style',None),('EvaluateSound_RoundEnding','sound','CPScoring')):
                graph=graphs[method];entry=graph.Nodes[0];points.append((graph,entry,'then',key,param,entry.node_find_pin(param) if param else None))
            points.extend(((event,nodes['K2Node_CustomEvent_0'],'then','score',None,None),(event,nodes['K2Node_IfThenElse_0'],'then','scoreteam','TeamId',nodes['K2Node_AsyncAction_2'].node_find_pin('TeamId'))))
        else:
            methods=('Construct','Tick');points=[(event,nodes['K2Node_Event_0'],'then','status',None,None),(event,nodes['K2Node_AsyncAction_2'],'OnTeamChanged','statusteam','TeamId',nodes['K2Node_AsyncAction_2'].node_find_pin('TeamId'))]
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for graph,node,pin,key,param,param_pin in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals}
        made=set()
        for graph,node,pin,key,param,param_pin in points:
            if key not in made:make_gate(bp,GATES[key],param,param_pin);made.add(key)
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for graph,node,pin,key,param,param_pin in points:
            insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]))
            if param:
                call,=node.node_find_pin(pin).get_linked_to();param_pin.make_link_to(call.owning_node.node_find_pin(param))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_ControlPoint'+label.title()+'WidgetMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.control_point_widgets_mixin',PythonClass='LyraCP'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-cp-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,n)!=v for n,v in signatures.items()):raise RuntimeError('control-point widget CDO/visuals/signatures changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('original CP graphs changed beyond typed transport')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('CP widget transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete control-point widget Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='controlpointwidgets',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_trees_animations_async_factories_delay_and_graphs_preserved=True,original_empty_tick_stays_unconnected=True,source_index_two_and_later_reuses_marker_c=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
