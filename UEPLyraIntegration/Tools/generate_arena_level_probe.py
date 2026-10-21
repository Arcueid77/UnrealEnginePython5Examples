"""Native typed calls to original editor-facing grid functions and named bool out."""
import hashlib,json,sys,traceback
from pathlib import Path
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_arena_level_probe.py')
sys.path.insert(0,str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_world.arena_level_mixin import CLASS
RELATIVE='Content/UEPValidation/BP_ArenaLevelProbe.uasset'
def kind(p):return EdGraphPinType(PinCategory=p.category,PinSubCategory=p.sub_category,PinSubCategoryObject=p.sub_category_object,ContainerType=p.container_type,bIsReference=p.is_reference,bIsConst=p.is_const)
def generate(stage):
    if (stage/RELATIVE).exists():raise RuntimeError('fresh grid probe required')
    cls=ue.load_class(CLASS);bp=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_ArenaLevelProbe')
    for method in ('GenerateLevel','ClearWalls','BlockingPlayerSpawn','DistanceBlocking'):
        g=ue.blueprint_add_function(bp,method);entry=g.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Generator');call=g.graph_add_node_call_function(getattr(cls,method));connect(entry,'then',call,'execute');connect(entry,'Generator',call,'self')
        if method=='DistanceBlocking':
            entry.node_create_pin(1,kind(call.node_find_pin('A')),'Point');connect(entry,'Point',call,'A');result=g.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'Allowed');connect(call,'then',result,'execute');connect(call,'CanSpawn',result,'Allowed')
    ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('native grid caller compile failed')
    bp.save_package();return dict(status='passed',stage_only=True,gameplay_business=False,typed_virtual_calls=True,callbacks_replayed=False,signatures={m:ue.describe_function(cls,m) for m in ('GenerateLevel','ClearWalls','BlockingPlayerSpawn','DistanceBlocking')},asset=str(stage/RELATIVE),sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
if __name__=='__main__':
    from stage_safety import require_authoring_stage
    result=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaLevelProbeResult=')))
    try:
        stage=require_authoring_stage(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')),ue.convert_relative_path_to_full(ue.get_content_dir()));result.write_text(json.dumps(generate(stage),indent=2),encoding='utf-8');ue.log('UEP_ARENA_LEVEL_PROBE_PASSED')
    except Exception:result.write_text(json.dumps(dict(status='failed',error=traceback.format_exc()),indent=2),encoding='utf-8');raise
