"""Keep original GAS entry, montage/spawn tasks, delegates and unconnected paths."""
import hashlib, json, sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics, make_gate, insert_gate
from message_payload_graphs import connect
from uep_lyra_abilities.arena_drop_bomb_mixin import CLASS, AFTER_MONTAGE, AFTER_SPAWN, SPAWN

RELATIVE = 'Plugins/GameFeatures/TopDownArena/Content/Game/Bombs/GA_DropBomb.uasset'
DEPENDENCIES = ['Plugins/GameFeatures/TopDownArena/Content/Game/Bombs/'+n+'.uasset' for n in ('B_Bomb_Base', 'B_Bomb_Standard')]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generate(stage):
    official = Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    out = Path(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if sha(stage/RELATIVE) != sha(official/RELATIVE):
        raise RuntimeError('fresh original Arena drop ability required')
    dependencies = {relative: sha(stage/relative) for relative in DEPENDENCIES}
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, CLASS.removesuffix('_C'))
    before = snapshot(bp, 'arena-drop-bomb-before')
    original = [(g, {n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    guids = {n: n.NodeGuid.as_dict() for g, _ in original for n in g.Nodes}
    methods = ('K2_ActivateAbility', 'K2_CanActivateAbility', 'GetBombSpawnLocation')
    shapes = {m: ue.describe_function(bp.GeneratedClass, m) for m in methods}
    event = bp.UbergraphPages[0]
    nodes = {n.get_name(): n for n in event.Nodes}
    montage, spawn = nodes['K2Node_LatentAbilityCall_0'], nodes['K2Node_LatentGameplayTaskCall_0']
    authority, location = nodes['K2Node_CallFunction_0'], nodes['K2Node_CallFunction_11']
    points = [(montage, 'then', AFTER_MONTAGE), (spawn, 'Success', AFTER_SPAWN), (spawn, 'DidNotSpawn', AFTER_SPAWN)]
    ignored = set()
    for node, pin, _ in points:
        target, = node.node_find_pin(pin).get_linked_to()
        ignored.update(((node.get_name(), pin), (target.owning_node.get_name(), target.name)))
    ignored.update(((authority.get_name(), 'True'), (spawn.get_name(), 'execute'),
                    (location.get_name(), 'ReturnValue'), (spawn.get_name(), 'SpawnLocation')))
    hashes = {g.get_name(): semantics(g, names, ignored if g == event else set()) for g, names in original}
    if sum(len(names) for _, names in original) != 25:
        raise RuntimeError('original drop ability footprint differs')
    if nodes['K2Node_CallFunction_3'].node_find_pin('execute').get_linked_to() or authority.node_find_pin('False').get_linked_to():
        raise RuntimeError('original disconnected delay/remote branch differs')
    for name in (AFTER_MONTAGE, AFTER_SPAWN):
        make_gate(bp, name, None)
    native = event.graph_add_node(K2Node_CustomEvent)
    native.CustomFunctionName = SPAWN
    event.graph_reconstruct_node(native)
    native.node_create_pin(1, EdGraphPinType(PinCategory='struct', PinSubCategoryObject=ue.find_struct('Vector')), 'Position')
    source, = spawn.node_find_pin('execute').get_linked_to()
    source.break_link_to(spawn.node_find_pin('execute'))
    source_position, = spawn.node_find_pin('SpawnLocation').get_linked_to()
    source_position.break_link_to(spawn.node_find_pin('SpawnLocation'))
    connect(native, 'then', spawn, 'execute')
    connect(native, 'Position', spawn, 'SpawnLocation')
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    forwarding = event.graph_add_node_call_function(getattr(bp.GeneratedClass, SPAWN))
    source.connect(forwarding.node_find_pin('execute'))
    source_position.connect(forwarding.node_find_pin('Position'))
    for node, pin, name in points:
        insert_gate(event, node, pin, getattr(bp.GeneratedClass, name))
    factory = DataAssetFactory()
    factory.DataAssetClass = UEPPythonMixinSet
    asset = ue.create_asset('DA_ArenaDropBombMixin', '/Game/UEPMixins', UEPPythonMixinSet, factory)
    asset.DefaultProfile = 'Python'
    asset.Profiles = [UEPPythonMixinProfile(ProfileName=p, PythonModule='uep_lyra_abilities.arena_drop_bomb_mixin',
        PythonClass='LyraArenaDropBomb'+p+'Profile') for p in ('Python', 'BlueprintFallback')]
    ue.blueprint_configure_mixin(bp, asset, 'Python', 'PythonMixinProfile')
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    after = snapshot(bp, 'arena-drop-bomb-after')
    after_shapes = {m: ue.describe_function(bp.GeneratedClass, m) for m in methods}
    after_hashes = {g.get_name(): semantics(g, names, ignored if g == event else set()) for g, names in original}
    bad = [n.get_name() for n, guid in guids.items() if n.NodeGuid.as_dict() != guid]
    proof = dict(cdo_equal=before == after, signatures_before=shapes, signatures_after=after_shapes,
        graph_hashes_before=hashes, graph_hashes_after=after_hashes, bad_guids=bad,
        montage_guid=montage.NodeGuid.as_dict(), spawn_task_guid=spawn.NodeGuid.as_dict(),
        disconnected_delay_guid=nodes['K2Node_CallFunction_3'].NodeGuid.as_dict(),
        montage_stop_when_ability_ends=montage.node_find_pin('bStopWhenAbilityEnds').default_value,
        spawn_only_on_authority=spawn.node_find_pin('bSpawnOnlyOnAuthority').default_value)
    (out/'arena-drop-bomb-preservation.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
    if int(bp.Status) == 2 or before != after or shapes != after_shapes or hashes != after_hashes or bad or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp)) != 42:
        raise RuntimeError('drop ability CDO/ABI/GUID/native tasks/graph transport differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        row, = [r for r in ue.get_registered_mixins() if r['target_class'] == bp.GeneratedClass]
        counts = {p: len(v['functions']) for p, v in row['profiles'].items()}
        if counts != dict(Python=4, BlueprintFallback=4):
            raise RuntimeError('complete drop ability Profile family required')
    finally:
        ue.unregister_all_mixins()
    if any(sha(stage/relative) != digest for relative, digest in dependencies.items()):
        raise RuntimeError('accepted Arena bomb dependency changed')
    bp.save_package()
    asset.save_package()
    return dict(status='passed', kind='arenadropbomb', runtime_acceptance=False, full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True,
        original_cdo_gas_abis_guids_graphs_montage_and_spawn_tasks_preserved=True,
        original_failure_tag_cost_and_montage_defaults_preserved=True,
        original_native_gas_entry_and_both_spawn_end_delegates_preserved=True,
        original_disconnected_delay_and_unconnected_remote_branch_preserved=True,
        accepted_bomb_dependency_bytes_preserved=True, dependencies=dependencies,
        method_counts=counts, original_nodes=25, interface_nodes=5, transport_nodes=12,
        new_business_nodes=0, native_end_adapter_nodes=0,
        assets=[RELATIVE, 'Content/UEPMixins/DA_ArenaDropBombMixin.uasset'])
