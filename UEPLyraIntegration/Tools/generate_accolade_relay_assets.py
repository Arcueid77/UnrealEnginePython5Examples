"""Preserve the partial listener/RPC; typed native notification VM transport."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_GetSubsystem
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect,read_graph,broadcast_graph
from uep_lyra_hud.accolade_relay_mixin import CLASS,RECEIVE,BROADCAST,ROOT

RELATIVE='Plugins/GameFeatures/ShooterCore/Content/Accolades/B_AccoladeRelay.uasset'
SET='Content/UEPMixins/DA_AccoladeRelayMixin.uasset'
PROBE='Content/UEPValidation/BP_AccoladeRelayProbe.uasset'


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh original accolade relay required')
    if (stage/PROBE).exists():raise RuntimeError('fresh accolade observer fixture required')
    dependency='Plugins/GameFeatures/ShooterCore/Content/Accolades/B_EliminationFeedRelay.uasset';dependency_sha=hashlib.sha256((stage/dependency).read_bytes()).hexdigest()
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'accolade-before');signature=ue.describe_function(bp.GeneratedClass,'ReceiveBeginPlay');rpc=ue.describe_function(ue.find_class('LyraPlayerState'),'ClientBroadcastMessage')
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
    if total!=15:raise RuntimeError('original accolade relay graph footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};listen=nodes['K2Node_AsyncAction_ListenForGameplayMessages_0'];payload=listen.node_find_pin('Payload')
    if listen.node_find_pin('MatchType').default_value!='PartialMatch' or listen.node_find_pin('Channel').default_value!='(TagName="'+ROOT+'")':raise RuntimeError('original partial accolade listener differs')
    out=listen.node_find_pin('OnMessageReceived');target,=out.get_linked_to();ignored={(listen.get_name(),out.name),(target.owning_node.get_name(),target.name)};hashes={g.get_name():semantics(g,n,ignored if g==event else set()) for g,n in originals}
    make_gate(bp,RECEIVE,'Payload',payload)
    graph=ue.blueprint_add_function(bp,BROADCAST);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='struct',PinSubCategoryObject=ue.find_struct('LyraNotificationMessage')),'Payload')
    router=ue.new_object(K2Node_GetSubsystem);router.CustomClass=ue.find_class('GameplayMessageSubsystem');graph.graph_add_node(router);call=graph.graph_add_node_call_function(ue.find_class('GameplayMessageSubsystem').K2_BroadcastMessage)
    connect(entry,'then',call,'execute');connect(entry,'Payload',call,'Message');connect(router,'ReturnValue',call,'self');call.node_find_pin('Channel').default_value=nodes['K2Node_CallFunction_2'].node_find_pin('Channel').default_value
    ue.compile_blueprint(bp);ue.unregister_all_mixins();insert_gate(event,listen,'OnMessageReceived',getattr(bp.GeneratedClass,RECEIVE),'Payload','Payload')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_AccoladeRelayMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.accolade_relay_mixin',PythonClass='LyraAccoladeRelay'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'accolade-after')!=before or ue.describe_function(bp.GeneratedClass,'ReceiveBeginPlay')!=signature or ue.describe_function(ue.find_class('LyraPlayerState'),'ClientBroadcastMessage')!=rpc:raise RuntimeError('original accolade CDO/BeginPlay/client RPC changed')
    if any(semantics(g,n,ignored if g==event else set())!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('original accolade graph changed beyond callback gate')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=12:raise RuntimeError('accolade requires7 transport and5 interface nodes')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict(Python=1,BlueprintFallback=1):raise RuntimeError('complete accolade Profile family required')
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_AccoladeRelayProbe');read_graph(probe,'Notification',ue.find_struct('LyraNotificationMessage'),ue.find_class('AsyncAction_ListenForGameplayMessage'));broadcast_graph(probe,'Verb',ue.find_struct('LyraVerbMessage'),ue.find_class('GameplayMessageSubsystem'));ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('typed accolade notification observer failed')
    if hashlib.sha256((stage/dependency).read_bytes()).hexdigest()!=dependency_sha:raise RuntimeError('accepted elimination relay dependency changed')
    bp.save_package();asset.save_package();probe.save_package()
    return dict(status='passed',kind='accoladerelay',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_full_cdo_partial_async_factory_sequence_authority_cosmetic_rpc_and_business_graphs_preserved=True,
        original_graph_nodes=15,transport_nodes=7,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,actual_registered_profile_method_counts=counts,native_notification_struct_and_broadcast_custom_thunk=True,native_client_rpc_signature=rpc,
        dependency_hashes={dependency:dependency_sha},fixture=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=[RELATIVE,SET])
