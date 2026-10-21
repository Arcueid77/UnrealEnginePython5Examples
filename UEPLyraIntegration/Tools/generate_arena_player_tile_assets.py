"""Retain complete original player tile graphs and native constant payloads."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType,MemberReference
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_hud.arena_player_tile_mixin import CLASS,MONITOR,BOUND,BIND,STATS
RELATIVE='Plugins/GameFeatures/TopDownArena/Content/UserInterface/Player/W_PlayerTile.uasset'
CHILD='Plugins/GameFeatures/TopDownArena/Content/UserInterface/Player/W_Powerup_Stat.uasset'
def sha(file):return hashlib.sha256(Path(file).read_bytes()).hexdigest()

def transports(bp,configure):
    graph=ue.blueprint_add_function(bp,BIND);entry=graph.Nodes[0];cls=ue.find_class('AsyncAction_ObserveTeam');entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Observer');call=graph.graph_add_node(K2Node_AddDelegate);call.DelegateReference=MemberReference(MemberName='OnTeamChanged',MemberParent=cls,bSelfContext=False);graph.graph_reconstruct_node(call);delegate,owner=graph.graph_add_node(K2Node_CreateDelegate),graph.graph_add_node(K2Node_Self);connect(entry,'then',call,'execute');connect(entry,'Observer',call,'self');connect(owner,'self',delegate,'self');connect(delegate,'OutputDelegate',call,'Delegate');delegate.SelectedFunctionName=BOUND
    if len(graph.Nodes)!=4:raise RuntimeError('named team delegate adapter differs')
    rows=[]
    for stat,attribute,texture in zip(STATS,('BombsRemaining','BombRange','MovementSpeed'),('Bombs','Range','Speed')):
        source,=[n for n in configure.Nodes if n.get_class().get_name()=='K2Node_CallFunction' and str(n.FunctionReference.MemberName)=='Configure' and n.node_find_pin('Display Asset').default_value.endswith('T_'+texture+'.T_'+texture)]
        expected='(AttributeName="'+attribute+'",Attribute=/Script/TopDownArenaRuntime.TopDownArenaAttributeSet:'+attribute+',AttributeOwner="/Script/CoreUObject.Class\'/Script/TopDownArenaRuntime.TopDownArenaAttributeSet\'")'
        if source.node_find_pin('Attribute').default_value!=expected:raise RuntimeError('original native attribute literal differs: '+stat)
        target,=source.node_find_pin('self').get_linked_to()
        if str(target.owning_node.VariableReference.MemberName)!=stat+'Stat':raise RuntimeError('original stat child differs')
        graph=ue.blueprint_add_function(bp,'UEPArenaTileConfigure'+stat);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('LyraPlayerState')),'PlayerState');get=graph.graph_add_node_variable_get(stat+'Stat');call=graph.graph_add_node_call_function(ue.load_class('/TopDownArena/UserInterface/Player/W_Powerup_Stat.W_Powerup_Stat_C').Configure)
        connect(entry,'then',call,'execute');connect(get,stat+'Stat',call,'self');connect(entry,'PlayerState',call,'Ability Target')
        literals={name:source.node_find_pin(name).default_value for name in ('Attribute','Display Asset')}
        for name,value in literals.items():call.node_find_pin(name).default_value=value
        if len(graph.Nodes)!=3:raise RuntimeError('typed native stat call contains policy')
        rows.append(dict(function=graph.get_name(),nodes=3,original_literals=literals,gameplay_business=False))
    return dict(delegate=dict(function=BIND,nodes=4,callback=BOUND,gameplay_business=False,native_named_multicast=True),stat_calls=rows,nodes=13)

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if sha(stage/RELATIVE)!=sha(official/RELATIVE) or sha(stage/CHILD)!=sha(official/CHILD):raise RuntimeError('fresh original Arena tile and powerup child required')
    child_hash=sha(stage/CHILD);ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'arena-player-tile-before');templates=visuals(bp,out,'arena-player-tile-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in ('Configure',MONITOR,BOUND)}
    if sum(len(ns) for _,ns in original)!=30:raise RuntimeError('original thirty tile nodes required')
    configure,=[g for g,_ in original if g.get_name()=='Configure'];transport=transports(bp,configure)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_ArenaPlayerTileMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.arena_player_tile_mixin',PythonClass='LyraArenaPlayerTile'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    after=snapshot(bp,'arena-player-tile-after');after_templates=visuals(bp,out,'arena-player-tile-after');after_shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in shapes};after_hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};proof=dict(cdo_equal=before==after,visuals_equal=templates==after_templates,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'arena-player-tile-preservation.json').write_text(json.dumps(proof,indent=2))
    if int(bp.Status)==2 or before!=after or templates!=after_templates or shapes!=after_shapes or hashes!=after_hashes or proof['bad_guids'] or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))!=48 or sha(stage/CHILD)!=child_hash:raise RuntimeError('original tile CDO/ABI/graphs/GUIDs/tree or native child changed')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=3,BlueprintFallback=3):raise RuntimeError('tile Configure/Monitor/native-bound callback family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='arenaplayertile',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_abis_graphs_guids_tree_preserved=True,child_asset=str(stage/CHILD),child_sha256=child_hash,child_business_retained_for_next_batch=True,method_counts=counts,transport=transport,original_nodes=30,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,assets=[RELATIVE,'Content/UEPMixins/DA_ArenaPlayerTileMixin.uasset'])
