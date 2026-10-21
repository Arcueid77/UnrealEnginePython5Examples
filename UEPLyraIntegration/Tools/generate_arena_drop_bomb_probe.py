"""Stage-only typed calls to original drop-ability methods and named tag outputs."""
import hashlib, json, sys, traceback
from pathlib import Path
script = globals().get('__file__') or next(v for v in sys.argv if Path(v).name == 'generate_arena_drop_bomb_probe.py')
sys.path.insert(0, str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_abilities.arena_drop_bomb_mixin import CLASS
RELATIVE = 'Content/UEPValidation/BP_ArenaDropBombProbe.uasset'


def kind(pin):
    return EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category,
        PinSubCategoryObject=pin.sub_category_object, ContainerType=pin.container_type,
        bIsReference=pin.is_reference, bIsConst=pin.is_const)


def generate(stage):
    if (stage/RELATIVE).exists():
        raise RuntimeError('fresh drop bomb native caller required')
    cls = ue.load_class(CLASS)
    bp = ue.create_blueprint(ue.find_class('Object'), '/Game/UEPValidation/BP_ArenaDropBombProbe')
    for method, inputs, outputs in (('GetBombSpawnLocation', ('AvatarActor',), ('ReturnValue',)),):
        graph = ue.blueprint_add_function(bp, method)
        entry = graph.Nodes[0]
        entry.node_create_pin(1, EdGraphPinType(PinCategory='object', PinSubCategoryObject=cls), 'Ability')
        call = graph.graph_add_node_call_function(getattr(cls, method))
        connect(entry, 'then', call, 'execute')
        connect(entry, 'Ability', call, 'self')
        for name in inputs:
            entry.node_create_pin(1, kind(call.node_find_pin(name)), name)
            connect(entry, name, call, name)
        result = graph.graph_add_node(K2Node_FunctionResult)
        for name in outputs:
            result.node_create_pin(0, kind(call.node_find_pin(name)), name)
            connect(call, name, result, name)
        connect(call, 'then', result, 'execute')
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2:
        raise RuntimeError('drop bomb native caller compile failed')
    bp.save_package()
    return dict(status='passed', stage_only=True, gameplay_business=False, typed_virtual_calls=True,
        callbacks_replayed=False, asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())


if __name__ == '__main__':
    from stage_safety import require_authoring_stage
    result = Path(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPArenaDropBombProbeResult=')))
    try:
        stage = require_authoring_stage(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')), ue.convert_relative_path_to_full(ue.get_content_dir()))
        result.write_text(json.dumps(generate(stage), indent=2), encoding='utf-8')
        ue.log('UEP_ARENA_DROP_BOMB_PROBE_PASSED')
    except Exception:
        result.write_text(json.dumps(dict(status='failed', error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise
