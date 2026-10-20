"""Retain the original subscription; typed VM packs user-defined feed messages."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_MakeStruct,K2Node_GetSubsystem
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect,read_graph,broadcast_graph
from uep_lyra_hud.elimination_feed_relay_mixin import CLASS,RECEIVE,BROADCAST,STRUCT,CHANNEL,SLOT

RELATIVE='Plugins/GameFeatures/ShooterCore/Content/Accolades/B_EliminationFeedRelay.uasset'
SET='Content/UEPMixins/DA_EliminationFeedRelayMixin.uasset'
PROBE='Content/UEPValidation/BP_EliminationFeedProbe.uasset'
ARGS=('Attacker','Attackee','AttackerTeamID','AttackeeTeamID','InstigatorTags')


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh original elimination relay required')
    if (stage/PROBE).exists():raise RuntimeError('fresh elimination feed fixture required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'elim-feed-before')
    signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in ('ReceiveBeginPlay',)}
    rpc=ue.describe_function(ue.find_class('LyraGameState'),'MulticastReliableMessageToClients')
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
    if total!=30:raise RuntimeError('original elimination relay graph footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};listen=nodes['K2Node_AsyncAction_ListenForGameplayMessages_0'];source=nodes['K2Node_MakeStruct_1'];payload=listen.node_find_pin('Payload')
    if listen.node_find_pin('MatchType').default_value!='ExactMatch' or listen.node_find_pin('Channel').default_value!='(TagName="Lyra.Elimination.Message")':raise RuntimeError('original exact elimination channel differs')
    out=listen.node_find_pin('OnMessageReceived');target,=out.get_linked_to();ignored={(listen.get_name(),out.name),(target.owning_node.get_name(),target.name)}
    hashes={g.get_name():semantics(g,n,ignored if g==event else set()) for g,n in originals}
    make_gate(bp,RECEIVE,'Payload',payload)
    fields={name:next(p for p in source.node_pins() if p.direction==0 and p.name.startswith(name+'_')) for name in ARGS}
    struct=ue.load_object(ue.find_class('ScriptStruct'),STRUCT);graph=ue.blueprint_add_function(bp,BROADCAST);entry=graph.Nodes[0]
    for name,p in fields.items():entry.node_create_pin(1,EdGraphPinType(PinCategory=p.category,PinSubCategory=p.sub_category,PinSubCategoryObject=p.sub_category_object),name)
    pack=graph.graph_add_node(K2Node_MakeStruct);pack.StructType=struct;graph.graph_reconstruct_node(pack)
    router=ue.new_object(K2Node_GetSubsystem);router.CustomClass=ue.find_class('GameplayMessageSubsystem');graph.graph_add_node(router)
    call=graph.graph_add_node_call_function(ue.find_class('GameplayMessageSubsystem').K2_BroadcastMessage);connect(entry,'then',call,'execute');connect(router,'ReturnValue',call,'self');call.node_find_pin('Channel').default_value=nodes['K2Node_CallFunction_2'].node_find_pin('Channel').default_value
    for name,p in fields.items():connect(entry,name,pack,p.name)
    slot=next(p for p in source.node_pins() if p.name.startswith('TargetChannel_'));pack.node_find_pin(slot.name).default_value=slot.default_value
    connect(pack,'EliminationFeedMessage',call,'Message')
    ue.compile_blueprint(bp);ue.unregister_all_mixins();insert_gate(event,listen,'OnMessageReceived',getattr(bp.GeneratedClass,RECEIVE),'Payload','Payload')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_EliminationFeedRelayMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.elimination_feed_relay_mixin',PythonClass='LyraEliminationFeedRelay'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'elim-feed-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()) or ue.describe_function(ue.find_class('LyraGameState'),'MulticastReliableMessageToClients')!=rpc:raise RuntimeError('original relay CDO/signature/native RPC changed')
    if any(semantics(g,n,ignored if g==event else set())!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('original relay graph changed beyond typed callback gate')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=13:raise RuntimeError('relay requires8 transport and5 interface nodes')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict(Python=1,BlueprintFallback=1):raise RuntimeError('complete relay Profile family required')
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_EliminationFeedProbe');read_graph(probe,'Feed',struct,ue.find_class('AsyncAction_ListenForGameplayMessage'));broadcast_graph(probe,'Verb',ue.find_struct('LyraVerbMessage'),ue.find_class('GameplayMessageSubsystem'));ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('typed native feed observer fixture failed')
    bp.save_package();asset.save_package();probe.save_package()
    return dict(status='passed',kind='eliminationfeedrelay',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_full_cdo_exact_async_factory_authority_cosmetic_rpc_and_business_graphs_preserved=True,
        original_graph_nodes=30,transport_nodes=8,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,actual_registered_profile_method_counts=counts,native_user_defined_feed_struct_and_broadcast_custom_thunk=True,
        typed_message_field_names={n:p.name for n,p in fields.items()},native_target_slot=slot.default_value,native_channel=call.node_find_pin('Channel').default_value,native_reliable_rpc_signature=rpc,
        fixture=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=[RELATIVE,SET])
