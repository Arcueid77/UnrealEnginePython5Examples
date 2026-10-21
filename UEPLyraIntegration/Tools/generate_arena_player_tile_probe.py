"""Stage-only typed virtual calls into the retained player tile."""
import hashlib,json,sys,traceback
from pathlib import Path
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_arena_player_tile_probe.py')
sys.path.insert(0,str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_hud.arena_player_tile_mixin import CLASS,MONITOR,BOUND

PATH='/Game/UEPValidation/BP_ArenaPlayerTileProbe'
RELATIVE='Content/UEPValidation/BP_ArenaPlayerTileProbe.uasset'
def generate(stage):
    if (stage/RELATIVE).exists():raise RuntimeError('fresh Arena tile typed caller required')
    cls=ue.load_class(CLASS);signatures={name:ue.describe_function(cls,name) for name in ('Configure',MONITOR,BOUND)}
    bp=ue.create_blueprint(ue.find_class('Object'),PATH)
    for name,target in (('Configure','Configure'),('Monitor',MONITOR)):
        graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Tile');entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('LyraPlayerState')),'PlayerState');call=graph.graph_add_node_call_function(getattr(cls,target));connect(entry,'then',call,'execute');connect(entry,'Tile',call,'self');connect(entry,'PlayerState',call,'PlayerState')
        if len(graph.Nodes)!=2:raise RuntimeError('typed tile caller contains extra nodes')
    ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('Arena tile typed caller compile failed')
    bp.save_package()
    return dict(status='passed',stage_only=True,gameplay_business=False,typed_virtual_calls=True,callback_replayed=False,signatures=signatures,nodes=4,asset=str(stage/RELATIVE),sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
if __name__=='__main__':
    from stage_safety import require_authoring_stage
    result=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaPlayerTileProbeResult=')))
    try:
        stage=require_authoring_stage(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')),ue.convert_relative_path_to_full(ue.get_content_dir()));result.write_text(json.dumps(generate(stage),indent=2));ue.log('UEP_ARENA_PLAYER_TILE_PROBE_PASSED')
    except Exception:result.write_text(json.dumps(dict(status='failed',error=traceback.format_exc()),indent=2));raise
