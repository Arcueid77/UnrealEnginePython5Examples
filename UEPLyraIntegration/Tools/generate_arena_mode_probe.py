"""Concrete owned mode fixture, typed message producer and native getter caller."""
import hashlib,json,sys,traceback
from pathlib import Path
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_arena_mode_probe.py')
sys.path.insert(0,str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult,Blueprint
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect,broadcast_graph
from uep_lyra_world.arena_mode_mixin import BASE
PATH='/Game/UEPValidation/BP_ArenaModeProbe'
FIXTURE='/Game/UEPValidation/BP_ArenaModeFixture'
def generate(stage):
    files=['Content/UEPValidation/BP_ArenaModeProbe.uasset','Content/UEPValidation/BP_ArenaModeFixture.uasset']
    if any((stage/p).exists() for p in files):raise RuntimeError('fresh mode fixture assets required')
    cls=ue.load_class(BASE);bp=ue.create_blueprint(ue.find_class('Object'),PATH);broadcast_graph(bp,'Verb',ue.find_struct('LyraVerbMessage'),ue.find_class('GameplayMessageSubsystem'));g=ue.blueprint_add_function(bp,'Remaining');entry=g.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Component');call=g.graph_add_node_call_function(cls.GetRoundTimeRemaining);result=g.graph_add_node(K2Node_FunctionResult);source=call.node_find_pin('SecondsRemaining');result.node_create_pin(0,EdGraphPinType(PinCategory=source.category,PinSubCategory=source.sub_category),'Seconds');connect(entry,'then',call,'execute');connect(entry,'Component',call,'self');connect(call,'then',result,'execute');connect(call,'SecondsRemaining',result,'Seconds');ue.compile_blueprint(bp)
    fixture=ue.create_blueprint(cls,FIXTURE);fixture.bGenerateAbstractClass=False;ue.compile_blueprint(fixture)
    if int(bp.Status)==2 or int(fixture.Status)==2:raise RuntimeError('mode probe/concrete fixture compilation failed')
    bp.save_package();fixture.save_package()
    return dict(status='passed',stage_only=True,gameplay_business=False,typed_virtual_calls=True,callbacks_replayed=False,native_broadcast=True,fixture_begin_not_overridden=True,signature=ue.describe_function(cls,'GetRoundTimeRemaining'),assets=[dict(asset=str(stage/p),sha256=hashlib.sha256((stage/p).read_bytes()).hexdigest()) for p in files],asset=str(stage/files[0]),sha256=hashlib.sha256((stage/files[0]).read_bytes()).hexdigest())
if __name__=='__main__':
    from stage_safety import require_authoring_stage
    result=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaModeProbeResult=')))
    try:
        stage=require_authoring_stage(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')),ue.convert_relative_path_to_full(ue.get_content_dir()));result.write_text(json.dumps(generate(stage),indent=2),encoding='utf-8');ue.log('UEP_ARENA_MODE_PROBE_PASSED')
    except Exception:result.write_text(json.dumps(dict(status='failed',error=traceback.format_exc()),indent=2),encoding='utf-8');raise
