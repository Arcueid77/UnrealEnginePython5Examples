"""Move shared macro policy to Python;both Profiles share native latent class IO."""
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_VariableGet,K2Node_LoadAssetClass,K2Node_ClassDynamicCast,K2Node_GetSubsystem,K2Node_CustomEvent,K2Node_FunctionResult,K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_ui_experience_preparation_assets.py')
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_hud.experience_preparation_policy import AFTER,KEY
MACRO='Content/UI/Menu/Experiences/UIExperienceMacros.uasset'
FAMILIES={'selection':('experience_screen_mixin','W_ExperienceSelectionScreen','K2Node_MacroInstance_2',11),'host':('host_session_mixin','W_HostSessionScreen','K2Node_MacroInstance_3',13),'entry':('session_entry_mixin','W_SessionBrowserEntry','K2Node_MacroInstance_1',9)}
def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def methods(bp):
    names=set()
    for graph in ue.blueprint_get_all_graphs(bp):
        if graph.get_name()!='EventGraph' and any(n.get_class().get_name()=='K2Node_FunctionEntry' for n in graph.Nodes):names.add(graph.get_name())
        for n in graph.Nodes:
            if n.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):names.add(str(n.CustomFunctionName))
            if n.get_class().get_name()=='K2Node_Event':names.add(str(n.EventReference.MemberName))
    result={}
    for name in names:
        try:result[name]=ue.describe_function(bp.GeneratedClass,name)
        except AttributeError:
            graph=next(g for g in ue.blueprint_get_all_graphs(bp) if g.get_name()==name)
            if len(graph.Nodes)!=1:raise
    return result
def pins(node):return [(p.name,p.direction,p.category,p.sub_category,p.sub_category_object.get_path_name() if p.sub_category_object else None,p.default_value,str(p.default_text_value)) for p in node.node_pins()]
def generate():
    stage=require_authoring_stage(arg('UEPPreparationStage'),ue.convert_relative_path_to_full(ue.get_content_dir()));out=Path(arg('UEPPreparationResult')).parent;baseline=json.loads(Path(arg('UEPPreparationBaselines')).read_text(encoding='utf-8-sig'));official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    if sha(stage/MACRO)!=sha(official/MACRO):raise RuntimeError('original shared macro library required')
    library=ue.load_object(Blueprint,'/Game/UI/Menu/Experiences/UIExperienceMacros.UIExperienceMacros');source_graph,=ue.blueprint_get_all_graphs(library);source={n.get_name():n for n in source_graph.Nodes};macro_semantics=semantics(source_graph,set(source),set());macro_sha=sha(stage/MACRO)
    if len(source)!=7:raise RuntimeError('original UI macro footprint differs')
    repo=Path(script).resolve().parents[3];index=repo/'.build/LyraValidation/BlueprintPython/20261012-audit/blueprints.json';original=json.loads(index.read_text(encoding='utf-8-sig'));calls=[]
    for bp in original['blueprints']:
        for graph in bp['graphs']:
            for n in graph['nodes']:
                if n['class']=='K2Node_MacroInstance' and 'preparetoenteruserfacingexperience' in re.sub('[^a-z0-9]','',str(n.get('title','')).lower()):calls.append(dict(package=bp['path'],graph=graph['name'],node=n['name']))
    if sorted((c['package'].split('.')[-1],c['node']) for c in calls)!=sorted((v[1],v[2]) for v in FAMILIES.values()):raise RuntimeError('complete original UI preparation callsite census required')
    rows={};pending=[];roots=[];hidden=[];policies={}
    try:
        # Accepted parents do not yet declare the newly authored gate. Suppress
        # only that method during editor auto-registration of their old classes.
        # Restore it as soon as its native declaration has been compiled.
        for label,(module_name,_,_,_) in FAMILIES.items():
            policy=importlib.import_module('uep_lyra_hud.'+module_name);policies[label]=policy
            for profile in ('Python','BlueprintFallback'):
                cls=next(value for value in vars(policy).values() if isinstance(value,type) and value.__name__.endswith(profile+'Profile'));fn=vars(cls)[KEY];hidden.append((label,cls,fn));delattr(cls,KEY)
        for label,(module_name,name,macro_name,count) in FAMILIES.items():
            policy=policies[label];relative='Content/UI/Menu/Experiences/'+name+'.uasset';parent=baseline[label];ue.unregister_all_mixins();bp=ue.load_object(Blueprint,policy.CLASS.removesuffix('_C'));ue.unregister_all_mixins()
            if sha(stage/relative)!=parent['sha256'].lower():raise RuntimeError('accepted parent asset changed')
            for easing in ue.tobject_iterator(ue.find_class('MovieSceneBuiltInEasingFunction')):
                if easing.get_path_name().startswith(bp.get_path_name()+':') and not easing.is_rooted():easing.add_to_root();roots.append(easing)
            before=snapshot(bp,label+'-before');tree=visuals(bp,out,label+'-before');signatures=methods(bp);originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];event=bp.UbergraphPages[0];macro=next(n for n in event.Nodes if n.get_name()==macro_name);resolved=macro.node_get_macro_graph()
            if resolved!=source_graph:raise RuntimeError('original current preparation macro reference required')
            incoming=list(macro.node_find_pin('execute').get_linked_to());experience,=macro.node_find_pin('Experience').get_linked_to();following,=macro.node_find_pin('then').get_linked_to();ignored={g.get_name():set() for g,_ in originals};ignored[event.get_name()].add((macro_name,'execute'));ignored[event.get_name()].update((p.owning_node.get_name(),p.name) for p in incoming);hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};total=sum(len(ns) for _,ns in originals)
            getter=event.graph_add_node(K2Node_VariableGet);getter.VariableReference=ue.find_struct('MemberReference')(**source['K2Node_VariableGet_2'].VariableReference.as_dict());event.graph_reconstruct_node(getter);experience.make_link_to(getter.node_find_pin('self'));load=event.graph_add_node(K2Node_LoadAssetClass);connect(getter,'LoadingScreenWidget',load,'AssetClass')
            for p in incoming:p.break_link_to(macro.node_find_pin('execute'));p.make_link_to(load.node_find_pin('execute'))
            graph=ue.blueprint_add_function(bp,policy.GATES[KEY]);entry=graph.Nodes[0];entry.node_create_pin(1,kind(load.node_find_pin('Class')),'LoadedClass');result=graph.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute');alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=AFTER;event.graph_reconstruct_node(alias);alias.node_find_pin('then').make_link_to(following);ue.compile_blueprint(bp);ue.unregister_all_mixins()
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,policy.GATES[KEY]));branch=event.graph_add_node(K2Node_IfThenElse);connect(load,'Completed',call,'execute');connect(load,'Class',call,'LoadedClass');connect(call,'then',branch,'execute');connect(call,'ReturnValue',branch,'Condition');cast=event.graph_add_node(K2Node_ClassDynamicCast);cast.TargetType=source['K2Node_ClassDynamicCast_1'].TargetType;cast.set_property('PureState',source['K2Node_ClassDynamicCast_1'].get_property('PureState'));event.graph_reconstruct_node(cast);sub=event.graph_add_node(K2Node_GetSubsystem);sub.CustomClass=source['K2Node_GetSubsystem_3'].CustomClass;event.graph_reconstruct_node(sub);setter=event.graph_add_node_call_function(ue.find_class('LyraLoadingScreenSubsystem').SetLoadingScreenContentWidget);connect(branch,'then',setter,'execute');connect(load,'Class',cast,'Class');connect(cast,'AsUser Widget',setter,'NewWidgetClass');connect(sub,'ReturnValue',setter,'self');setter.node_find_pin('then').make_link_to(following);ue.compile_blueprint(bp);ue.unregister_all_mixins();after=methods(bp);old_current={name:after[name] for name in signatures}
            (out/(label+'-signatures.json')).write_text(json.dumps(dict(before=signatures,after=old_current),indent=2),encoding='utf-8')
            if int(bp.Status)==2 or old_current!=signatures or snapshot(bp,label+'-after')!=before or visuals(bp,out,label+'-after')!=tree:raise RuntimeError('UI preparation public ABI/CDO/tree/animations changed: '+label)
            if any(semantics(g,ns,ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original caller graph/GUID changed: '+label)
            added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total
            if added!=10 or pins(load)!=pins(source['K2Node_LoadAssetClass_0']) or cast.TargetType!=source['K2Node_ClassDynamicCast_1'].TargetType or sub.CustomClass!=source['K2Node_GetSubsystem_3'].CustomClass:raise RuntimeError('exact shared native load and typed fallback transport required: '+label)
            for family,cls,fn in hidden:
                if family==label:setattr(cls,KEY,fn)
            try:
                ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
                if counts!=dict.fromkeys(('Python','BlueprintFallback'),count):raise RuntimeError('complete revised preparation Profile family required')
            finally:ue.unregister_all_mixins()
            rows[label]=dict(relative=relative,before_sha256=parent['sha256'],added_transport_nodes=added,method_counts=counts,original_macro_instance_preserved_as_unwired_reference=True,all_incoming_original_exec_paths_share_one_native_load=True,native_load_node=load.get_name(),native_load_guid=load.NodeGuid.as_dict(),loaded_gate=policy.GATES[KEY],continuation_alias=AFTER);pending.append(bp)
        if sha(stage/MACRO)!=macro_sha or semantics(source_graph,set(source),set())!=macro_semantics:raise RuntimeError('original shared macro definition changed')
        for bp in pending:bp.save_package()
    finally:
        ue.unregister_all_mixins()
        for _,cls,fn in hidden:setattr(cls,KEY,fn)
        for obj in roots:obj.remove_from_root()
    return dict(status='passed',kind='uipreparation',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_macro_library_unchanged=True,original_macro_sha256=macro_sha,original_macro_graph_nodes=7,original_callsites=calls,source_index=dict(path=str(index),sha256=sha(index)),consumers=rows,all_original_caller_signatures_cdos_visuals_nodes_and_guids_preserved=True,one_native_latent_load_per_consumer_shared_by_both_profiles=True,python_pure_class_cast_setter_then_original_continuation=True,new_business_nodes=0,assets=[v['relative'] for v in rows.values()])
try:report=generate()
except Exception:report=dict(status='failed',error=traceback.format_exc());ue.log_error(report['error'])
Path(arg('UEPPreparationResult')).write_text(json.dumps(report,indent=2),encoding='utf-8')
if report['status']!='passed':raise RuntimeError(report['error'])
ue.log('UEP_UI_PREPARATION_AUTHORING_PASSED')
