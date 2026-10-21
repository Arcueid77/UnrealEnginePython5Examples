"""Preserve standard bomb parent construction, components, ABI and original graphs."""
import hashlib, json, sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics, make_gate, insert_gate
from uep_lyra_world.arena_bomb_visual_mixin import CLASS, CONSTRUCT

RELATIVE = 'Plugins/GameFeatures/TopDownArena/Content/Game/Bombs/B_Bomb_Standard.uasset'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generate(stage):
    official = Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    out = Path(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if sha(stage/RELATIVE) != sha(official/RELATIVE):
        raise RuntimeError('fresh original standard bomb required')
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, CLASS.removesuffix('_C'))
    before = canonical_cdo(snapshot(bp, 'arena-bomb-visual-before'))
    original = [(g, {n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    guids = {n: n.NodeGuid.as_dict() for g, _ in original for n in g.Nodes}
    methods = ('UserConstructionScript', 'ClientUpdateFireballVisuals')
    shapes = {m: ue.describe_function(bp.GeneratedClass, m) for m in methods}
    construction, = [g for g, _ in original if g.get_name() == 'UserConstructionScript']
    parent, = [n for n in construction.Nodes if n.get_class().get_name() == 'K2Node_CallParentFunction']
    target, = parent.node_find_pin('then').get_linked_to()
    ignored = {(parent.get_name(), 'then'), (target.owning_node.get_name(), target.name)}
    hashes = {g.get_name(): semantics(g, names, ignored if g == construction else set()) for g, names in original}
    if sum(len(names) for _, names in original) != 33:
        raise RuntimeError('original standard bomb graph footprint differs')
    make_gate(bp, CONSTRUCT, None)
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    insert_gate(construction, parent, 'then', getattr(bp.GeneratedClass, CONSTRUCT))
    factory = DataAssetFactory()
    factory.DataAssetClass = UEPPythonMixinSet
    asset = ue.create_asset('DA_ArenaBombVisualMixin', '/Game/UEPMixins', UEPPythonMixinSet, factory)
    asset.DefaultProfile = 'Python'
    asset.Profiles = [UEPPythonMixinProfile(ProfileName=p,
        PythonModule='uep_lyra_world.arena_bomb_visual_mixin',
        PythonClass='LyraArenaBombVisual'+p+'Profile') for p in ('Python', 'BlueprintFallback')]
    ue.blueprint_configure_mixin(bp, asset, 'Python', 'PythonMixinProfile')
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    after = canonical_cdo(snapshot(bp, 'arena-bomb-visual-after'))
    after_shapes = {m: ue.describe_function(bp.GeneratedClass, m) for m in methods}
    after_hashes = {g.get_name(): semantics(g, names, ignored if g == construction else set()) for g, names in original}
    bad = [n.get_name() for n, value in guids.items() if n.NodeGuid.as_dict() != value]
    proof = dict(cdo_equal=before == after, signatures_before=shapes, signatures_after=after_shapes,
                 graph_hashes_before=hashes, graph_hashes_after=after_hashes, bad_guids=bad)
    (out/'arena-bomb-visual-preservation.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
    if int(bp.Status) == 2 or before != after or shapes != after_shapes or hashes != after_hashes or bad or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp)) != 42:
        raise RuntimeError('standard bomb CDO/ABI/GUID/components/graphs changed')
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        row, = [r for r in ue.get_registered_mixins() if r['target_class'] == bp.GeneratedClass]
        counts = {p: len(v['functions']) for p, v in row['profiles'].items()}
        if counts != dict(Python=2, BlueprintFallback=2):
            raise RuntimeError('complete standard bomb Profile family required')
    finally:
        ue.unregister_all_mixins()
    bp.save_package()
    asset.save_package()
    return dict(status='passed', kind='arenabombvisual', runtime_acceptance=False, full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True,
        original_cdo_abis_guids_components_and_parent_construction_preserved=True,
        original_real_time_clock_and_local_array_scope_preserved=True,
        method_counts=counts, original_nodes=33, interface_nodes=5, transport_nodes=4,
        new_business_nodes=0, native_end_adapter_nodes=0,
        assets=[RELATIVE, 'Content/UEPMixins/DA_ArenaBombVisualMixin.uasset'])
