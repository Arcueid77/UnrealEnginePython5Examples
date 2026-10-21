"""Stage-only native UIExtension delegate adapter; no gameplay decisions."""
import hashlib,json,sys,traceback
from pathlib import Path
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_arena_player_ui_probe.py')
sys.path.insert(0,str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult,K2Node_CreateDelegate,K2Node_Self
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect

PATH='/Game/UEPValidation/BP_ArenaPlayerUIProbe'
RELATIVE='Content/UEPValidation/BP_ArenaPlayerUIProbe.uasset'

def pin_type(pin):
    return EdGraphPinType(PinCategory=pin.category,PinSubCategory=pin.sub_category,PinSubCategoryObject=pin.sub_category_object,ContainerType=pin.container_type,bIsReference=pin.is_reference,bIsConst=pin.is_const)

def generate(stage):
    if (stage/RELATIVE).exists():raise RuntimeError('fresh Arena UI observer required')
    bp=ue.create_blueprint(ue.find_class('Object'),PATH)
    callback=ue.blueprint_add_function(bp,'Observe');entry=callback.Nodes[0]
    entry.node_create_pin(1,EdGraphPinType(PinCategory='byte',PinSubCategoryObject=ue.find_object('/Script/UIExtension.EUIExtensionAction')),'Action')
    entry.node_create_pin(1,EdGraphPinType(PinCategory='struct',PinSubCategoryObject=ue.find_struct('UIExtensionRequest'),bIsReference=True,bIsConst=True),'ExtensionRequest')
    graph=ue.blueprint_add_function(bp,'Install');entry=graph.Nodes[0];subsystem=ue.find_class('UIExtensionSubsystem');call=graph.graph_add_node_call_function(subsystem.K2_RegisterExtensionPoint)
    entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=subsystem),'Subsystem')
    entry.node_create_pin(1,pin_type(call.node_find_pin('AllowedDataClasses')),'AllowedDataClasses')
    call.node_find_pin('ExtensionPointTag').default_value='(TagName="TopDownArena.ExtensionPoint.Players")'
    call.node_find_pin('ExtensionPointTagMatchType').default_value='ExactMatch'
    delegate,owner=graph.graph_add_node(K2Node_CreateDelegate),graph.graph_add_node(K2Node_Self)
    connect(entry,'then',call,'execute');connect(entry,'Subsystem',call,'self');connect(entry,'AllowedDataClasses',call,'AllowedDataClasses')
    connect(owner,'self',delegate,'self');connect(delegate,'OutputDelegate',call,'ExtensionCallback');delegate.SelectedFunctionName='Observe'
    result=graph.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,pin_type(call.node_find_pin('ReturnValue')),'Handle')
    connect(call,'then',result,'execute');connect(call,'ReturnValue',result,'Handle')
    ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('Arena UI observer compile failed')
    if len(callback.Nodes)!=1 or len(graph.Nodes)!=5:raise RuntimeError('Arena observer contains unexpected nodes')
    bp.save_package()
    return dict(status='passed',stage_only=True,gameplay_business=False,native_extension_callback=True,callback='Observe',callback_nodes=1,install_nodes=5,asset=str(stage/RELATIVE),sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())

if __name__=='__main__':
    from stage_safety import require_authoring_stage
    result=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaPlayerUIProbeResult=')))
    try:
        stage=require_authoring_stage(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')),ue.convert_relative_path_to_full(ue.get_content_dir()))
        report=generate(stage);result.write_text(json.dumps(report,indent=2));ue.log('UEP_ARENA_PLAYER_UI_PROBE_PASSED')
    except Exception:
        result.write_text(json.dumps(dict(status='failed',error=traceback.format_exc()),indent=2));raise
