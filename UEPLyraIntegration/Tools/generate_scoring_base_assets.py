"""Base-owned gates cover native child static calls without changing child assets."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_weapons.scoring_base_mixin import CLASS,START,GATES

RELATIVE='Plugins/GameFeatures/ShooterCore/Content/Game/B_ShooterGameScoring_Base.uasset'
CHILDREN={label:('/ShooterCore/'+folder+'/'+name+'.'+name,'Plugins/GameFeatures/ShooterCore/Content/'+folder+'/'+name+'.uasset') for label,folder,name in (('tdm','Elimination','B_TeamDeathMatchScoring'),('cp','ControlPoint','B_ControlPointScoring'))}
FIXTURE='Content/UEPValidation/BP_ScoringBaseFixture.uasset'


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh scoring base required')
    if (stage/FIXTURE).exists():raise RuntimeError('fresh scoring fixture required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'scoring-base-before')
    methods=('ReceiveBeginPlay','ResetAllActivePlayers','PostWarmup','OnEliminationScored');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};children={}
    for label,(package,relative) in CHILDREN.items():
        child=ue.load_object(Blueprint,package);digest=hashlib.sha256((stage/relative).read_bytes()).hexdigest()
        if digest!=hashlib.sha256((official/relative).read_bytes()).hexdigest():raise RuntimeError('original scoring child required')
        children[label]=dict(bp=child,relative=relative,sha256=digest,cdo=snapshot(child,'scoring-'+label+'-before'),signatures={m:ue.describe_function(child.GeneratedClass,m) for m in methods})
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(keys) for _,keys in originals)
    if total!=61:raise RuntimeError('original scoring base footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};authority=nodes['K2Node_MacroInstance_1'];sequence=nodes['K2Node_ExecutionSequence_0'];points=[(event,authority,'Authority',GATES['begin'],None)]
    channels=[]
    for node in event.Nodes:
        if node.get_class().get_name()=='K2Node_AsyncAction_ListenForGameplayMessages':
            channel=node.node_find_pin('Channel').default_value;label='elimination' if 'Lyra.Elimination.Message' in channel else 'assist' if 'Lyra.Assist.Message' in channel else None
            if label is None or node.node_find_pin('MatchType').default_value!='ExactMatch':raise RuntimeError('source scoring exact channel differs')
            channels.append(channel);points.append((event,node,'OnMessageReceived',GATES[label],node.node_find_pin('Payload')))
    if len(channels)!=2:raise RuntimeError('both source scoring listeners required')
    for method,label in (('ResetAllActivePlayers','reset'),('PostWarmup','warmup')):
        g,=[g for g,_ in originals if g.get_name()==method];points.append((g,g.Nodes[0],'then',GATES[label],None))
    ignored={g.get_name():set() for g,_ in originals}
    for g,node,output,name,payload in points:
        target,=node.node_find_pin(output).get_linked_to();ignored[g.get_name()].update(((node.get_name(),output),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,keys,ignored[g.get_name()]) for g,keys in originals}
    for g,node,output,name,payload in points:make_gate(bp,name,'Payload' if payload is not None else None,payload)
    start=event.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName=START;event.graph_reconstruct_node(start);connect(start,'then',sequence,'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for g,node,output,name,payload in points:insert_gate(g,node,output,getattr(bp.GeneratedClass,name),'Payload' if payload is not None else None,'Payload' if payload is not None else None)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_ScoringBaseMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python'
    asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.scoring_base_mixin',PythonClass='LyraScoringBase'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'scoring-base-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('scoring base CDO/signatures changed')
    if any(semantics(g,keys,ignored[g.get_name()])!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('scoring graph changed beyond gates')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=26:raise RuntimeError('scoring transport footprint differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict(Python=5,BlueprintFallback=5):raise RuntimeError('complete base-owned scoring gates required')
    finally:ue.unregister_all_mixins()
    for label,row in children.items():
        child=row['bp']
        if snapshot(child,'scoring-'+label+'-after')!=row['cdo'] or any(ue.describe_function(child.GeneratedClass,m)!=v for m,v in row['signatures'].items()) or hashlib.sha256((stage/row['relative']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('scoring child CDO/signature/bytes changed')
    probe=ue.create_blueprint(bp.GeneratedClass,'/Game/UEPValidation/BP_ScoringBaseFixture');probe.bGenerateAbstractClass=False;ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('concrete scoring base fixture compile failed')
    bp.save_package();asset.save_package();probe.save_package()
    return dict(status='passed',kind='scoringbase',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdo_signatures_business_graphs_children_and_hook_preserved=True,original_authority_switch_exact_async_factories_and_listener_lifetime_preserved=True,
        base_owned_gates_cover_child_static_parent_and_public_calls=True,original_graph_nodes=61,transport_nodes=21,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,
        actual_registered_profile_method_counts=counts,child_asset_hashes={k:dict(relative=v['relative'],sha256=v['sha256']) for k,v in children.items()},
        fixture=dict(stage_only=True,asset=str(stage/FIXTURE),sha256=hashlib.sha256((stage/FIXTURE).read_bytes()).hexdigest()),assets=[RELATIVE,'Content/UEPMixins/DA_ScoringBaseMixin.uasset'])
