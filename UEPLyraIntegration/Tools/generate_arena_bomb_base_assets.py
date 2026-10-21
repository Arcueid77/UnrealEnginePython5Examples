"""Retain bomb RPC/repnotify ABI, native delays and complete original graph data."""
import hashlib, json, sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_CustomEvent, K2Node_FunctionResult, K2Node_MacroInstance
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics, make_gate, insert_gate
from message_payload_graphs import connect
from generate_message_widget_assets import move_node
from generate_arena_level_assets import pins
from uep_lyra_world.arena_bomb_base_mixin import CLASS, SELECTOR, GATES, START_FUSE, MIN_BURN, PROPAGATE, HOVER, ATTRIBUTE, SPAWN, COSMETIC

RELATIVE = 'Plugins/GameFeatures/TopDownArena/Content/Game/Bombs/B_Bomb_Base.uasset'
CHILD = 'Plugins/GameFeatures/TopDownArena/Content/Game/Bombs/B_Bomb_Standard.uasset'
METHODS = ('ServerAddFireballInstance', 'ServerExpandFireballInAllDirections', 'SnapshotRange', 'SpawnBonus', 'OnRep_DirectionalRadius', 'ClientUpdateFireballVisuals', 'ReceiveBeginPlay', 'ReceiveDestroyed', 'TriggerExplosion', 'IncrementBlastRadius', 'BndEvt__B_Bomb_OverlapBox_K2Node_ComponentBoundEvent_1_ComponentEndOverlapSignature__DelegateSignature', 'UserConstructionScript')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def kind(pin):
    return EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category,
        PinSubCategoryObject=pin.sub_category_object, ContainerType=pin.container_type,
        bIsReference=pin.is_reference, bIsConst=pin.is_const)


def defaults(bp, label):
    return canonical_cdo('\n'.join(line for line in snapshot(bp, label).splitlines()
        if not line.strip().startswith(SELECTOR+'=')))


def generate(stage):
    official = Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    out = Path(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if sha(stage/RELATIVE) != sha(official/RELATIVE):
        raise RuntimeError('fresh original base bomb required')
    child_hash = sha(stage/CHILD)
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, CLASS.removesuffix('_C'))
    ue.unregister_all_mixins()
    before = defaults(bp, 'arena-bomb-base-before')
    original = [(g, {n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    guids = {n: n.NodeGuid.as_dict() for g, _ in original for n in g.Nodes}
    shapes = {name: ue.describe_function(bp.GeneratedClass, name) for name in METHODS}
    graphs = {g.get_name(): g for g, _ in original}
    event = bp.UbergraphPages[0]
    nodes = {n.get_name(): n for n in event.Nodes}
    ignored = {g.get_name(): set() for g, _ in original}
    points = [(nodes[n], 'then', key, param) for n, key, param in (
        ('K2Node_Event_0', 'begin', None), ('K2Node_Event_1', 'destroyed', None),
        ('K2Node_ComponentBoundEvent_1', 'overlap', 'OtherActor'),
        ('K2Node_CustomEvent_1', 'trigger', None), ('K2Node_CustomEvent_0', 'increment', None),
        ('K2Node_CallFunction_13', 'propagated', None), ('K2Node_CallFunction_15', 'hover', None))]
    for node, output, key, param in points:
        target, = node.node_find_pin(output).get_linked_to()
        ignored[event.get_name()].update(((node.get_name(), output), (target.owning_node.get_name(), target.name)))
    aliases = ((START_FUSE, nodes['K2Node_MacroInstance_2'], 'execute'),
               (MIN_BURN, nodes['K2Node_CallFunction_17'], 'execute'),
               (PROPAGATE, nodes['K2Node_CallFunction_13'], 'execute'),
               (HOVER, nodes['K2Node_CallFunction_15'], 'execute'))
    for _, node, pin in aliases:
        ignored[event.get_name()].add((node.get_name(), pin))
    fuse = graphs['FuseStepPause']
    fuse_nodes = {n.get_name(): n for n in fuse.Nodes}
    delay = fuse_nodes['K2Node_CallFunction_6']
    condition = fuse_nodes['K2Node_IfThenElse_0']
    field, = condition.node_find_pin('Condition').get_linked_to()
    ignored[fuse.get_name()].update(((delay.get_name(), 'then'), (condition.get_name(), 'execute'),
                                     (field.owning_node.get_name(), field.name), (condition.get_name(), 'Condition')))
    bonus = graphs['SpawnBonus']
    spawn, = [n for n in bonus.Nodes if n.get_class().get_name() == 'K2Node_SpawnActorFromClass']
    exec_source, = spawn.node_find_pin('execute').get_linked_to()
    location, = spawn.node_find_pin('SpawnTransform_Location').get_linked_to()
    effect, = spawn.node_find_pin('GameplayEffectToApply').get_linked_to()
    debug, = spawn.node_find_pin('ReturnValue').get_linked_to()
    spawn_before = pins(spawn)
    if sum(len(names) for _, names in original) != 156:
        raise RuntimeError('original base bomb graph footprint differs')
    if spawn.node_find_pin('TransformScaleMethod').default_value != 'OverrideRootScale':
        raise RuntimeError('original bonus spawn scale differs')
    hashes = {g.get_name(): semantics(g, names-({spawn.get_name()} if g == bonus else set()), ignored[g.get_name()]) for g, names in original}
    spawn_hash = semantics(bonus, {spawn.get_name()}, set())
    native_delays = {name: dict(guid=node.NodeGuid.as_dict(), duration_pin=node.node_find_pin('Duration').default_value,
        duration_links=sorted((p.owning_node.get_name(), p.name) for p in node.node_find_pin('Duration').get_linked_to()))
        for name, node in (('minimum', nodes['K2Node_CallFunction_17']), ('propagation', nodes['K2Node_CallFunction_13']),
                           ('hover', nodes['K2Node_CallFunction_15']), ('fuse', delay))}
    for node, output, key, param in points:
        make_gate(bp, GATES[key], param, node.node_find_pin(param) if param else None)
    make_gate(bp, GATES['fuse'], None)
    fuse_query, = [g for g in bp.FunctionGraphs if g.get_name() == GATES['fuse']]
    result, = [n for n in fuse_query.Nodes if n.get_class().get_name() == 'K2Node_FunctionResult']
    variable = fuse_query.graph_add_node_variable_get('IsFuseStillBurning')
    connect(variable, 'IsFuseStillBurning', result, 'ReturnValue')
    for name, node, pin in aliases:
        entry = event.graph_add_node(K2Node_CustomEvent)
        entry.CustomFunctionName = name
        event.graph_reconstruct_node(entry)
        connect(entry, 'then', node, pin)
    # Typed native query retains the original GameplayAttribute field path verbatim.
    source, = [n for n in graphs['SnapshotRange'].Nodes if n.get_class().get_name() == 'K2Node_CallFunction' and str(n.FunctionReference.MemberName) == 'GetFloatAttribute']
    query = ue.blueprint_add_function(bp, ATTRIBUTE)
    entry = query.Nodes[0]
    entry.node_create_pin(1, kind(source.node_find_pin('Actor')), 'Actor')
    call = query.graph_add_node_call_function(ue.find_class('AbilitySystemBlueprintLibrary').GetFloatAttribute)
    call.node_find_pin('Attribute').default_value = source.node_find_pin('Attribute').default_value
    result = query.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, kind(source.node_find_pin('ReturnValue')), 'Value')
    result.node_create_pin(0, EdGraphPinType(PinCategory='bool'), 'Found')
    connect(entry, 'then', result, 'execute')
    connect(entry, 'Actor', call, 'Actor')
    connect(call, 'ReturnValue', result, 'Value')
    connect(call, 'bSuccessfullyFoundAttribute', result, 'Found')
    # Keep the actual original spawn node, including exposed GE and native defaults.
    backend = ue.blueprint_add_function(bp, SPAWN)
    entry = backend.Nodes[0]
    entry.node_create_pin(1, kind(spawn.node_find_pin('SpawnTransform_Location')), 'Position')
    entry.node_create_pin(1, kind(spawn.node_find_pin('GameplayEffectToApply')), 'Effect')
    return_kind = kind(spawn.node_find_pin('ReturnValue'))
    move_node(bonus, backend, spawn)
    spawn.node_find_pin('TransformScaleMethod').default_value = 'OverrideRootScale'
    result = backend.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, return_kind, 'ReturnValue')
    connect(entry, 'then', spawn, 'execute')
    connect(entry, 'Position', spawn, 'SpawnTransform_Location')
    connect(entry, 'Effect', spawn, 'GameplayEffectToApply')
    connect(spawn, 'then', result, 'execute')
    connect(spawn, 'ReturnValue', result, 'ReturnValue')
    # Original cosmetic macro is a native world-mode query, not a guessed test.
    cosmetic_source, = [n for n in graphs['ServerExpandFireballInAllDirections'].Nodes if n.get_class().get_name() == 'K2Node_MacroInstance' and n.get_name() == 'K2Node_MacroInstance_1']
    cosmetic = ue.blueprint_add_function(bp, COSMETIC)
    entry = cosmetic.Nodes[0]
    macro = cosmetic.graph_add_node(K2Node_MacroInstance)
    macro.MacroGraphReference = cosmetic_source.MacroGraphReference.clone()
    cosmetic.graph_reconstruct_node(macro)
    connect(entry, 'then', macro, 'execute')
    for pin, boolean in (('True', 'true'), ('False', 'false')):
        result = cosmetic.graph_add_node(K2Node_FunctionResult)
        if not any(pin.name == 'ReturnValue' for pin in result.node_pins()):
            result.node_create_pin(0, EdGraphPinType(PinCategory='bool'), 'ReturnValue')
        result.node_find_pin('ReturnValue').default_value = boolean
        connect(macro, pin, result, 'execute')
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    for node, output, key, param in points:
        insert_gate(event, node, output, getattr(bp.GeneratedClass, GATES[key]), param, param)
    # Preserve macro instance and Delay GUID; replace only its state-query transport.
    target, = delay.node_find_pin('then').get_linked_to()
    delay.node_find_pin('then').break_link_to(target)
    condition.node_find_pin('Condition').break_link_to(field)
    call = fuse.graph_add_node_call_function(getattr(bp.GeneratedClass, GATES['fuse']))
    connect(delay, 'then', call, 'execute')
    connect(call, 'then', condition, 'execute')
    connect(call, 'ReturnValue', condition, 'Condition')
    call = bonus.graph_add_node_call_function(getattr(bp.GeneratedClass, SPAWN))
    exec_source.connect(call.node_find_pin('execute'))
    location.connect(call.node_find_pin('Position'))
    effect.connect(call.node_find_pin('Effect'))
    call.node_find_pin('ReturnValue').connect(debug)
    factory = DataAssetFactory()
    factory.DataAssetClass = UEPPythonMixinSet
    asset = ue.create_asset('DA_ArenaBombBaseMixin', '/Game/UEPMixins', UEPPythonMixinSet, factory)
    asset.DefaultProfile = 'Python'
    asset.Profiles = [UEPPythonMixinProfile(ProfileName=p, PythonModule='uep_lyra_world.arena_bomb_base_mixin',
        PythonClass='LyraArenaBombBase'+p+'Profile') for p in ('Python', 'BlueprintFallback')]
    ue.blueprint_configure_mixin(bp, asset, 'Python', SELECTOR)
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    after = defaults(bp, 'arena-bomb-base-after')
    after_shapes = {name: ue.describe_function(bp.GeneratedClass, name) for name in METHODS}
    after_hashes = {g.get_name(): semantics(g, names-({spawn.get_name()} if g == bonus else set()), ignored[g.get_name()]) for g, names in original}
    bad = [n.get_name() for n, guid in guids.items() if n.NodeGuid.as_dict() != guid]
    proof = dict(cdo_equal=before == after, signatures_before=shapes, signatures_after=after_shapes,
        graph_hashes_before=hashes, graph_hashes_after=after_hashes, bad_guids=bad,
        spawn_hash_before=spawn_hash, spawn_hash_after=semantics(backend, {spawn.get_name()}, set()),
        spawn_pins_before=spawn_before, spawn_pins_after=pins(spawn), native_delays=native_delays,
        attribute_literal=source.node_find_pin('Attribute').default_value,
        cosmetic_macro=cosmetic_source.MacroGraphReference.as_dict(),
        original_macro_instance_guid=nodes['K2Node_MacroInstance_2'].NodeGuid.as_dict())
    (out/'arena-bomb-base-preservation.json').write_text(json.dumps(proof, indent=2, default=str), encoding='utf-8')
    if int(bp.Status) == 2 or before != after or shapes != after_shapes or hashes != after_hashes or bad or proof['spawn_hash_before'] != proof['spawn_hash_after'] or spawn_before != pins(spawn):
        raise RuntimeError('base bomb CDO/ABI/GUID/native delay/macro/spawn/graph preservation differs')
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp)) != 207:
        raise RuntimeError('exact base bomb native transport footprint differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        row, = [r for r in ue.get_registered_mixins() if r['target_class'] == bp.GeneratedClass]
        counts = {p: len(v['functions']) for p, v in row['profiles'].items()}
        if counts != dict(Python=13, BlueprintFallback=13):
            raise RuntimeError('complete base bomb Profile family required')
    finally:
        ue.unregister_all_mixins()
    if sha(stage/CHILD) != child_hash:
        raise RuntimeError('accepted standard bomb package changed')
    bp.save_package()
    asset.save_package()
    return dict(status='passed', kind='arenabombbase', runtime_acceptance=False, full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True,
        original_cdo_abis_guids_components_graph_partitions_and_native_delays_preserved=True,
        original_macro_instance_and_four_delay_guids_preserved=True,
        original_bonus_spawn_node_defaults_and_exposed_effect_preserved=True,
        original_attribute_field_path_and_cosmetic_macro_preserved=True,
        unique_base_selector_and_accepted_child_bytes_preserved=True,
        empty_base_visual_and_construction_events_retained=True, child_asset=str(stage/CHILD), child_sha256=child_hash,
        method_counts=counts, original_nodes=156, interface_nodes=5, transport_nodes=46,
        new_business_nodes=0, native_end_adapter_nodes=0,
        assets=[RELATIVE, 'Content/UEPMixins/DA_ArenaBombBaseMixin.uasset'])
