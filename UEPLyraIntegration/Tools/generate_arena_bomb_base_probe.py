"""Stage-only native bomb callers and native Arena attribute observation."""
import hashlib, json, sys, traceback
from pathlib import Path
script = globals().get('__file__') or next(v for v in sys.argv if Path(v).name == 'generate_arena_bomb_base_probe.py')
sys.path.insert(0, str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_world.arena_bomb_base_mixin import CLASS

RELATIVE = 'Content/UEPValidation/BP_ArenaBombBaseProbe.uasset'


def kind(pin):
    return EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category,
        PinSubCategoryObject=pin.sub_category_object, ContainerType=pin.container_type)


def generate(stage, out):
    if (stage/RELATIVE).exists():
        raise RuntimeError('fresh base bomb native caller required')
    cls = ue.load_class(CLASS)
    bp = ue.create_blueprint(ue.find_class('Object'), '/Game/UEPValidation/BP_ArenaBombBaseProbe')
    for method, parameters in (('ServerAddFireballInstance', ('DeltaX', 'DeltaY')), ('ServerExpandFireballInAllDirections', ()),
                               ('SnapshotRange', ()), ('SpawnBonus', ('Actor',)), ('OnRep_DirectionalRadius', ()), ('TriggerExplosion', ())):
        graph = ue.blueprint_add_function(bp, method)
        entry = graph.Nodes[0]
        entry.node_create_pin(1, EdGraphPinType(PinCategory='object', PinSubCategoryObject=cls), 'Bomb')
        call = graph.graph_add_node_call_function(getattr(cls, method))
        connect(entry, 'then', call, 'execute')
        connect(entry, 'Bomb', call, 'self')
        for parameter in parameters:
            entry.node_create_pin(1, kind(call.node_find_pin(parameter)), parameter)
            connect(entry, parameter, call, parameter)
        if method == 'ServerAddFireballInstance':
            result = graph.graph_add_node(K2Node_FunctionResult)
            for parameter in ('SpaceWasBlocked', 'SpawnedFireball'):
                result.node_create_pin(0, EdGraphPinType(PinCategory='bool'), parameter)
                connect(call, parameter, result, parameter)
            connect(call, 'then', result, 'execute')
    original = ue.load_object(Blueprint, CLASS.removesuffix('_C'))
    source, = [n for g in original.FunctionGraphs if g.get_name() == 'SnapshotRange' for n in g.Nodes if n.get_class().get_name() == 'K2Node_CallFunction' and str(n.FunctionReference.MemberName) == 'GetFloatAttribute']
    for attribute in ('BombRange', 'BombsRemaining'):
        graph = ue.blueprint_add_function(bp, 'Read'+attribute)
        entry = graph.Nodes[0]
        entry.node_create_pin(1, EdGraphPinType(PinCategory='object', PinSubCategoryObject=ue.find_class('Actor')), 'Actor')
        call = graph.graph_add_node_call_function(ue.find_class('AbilitySystemBlueprintLibrary').GetFloatAttribute)
        call.node_find_pin('Attribute').default_value = source.node_find_pin('Attribute').default_value.replace('BombRange', attribute)
        result = graph.graph_add_node(K2Node_FunctionResult)
        result.node_create_pin(0, EdGraphPinType(PinCategory='real', PinSubCategory='float'), 'Value')
        result.node_create_pin(0, EdGraphPinType(PinCategory='bool'), 'Found')
        connect(entry, 'then', result, 'execute')
        connect(entry, 'Actor', call, 'Actor')
        connect(call, 'ReturnValue', result, 'Value')
        connect(call, 'bSuccessfullyFoundAttribute', result, 'Found')
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2:
        raise RuntimeError('base bomb native caller compile failed')
    bp.save_package()
    effect = ue.load_class('/TopDownArena/Game/Bombs/GE_Damaged_By_Bomb.GE_Damaged_By_Bomb_C')
    ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(effect.get_cdo(), str(out/'bomb-damage-cdo.t3d'))
    return dict(status='passed', stage_only=True, gameplay_business=False, typed_virtual_calls=True,
        callbacks_replayed=False, asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())


if __name__ == '__main__':
    from stage_safety import require_authoring_stage
    result = Path(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPArenaBombBaseProbeResult=')))
    try:
        stage = require_authoring_stage(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')), ue.convert_relative_path_to_full(ue.get_content_dir()))
        result.write_text(json.dumps(generate(stage, result.parent), indent=2), encoding='utf-8')
        ue.log('UEP_ARENA_BOMB_BASE_PROBE_PASSED')
    except Exception:
        result.write_text(json.dumps(dict(status='failed', error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise
