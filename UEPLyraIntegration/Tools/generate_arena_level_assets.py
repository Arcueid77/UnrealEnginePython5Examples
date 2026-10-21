"""Preserve original grid graph and move unchanged native spawn node to helper."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from generate_message_widget_assets import move_node
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_world.arena_level_mixin import CLASS,SPAWN
RELATIVE='Plugins/GameFeatures/TopDownArena/Content/Game/MapsGenerator/B_LevelGeneration.uasset'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pins(node):return [dict(name=p.name,category=p.category,sub_category=p.sub_category,object_type=p.sub_category_object.get_path_name() if p.sub_category_object else None,direction=p.direction,default=p.default_value,text=str(p.default_text_value),object=p.default_object.get_path_name() if p.default_object else None) for p in node.node_pins()]
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if sha(stage/RELATIVE)!=sha(official/RELATIVE):raise RuntimeError('fresh original grid required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=canonical_cdo(snapshot(bp,'arena-level-before'));original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};methods=('GenerateLevel','ClearWalls','BlockingPlayerSpawn','DistanceBlocking','ReceiveBeginPlay','ReceiveTick','ReceiveActorBeginOverlap','UserConstructionScript');shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};event=bp.UbergraphPages[0];spawn,=[n for n in event.Nodes if n.get_class().get_name()=='K2Node_SpawnActorFromClass'];source,=spawn.node_find_pin('execute').get_linked_to();location,=spawn.node_find_pin('SpawnTransform_Location').get_linked_to();remaining={n.get_name() for n in event.Nodes if n!=spawn};ignored={(source.owning_node.get_name(),source.name)};hashes={g.get_name():semantics(g,ns-({spawn.get_name()} if g==event else set()),ignored if g==event else set()) for g,ns in original};spawn_hash=semantics(event,{spawn.get_name()},set())
    spawn_pins_before=pins(spawn);(out/'spawn-pins-before.json').write_text(json.dumps(spawn_pins_before,indent=2),encoding='utf-8')
    if sum(len(ns) for _,ns in original)!=66:raise RuntimeError('original grid footprint differs')
    if spawn.node_find_pin('CollisionHandlingOverride').default_value!='Undefined' or spawn.node_find_pin('TransformScaleMethod').default_value!='OverrideRootScale':raise RuntimeError('original spawn collision/scale differs')
    graph=ue.blueprint_add_function(bp,SPAWN);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='struct',PinSubCategoryObject=ue.find_struct('Vector')),'Position');move_node(event,graph,spawn);spawn.node_find_pin('TransformScaleMethod').default_value='OverrideRootScale';connect(entry,'then',spawn,'execute');connect(entry,'Position',spawn,'SpawnTransform_Location');ue.compile_blueprint(bp);ue.unregister_all_mixins();call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,SPAWN));source.connect(call.node_find_pin('execute'));location.connect(call.node_find_pin('Position'))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_ArenaLevelMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.arena_level_mixin',PythonClass='LyraArenaLevel'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    after=canonical_cdo(snapshot(bp,'arena-level-after'));after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in shapes};after_hashes={g.get_name():semantics(g,ns-({spawn.get_name()} if g==event else set()),ignored if g==event else set()) for g,ns in original};bad=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v];proof=dict(cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,spawn_hash_before=spawn_hash,spawn_hash_after=semantics(graph,{spawn.get_name()},set()),bad_guids=bad);(out/'arena-level-preservation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');(out/'spawn-pins-after.json').write_text(json.dumps(pins(spawn),indent=2),encoding='utf-8')
    if int(bp.Status)==2 or before!=after or shapes!=after_shapes or hashes!=after_hashes or proof['spawn_hash_before']!=proof['spawn_hash_after'] or bad or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))!=73:raise RuntimeError('original grid CDO/ABI/GUID/spawn defaults/graph partition changed')
    distance,=[g for g,_ in original if g.get_name()=='DistanceBlocking']
    if len(distance.Nodes[0].LocalVariables)!=1 or str(distance.Nodes[0].LocalVariables[0].VarName)!='IsBlocking':raise RuntimeError('original local blocking scope changed')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=4,BlueprintFallback=4):raise RuntimeError('complete grid Profile family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package();return dict(status='passed',kind='arenalevel',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_abis_guids_spawn_defaults_and_graph_partitions_preserved=True,original_spawn_node_moved_intact=True,local_IsBlocking_scope_preserved=True,blocking_area_append_and_fixed100_spacing_preserved=True,inclusive_loops_and_native_random_0_to_100_preserved=True,empty_actor_events_retained=True,method_counts=counts,original_nodes=66,interface_nodes=5,transport_nodes=2,new_business_nodes=0,native_end_adapter_nodes=0,assets=[RELATIVE,'Content/UEPMixins/DA_ArenaLevelMixin.uasset'])
