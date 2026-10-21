"""Owned typed list calls; timer ticks/ExperienceReady are never replayed."""
import hashlib,json,sys,traceback
from pathlib import Path
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_arena_hud_probe.py')
sys.path.insert(0,str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.classes import K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_hud.arena_hud_mixin import LIST,TIMER,READY
PATH='/Game/UEPValidation/BP_ArenaHUDProbe'
RELATIVE='Content/UEPValidation/BP_ArenaHUDProbe.uasset'
def kind(p):return EdGraphPinType(PinCategory=p.category,PinSubCategory=p.sub_category,PinSubCategoryObject=p.sub_category_object,ContainerType=p.container_type,bIsReference=p.is_reference,bIsConst=p.is_const)
def generate(stage):
    if (stage/RELATIVE).exists():raise RuntimeError('fresh typed Arena HUD caller required')
    cls=ue.load_class(LIST);timer=ue.load_class(TIMER);signatures={name:ue.describe_function(cls,name) for name in ('OnGetWidgetClassForData_0','OnConfigureWidgetForData_0')};signatures.update({name:ue.describe_function(timer,name) for name in ('Construct','Tick',READY)})
    bp=ue.create_blueprint(ue.find_class('Object'),PATH)
    for name,target in (('Select','OnGetWidgetClassForData_0'),('Configure','OnConfigureWidgetForData_0')):
        graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];call=graph.graph_add_node_call_function(getattr(cls,target));entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Host');connect(entry,'Host',call,'self');connect(entry,'then',call,'execute')
        for pin in call.node_pins():
            if pin.direction==0 and pin.category not in ('exec','delegate') and pin.name!='self':entry.node_create_pin(1,kind(pin),pin.name);connect(entry,pin.name,call,pin.name)
        if name=='Select':
            result=graph.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,kind(call.node_find_pin('ReturnValue')),'Result');connect(call,'then',result,'execute');connect(call,'ReturnValue',result,'Result')
    ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('Arena HUD typed list caller compile failed')
    bp.save_package()
    return dict(status='passed',stage_only=True,gameplay_business=False,typed_virtual_calls=True,callback_replayed=False,timer_tick_or_ready_called=False,signatures=signatures,asset=str(stage/RELATIVE),sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
if __name__=='__main__':
    from stage_safety import require_authoring_stage
    result=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaHUDProbeResult=')))
    try:
        stage=require_authoring_stage(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')),ue.convert_relative_path_to_full(ue.get_content_dir()));result.write_text(json.dumps(generate(stage),indent=2));ue.log('UEP_ARENA_HUD_PROBE_PASSED')
    except Exception:result.write_text(json.dumps(dict(status='failed',error=traceback.format_exc()),indent=2));raise
