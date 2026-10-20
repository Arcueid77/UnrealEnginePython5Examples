"""Retain full five-FText ABI, original multi-target material IO and latent click."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.session_button_mixin import CLASS,METHODS,GATES,NATIVE_CLICK

ASSET='Content/UI/Menu/Experiences/W_LyraSessionButton.uasset'
PROBE='Content/UEPValidation/BP_SessionButtonTextProbe.uasset'

def native_probe(stage,cls):
    source=ue.load_class('/ShooterCore/UserInterface/ScoreBoard/W_SB_TeamStat.W_SB_TeamStat_C');bp=ue.create_blueprint(ue.find_class('Actor'),'/Game/UEPValidation/BP_SessionButtonTextProbe');graph=ue.blueprint_add_function(bp,'SetLocalized');entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Button');red=graph.graph_add_node_call_function(source.UEPSBLocalizedTeamName);red.node_find_pin('self').default_object=source.get_cdo();red.node_find_pin('Team').default_value='1';blue=graph.graph_add_node_call_function(source.UEPSBLocalizedTeamName);blue.node_find_pin('self').default_object=source.get_cdo();blue.node_find_pin('Team').default_value='2';setter=graph.graph_add_node_call_function(getattr(cls,'Set Texts'));connect(entry,'then',red,'execute');connect(red,'then',blue,'execute');connect(blue,'then',setter,'execute');connect(entry,'Button',setter,'self')
    for parameter in ('GameMode','MapName','Ping','Players','MaxPlayers'):connect(red if parameter in ('GameMode','Ping','MaxPlayers') else blue,'ReturnValue',setter,parameter)
    ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('native five-FText session probe compile failed')
    bp.save_package();return dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest())

def gate(bp,key,params):
    graph=ue.blueprint_add_function(bp,GATES[key]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for name,pin in params:entry.node_create_pin(1,kind(pin),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original session button required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'session-button-before');tree=visuals(bp,out,'session-button-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(ns) for _,ns in originals)
    if total!=89:raise RuntimeError('original session button footprint differs')
    graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[]
    for function,key,param in (('ResetMaterials','reset',None),('ResetFontMaterials','font_reset','Text'),('SetMapImage','image','MapImage')):
        graph=graphs[function];entry=graph.Nodes[0];points.append((graph,entry,'then',key,((param,entry.node_find_pin(param)),) if param else ()))
    for name,key,param in (('K2Node_Event_12','pre','IsDesignTime'),('K2Node_Event_2','construct',None),('K2Node_Event_10','hover',None),('K2Node_Event_8','unhover',None),('K2Node_Event_7','select',None),('K2Node_Event_9','deselect',None),('K2Node_Event_11','click',None),('K2Node_Event_15','disable',None),('K2Node_Event_16','enable',None)):
        node=nodes[name];points.append((event,node,'then',key,((param,node.node_find_pin(param)),) if param else ()))
    points.append((event,nodes['K2Node_PlayAnimationTimeRange_0'],'Finished','finished',()))
    methods={g.get_name() for g,_ in originals if g.get_name()!='EventGraph'}
    for n in event.Nodes:
        if n.get_class().get_name()=='K2Node_Event':methods.add(str(n.EventReference.MemberName))
    signatures={method:ue.describe_function(bp.GeneratedClass,method) for method in methods};ignored={g.get_name():set() for g,_ in originals}
    for graph,node,pin,_,_ in points:
        target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
    for graph,node,pin,key,params in points:gate(bp,key,params)
    alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE_CLICK;event.graph_reconstruct_node(alias);connect(alias,'then',nodes['K2Node_PlayAnimationTimeRange_0'],'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for graph,node,pin,key,params in points:
        previous={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
        for name,p in params:p.make_link_to(call.node_find_pin(name))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_SessionButtonMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.session_button_mixin',PythonClass='LyraSessionButton'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after={method:ue.describe_function(bp.GeneratedClass,method) for method in signatures};(out/'session-button-public-signatures.json').write_text(json.dumps(dict(before=signatures,after=after),indent=2),encoding='utf-8')
    if int(bp.Status)==2 or signatures!=after or snapshot(bp,'session-button-after')!=before or visuals(bp,out,'session-button-after')!=tree:raise RuntimeError('session button CDO/tree/animation/public ABI changed')
    if any(semantics(g,ns,ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('session button original graph/GUID changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
    if interface!=5 or transport!=53:raise RuntimeError('session button transport count differs: '+str(transport))
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS)):raise RuntimeError('complete session button Profile family required')
    finally:ue.unregister_all_mixins()
    probe=native_probe(stage,bp.GeneratedClass);bp.save_package();asset.save_package();return dict(status='passed',kind='sessionbutton',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_tree_animations_public_signatures_guids_and_graphs_preserved=True,original_five_ftext_setter_graph_entirely_native_and_unmixed=True,original_native_latent_click_clock_start_time_then_sound_and_finished_preserved=True,original_six_target_material_reset_and_unused_label_getter_order_preserved=True,original_only_border_disabled_and_null_texture_ignored_semantics_preserved=True,native_text_probe=probe,original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/'+name+'.uasset'])
