"""Stage-only native virtual caller for the standard bomb visual function."""
import hashlib, json, sys, traceback
from pathlib import Path
script = globals().get('__file__') or next(v for v in sys.argv if Path(v).name == 'generate_arena_bomb_visual_probe.py')
sys.path.insert(0, str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_world.arena_bomb_visual_mixin import CLASS
RELATIVE = 'Content/UEPValidation/BP_ArenaBombVisualProbe.uasset'


def generate(stage):
    if (stage/RELATIVE).exists():
        raise RuntimeError('fresh bomb visual caller required')
    cls = ue.load_class(CLASS)
    bp = ue.create_blueprint(ue.find_class('Object'), '/Game/UEPValidation/BP_ArenaBombVisualProbe')
    graph = ue.blueprint_add_function(bp, 'UpdateVisuals')
    entry = graph.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory='object', PinSubCategoryObject=cls), 'Bomb')
    call = graph.graph_add_node_call_function(cls.ClientUpdateFireballVisuals)
    connect(entry, 'then', call, 'execute')
    connect(entry, 'Bomb', call, 'self')
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2:
        raise RuntimeError('native bomb visual caller compile failed')
    bp.save_package()
    return dict(status='passed', stage_only=True, gameplay_business=False, typed_virtual_calls=True,
                callbacks_replayed=False, asset=str(stage/RELATIVE),
                sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())


if __name__ == '__main__':
    from stage_safety import require_authoring_stage
    result = Path(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPArenaBombVisualProbeResult=')))
    try:
        stage = require_authoring_stage(next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')), ue.convert_relative_path_to_full(ue.get_content_dir()))
        result.write_text(json.dumps(generate(stage), indent=2), encoding='utf-8')
        ue.log('UEP_ARENA_BOMB_VISUAL_PROBE_PASSED')
    except Exception:
        result.write_text(json.dumps(dict(status='failed', error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise
