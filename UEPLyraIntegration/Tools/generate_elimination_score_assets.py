"""Typed gates retain original TDM delegates/Delay and native localized clock."""
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
from uep_lyra_hud.elimination_score_mixin import CLASS,GATES,CLOCK

ASSET='Plugins/GameFeatures/ShooterCore/Content/Elimination/UI/W_ScoreWidget_Elimination.uasset'
MOVED={'K2Node_CallFunction_0','K2Node_FormatText_0','K2Node_CallFunction_2','K2Node_CallFunction_6','K2Node_CallFunction_7'}


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original TDM score widget required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'tdm-hud-before');templates=visuals(bp,output,'tdm-hud-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
    if total!=230:raise RuntimeError('original TDM score graph footprint differs')
    graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[]
    for method,key,param in (('UpdateAllyTeamScore','ally','TDMScoring'),('Update Enemy Team Score','enemy','TDMScoring'),('UpdateTeamStyles','style',None),('UpdateStyleSides','sides',None),('UpdateClock','clock','Time'),('EvaluateSound_RoundEnding','sound','TDMScoring')):
        g=graphs[method];e=g.Nodes[0];points.append((g,e,'then',key,param,e.node_find_pin(param) if param else None))
    points.extend(((event,nodes['K2Node_CustomEvent_0'],'then','score',None,None),(event,nodes['K2Node_IfThenElse_0'],'then','team','TeamId',nodes['K2Node_AsyncAction_2'].node_find_pin('TeamId'))))
    methods=('UpdateAllyTeamScore','Update Enemy Team Score','UpdateTeamStyles','UpdateStyleSides','UpdateClock','EvaluateSound_RoundEnding','UpdateScore','Construct','Tick','PlayerCounted','CountDown');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
    for g,e,pin,key,param,param_pin in points:
        target,=e.node_find_pin(pin).get_linked_to();ignored[g.get_name()].update(((e.get_name(),pin),(target.owning_node.get_name(),target.name)))
    clock=graphs['UpdateClock'];cn={n.get_name():n for n in clock.Nodes};literal=raw_text(cn['K2Node_FormatText_0'],output/'clock-format-before.t3d');mi={('K2Node_CallFunction_0','Dividend'),('K2Node_FormatText_0','Result'),('K2Node_CallFunction_6','A'),('K2Node_CallFunction_7','ReturnValue')};mh=semantics(clock,MOVED,mi);hashes={g.get_name():semantics(g,n-(MOVED if g==clock else set()),ignored[g.get_name()]) for g,n in originals}
    for g,e,pin,key,param,param_pin in points:make_gate(bp,GATES[key],param,param_pin)
    helper=ue.blueprint_add_function(bp,CLOCK);entry=helper.Nodes[0];entry.node_create_pin(1,kind(clock.Nodes[0].node_find_pin('Time')),'Time');result=helper.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='text'),'ClockText');result.node_create_pin(0,EdGraphPinType(PinCategory='int'),'CurrentTime');connect(entry,'then',result,'execute')
    for name in MOVED:move_node(clock,helper,cn[name])
    connect(cn['K2Node_CallFunction_0'],'ReturnValue',cn['K2Node_FormatText_0'],'min');connect(cn['K2Node_CallFunction_0'],'Remainder',cn['K2Node_CallFunction_2'],'Value');connect(cn['K2Node_CallFunction_2'],'ReturnValue',cn['K2Node_FormatText_0'],'sec');connect(cn['K2Node_CallFunction_6'],'ReturnValue',cn['K2Node_CallFunction_7'],'InInt')
    connect(entry,'Time',cn['K2Node_CallFunction_0'],'Dividend');connect(entry,'Time',cn['K2Node_CallFunction_6'],'A');connect(cn['K2Node_FormatText_0'],'Result',result,'ClockText');connect(cn['K2Node_CallFunction_7'],'ReturnValue',result,'CurrentTime')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for g,e,pin,key,param,param_pin in points:
        insert_gate(g,e,pin,getattr(bp.GeneratedClass,GATES[key]))
        if param:
            call,=e.node_find_pin(pin).get_linked_to();param_pin.make_link_to(call.owning_node.node_find_pin(param))
    setter=cn['K2Node_CallFunction_1'];prior,=setter.node_find_pin('execute').get_linked_to();call=clock.graph_add_node_call_function(getattr(bp.GeneratedClass,CLOCK));prior.break_link_to(setter.node_find_pin('execute'));prior.make_link_to(call.node_find_pin('execute'));connect(call,'then',setter,'execute');connect(clock.Nodes[0],'Time',call,'Time');connect(call,'ClockText',setter,'InText');connect(call,'CurrentTime',cn['K2Node_VariableSet_1'],'CurrentTime')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_EliminationScoreWidgetMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.elimination_score_mixin',PythonClass='LyraEliminationScore'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'tdm-hud-after')!=before or visuals(bp,output,'tdm-hud-after')!=templates or any(ue.describe_function(bp.GeneratedClass,n)!=v for n,v in signatures.items()):raise RuntimeError('original TDM HUD CDO/tree/animations/signatures changed')
    if any(semantics(g,n-(MOVED if g==clock else set()),ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or semantics(helper,MOVED,mi)!=mh or raw_text(cn['K2Node_FormatText_0'],output/'clock-format-after.t3d')!=literal:raise RuntimeError('original TDM HUD graphs/localized clock nodes changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=40:raise RuntimeError('TDM HUD transport footprint differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),8):raise RuntimeError('complete TDM HUD Profile family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package();return dict(status='passed',kind='eliminationscore',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_trees_animations_async_delegate_bindings_delay_and_graphs_preserved=True,original_localized_clock_nodes_moved_intact=True,localized_text_roundtripped=False,original_graph_nodes=total,transport_nodes=35,interface_nodes=interface,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/'+name+'.uasset'])
