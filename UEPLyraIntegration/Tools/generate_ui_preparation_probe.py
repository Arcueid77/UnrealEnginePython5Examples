"""Stage-only exact original loading macro and native continuation counters."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent,K2Node_MacroInstance
from unreal_engine.structs import EdGraphPinType
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_ui_preparation_probe.py')
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from generate_accolade_widget_assets import kind
from message_payload_graphs import connect
from mixin_graph_gates import semantics
RELATIVE='Content/UEPValidation/W_UIExperiencePreparationProbe.uasset'
def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def generate():
    stage=require_authoring_stage(arg('UEPPreparationProbeStage'),ue.convert_relative_path_to_full(ue.get_content_dir()));source_path='/Game/UI/Menu/Experiences/W_NonInteractiveSpinner.W_NonInteractiveSpinner';library=ue.load_object(Blueprint,'/Game/UI/Menu/Experiences/UIExperienceMacros.UIExperienceMacros');macro,=ue.blueprint_get_all_graphs(library);names={n.get_name() for n in macro.Nodes};digest=semantics(macro,names,set())
    if len(names)!=7 or (stage/RELATIVE).exists():raise RuntimeError('fresh exact original UI macro probe required')
    bp=ue.duplicate_asset(source_path,'/Game/UEPValidation/W_UIExperiencePreparationProbe','W_UIExperiencePreparationProbe');ue.unregister_all_mixins();event=bp.UbergraphPages[0]
    for name in ('OriginalCount','HelperCount'):ue.blueprint_add_member_variable(bp,name,EdGraphPinType(PinCategory='int'))
    ue.compile_blueprint(bp);ue.unregister_all_mixins();start=event.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName='RunOriginal';event.graph_reconstruct_node(start);instance=event.graph_add_node(K2Node_MacroInstance);instance.set_property('MacroGraphReference',ue.find_struct('GraphReference')(MacroGraph=macro,GraphBlueprint=library,GraphGuid=macro.get_property('GraphGuid')));event.graph_reconstruct_node(instance);start.node_create_pin(1,kind(instance.node_find_pin('Experience')),'Experience');connect(start,'then',instance,'execute');connect(start,'Experience',instance,'Experience')
    for counter,entry in (('OriginalCount',instance),('HelperCount',None)):
        if entry is None:entry=event.graph_add_node(K2Node_CustomEvent);entry.CustomFunctionName='HelperCompleted';event.graph_reconstruct_node(entry)
        getter=event.graph_add_node_variable_get(counter);setter=event.graph_add_node_variable_set(counter);add=event.graph_add_node_call_function(ue.find_class('KismetMathLibrary').Add_IntInt);connect(getter,counter,add,'A');add.node_find_pin('B').default_value='1';connect(add,'ReturnValue',setter,counter);connect(entry,'then',setter,'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or instance.node_get_macro_graph()!=macro or semantics(macro,names,set())!=digest:raise RuntimeError('exact original native UI macro probe compile failed')
    bp.save_package();return dict(status='passed',kind='uipreparationprobe',stage_only=True,production_assets_saved=False,original_macro_nodes=7,original_macro_graph_hash=digest,original_macro_unchanged=True,fixture=dict(relative=RELATIVE,asset=str(stage/RELATIVE),sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()))
try:report=generate()
except Exception:report=dict(status='failed',error=traceback.format_exc());ue.log_error(report['error'])
Path(arg('UEPPreparationProbeResult')).write_text(json.dumps(report,indent=2),encoding='utf-8')
if report['status']!='passed':raise RuntimeError(report['error'])
ue.log('UEP_UI_PREPARATION_PROBE_AUTHORING_PASSED')
