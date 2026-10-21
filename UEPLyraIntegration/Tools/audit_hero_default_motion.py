"""Read-only audit of the still-original parent motion dispatch graph."""
import hashlib,json,sys,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='audit_hero_default_motion.py');sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
PACKAGE='/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default'

def arg(key):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+key+'='))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def nodes(g):
    result=[]
    for n in g.Nodes:
        row=dict(node=n.get_name(),cls=n.get_class().get_name(),guid=n.NodeGuid.as_dict(),pins=[])
        for key,field in (('function','FunctionReference'),('event','EventReference'),('variable','VariableReference')):
            try:ref=n.get_property(field);row[key]=dict(name=str(ref.MemberName),owner=ref.MemberParent.get_path_name() if ref.MemberParent else None)
            except Exception:pass
        for pin in n.node_pins():row['pins'].append(dict(name=pin.name,category=pin.category,direction=pin.direction,default=pin.default_value,default_object=pin.default_object.get_path_name() if pin.default_object else None,links=[p.owning_node.get_name()+'.'+p.name for p in pin.get_linked_to()]))
        result.append(row)
    return result

def audit():
    stage=require_authoring_stage(arg('UEPHeroDefaultStage'),ue.convert_relative_path_to_full(ue.get_content_dir()));baseline=Path(arg('UEPHeroDefaultBaseline'));summary=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'));proof=json.loads((baseline/'assets.json').read_text(encoding='utf-8-sig'));out=Path(arg('UEPHeroDefaultResult')).parent
    if summary['status']!='passed' or proof['kind']!='herodefaultdeath' or proof['method_counts']!=dict(Python=5,BlueprintFallback=5):raise RuntimeError('accepted five-method parent baseline required')
    hashes={str(baseline/name):digest(baseline/name) for name in ('summary.json','assets.json')}
    for row in summary['assets']:
        for key in ('stage','overlay'):
            if digest(row[key]).upper()!=row['sha256'].upper():raise RuntimeError('accepted parent baseline changed')
            hashes[row[key]]=digest(row[key])
    historic=baseline.parents[1]/'20261021-hero-default/Audit01/audit.json';original=json.loads(historic.read_text(encoding='utf-8-sig'));hashes[str(historic)]=digest(historic)
    official=next(p for p in original['reference_hashes'] if 'Full' not in p)
    if digest(official)!=original['reference_hashes'][official]:raise RuntimeError('official original parent changed')
    hashes[official]=digest(official);ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();graph,=[g for g in ue.blueprint_get_all_graphs(bp) if g.get_name()=='EventGraph'];graph_hash=semantics(graph,{n.get_name() for n in graph.Nodes},set())
    if graph_hash!=original['asset']['graph_hashes']['EventGraph']:raise RuntimeError('original parent EventGraph changed')
    data=nodes(graph);(out/'motion-original-event-graph.json').write_text(json.dumps(data,indent=2));motion,=[r for r in data if r.get('event',{}).get('name')=='AnimMotionEffect'];branch,=[r for r in data if r['cls']=='K2Node_IfThenElse'];spawn,=[r for r in data if r['cls']=='K2Node_SpawnActorFromClass'];attach,=[r for r in data if r.get('function',{}).get('name')=='K2_AttachToComponent'];forward,=[r for r in data if r.get('function',{}).get('name')=='AnimMotionEffect']
    foot=ue.load_object(Blueprint,'/Game/Effects/Blueprints/B_FootStep.B_FootStep');foot_graphs={g.get_name():nodes(g) for g in ue.blueprint_get_all_graphs(foot)};(out/'footstep-current-graphs.json').write_text(json.dumps(foot_graphs,indent=2))
    for path,value in hashes.items():
        if digest(path)!=value:raise RuntimeError('read-only motion audit changed input')
    return dict(status='passed',runtime_acceptance=False,full_acceptance=False,assets_modified=False,assets_saved_or_compiled=False,reference_hashes=hashes,asset=dict(package=PACKAGE,signature=ue.describe_function(bp.GeneratedClass,'AnimMotionEffect'),event_graph_hash=graph_hash,motion_event=motion,server_branch=branch,spawn=spawn,attachment=attach,forward=forward,footstep_class_defaults=dict(right_bone=str(foot.GeneratedClass.get_cdo().get_property('FootStepRightFootBone')),skeletal_mesh_component=foot.GeneratedClass.get_cdo().get_property('Skeletal Mesh Component') is not None)),whole_parent_business_migrated=False,client_execution_tested=False)

try:report=audit()
except Exception:report=dict(status='failed',error=traceback.format_exc());ue.log_error(report['error'])
Path(arg('UEPHeroDefaultResult')).write_text(json.dumps(report,indent=2))
if report['status']!='passed':raise RuntimeError(report['error'])
ue.log('UEP_HERO_DEFAULT_MOTION_AUDIT_PASSED')
