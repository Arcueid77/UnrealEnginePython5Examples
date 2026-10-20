"""Preserve original level soft pointer/transform/delegate and latent release."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import kind
from generate_hero_burst_cue_assets import timeline_exports
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.lobby_background_mixin import CLASS,METHODS,GATES,NATIVE
ASSET='Content/Environments/B_LoadRandomLobbyBackground.uasset'
def declare(bp,key,params):
    graph=ue.blueprint_add_function(bp,GATES[key]);start=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for name,pin in params:
        parameter=kind(pin)
        # A Blueprint input array uses the normal readonly input convention.
        # Copying the native getter's out-reference flag creates an out parm.
        if pin.container_type:parameter.bIsReference=False;parameter.bIsConst=True
        start.node_create_pin(1,parameter,name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(start,'then',result,'execute')
def templates(bp,out,prefix):
    scs=bp.get_property('SimpleConstructionScript');values={}
    for node in scs.AllNodes:
        obj=node.ComponentTemplate
        if obj is not None:
            file=out/(prefix+'-'+node.get_name()+'.t3d');ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file));values[node.get_name()]=file.read_bytes()
    return values
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original lobby background actor required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'lobby-before');scs=templates(bp,out,'lobby-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};construction=next(g for g,_ in originals if g.get_name()=='UserConstructionScript');total=sum(len(ns) for _,ns in originals)
    if total!=42:raise RuntimeError('original lobby graph footprint differs')
    points=[(construction,construction.Nodes[0],'then','construct',())]+[(event,nodes[n],pin,key,params) for n,pin,key,params in (('K2Node_Event_0','then','begin',()),('K2Node_CallFunction_1','then','catalog',(('Ids',nodes['K2Node_CallFunction_1'].node_find_pin('OutPrimaryAssetIdList')),)),('K2Node_DynamicCast_0','then','asset_ready',(('Background',nodes['K2Node_DynamicCast_0'].node_find_pin('AsLyra Lobby Background')),)),('K2Node_CallFunction_0','then','instance_result',(('Success',nodes['K2Node_CallFunction_0'].node_find_pin('bOutSuccess')),('Streaming',nodes['K2Node_CallFunction_0'].node_find_pin('ReturnValue')))),('K2Node_CustomEvent_0','then','loaded',()),('K2Node_CustomEvent_3','then','shown',()),('K2Node_CustomEvent_2','then','show',()),('K2Node_CustomEvent_1','then','hide',()),('K2Node_CallFunction_15','then','release',()))]
    names=('UserConstructionScript','ReceiveBeginPlay','OnLevelLoaded','OnLevelShown','ShowLoadingScreen','HideLoadingScreen');signatures={n:ue.describe_function(bp.GeneratedClass,n) for n in names};ignored={g.get_name():set() for g,_ in originals}
    for graph,node,pin,_,_ in points:
        target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};proxy=dict(factory=str(nodes['K2Node_AsyncAction_0'].ProxyFactoryFunctionName),cls=nodes['K2Node_AsyncAction_0'].ProxyClass.get_path_name())
    if nodes['K2Node_CallFunction_15'].node_find_pin('Duration').default_value!='0.500000':raise RuntimeError('original half-second loading release delay required')
    for _,_,_,key,params in points:declare(bp,key,params)
    for key,target in (('catalog','K2Node_CallFunction_1'),('asset','K2Node_AsyncAction_0'),('level','K2Node_CallFunction_0'),('bind','K2Node_AddDelegate_0'),('delay','K2Node_CallFunction_15'),('unregister','K2Node_CallFunction_7')):
        alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE[key];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for graph,node,pin,key,params in points:
        previous={n.get_name() for n in graph.Nodes};insert_gate(graph,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
        for name,p in params:p.make_link_to(call.node_find_pin(name))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_LobbyBackgroundMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.lobby_background_mixin',PythonClass='LyraLobbyBackground'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after={n:ue.describe_function(bp.GeneratedClass,n) for n in names};(out/'lobby-public-signatures.json').write_text(json.dumps(dict(before=signatures,after=after),indent=2),encoding='utf-8')
    if int(bp.Status)==2 or signatures!=after or snapshot(bp,'lobby-after')!=before or templates(bp,out,'lobby-after')!=scs:raise RuntimeError('original lobby CDO/component/public ABI changed')
    if any(semantics(g,ns,ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original lobby graphs/GUIDs changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
    if interface!=5 or transport!=46:raise RuntimeError('lobby transport differs: '+str(transport))
    (out/'lobby-catalog-gate-signature.json').write_text(json.dumps(ue.describe_function(bp.GeneratedClass,GATES['catalog']),indent=2),encoding='utf-8')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS)):raise RuntimeError('complete lobby background Profile family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package();return dict(status='passed',kind='lobbybackground',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_scs_templates_public_signatures_guids_graphs_preserved=True,original_native_primary_async_soft_level_transform_and_weak_delegates_preserved=True,original_native_half_second_delay_then_current_task_unregister_preserved=True,original_loaded_shown_failure_messages_and_loading_reason_preserved=True,original_graph_nodes=42,transport_nodes=46,interface_nodes=5,method_counts=counts,native_primary_proxy=proxy,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/DA_LobbyBackgroundMixin.uasset'])
