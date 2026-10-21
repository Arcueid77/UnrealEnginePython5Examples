"""Read-only full original B_Hero_Default graph/ABI/component/descendant audit."""
import hashlib,json,sys,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='audit_hero_default.py');sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
PACKAGE='/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default'
RELATIVE='Content/Characters/Heroes/B_Hero_Default.uasset'
def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def path(obj):return obj.get_path_name() if obj is not None else None
def nodes(graph):
    result=[]
    for node in graph.Nodes:
        row=dict(node=node.get_name(),cls=node.get_class().get_name(),guid=node.NodeGuid.as_dict(),pins=[])
        for label,field in (('function','FunctionReference'),('event','EventReference'),('variable','VariableReference'),('delegate','DelegateReference')):
            try:r=node.get_property(field);row[label]=dict(name=str(r.MemberName),owner=path(r.MemberParent))
            except Exception:pass
        if node.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):row['custom_event']=str(node.CustomFunctionName)
        for p in node.node_pins():row['pins'].append(dict(name=p.name,category=p.category,direction=p.direction,default=p.default_value,default_object=path(p.default_object),links=[v.owning_node.get_name()+'.'+v.name for v in p.get_linked_to()]))
        result.append(row)
    return result
def export(obj,out,label):
    file=out/(label+'.t3d')
    if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file)):raise RuntimeError('native parent export failed')
    return dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
def audit():
    stage=require_authoring_stage(arg('UEPHeroDefaultStage'),ue.convert_relative_path_to_full(ue.get_content_dir()));out=Path(arg('UEPHeroDefaultResult')).parent;official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;hashes={str(root/RELATIVE):hashlib.sha256((root/RELATIVE).read_bytes()).hexdigest() for root in (official,stage)}
    if len(set(hashes.values()))!=1:raise RuntimeError('original B_Hero_Default official/stage hash differs')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();graphs=ue.blueprint_get_all_graphs(bp);data={g.get_name():nodes(g) for g in graphs};names={g.get_name() for g in graphs if g.get_name()!='EventGraph'}
    for rows in data.values():
        for n in rows:
            if 'custom_event' in n:names.add(n['custom_event'])
            if n['cls']=='K2Node_Event':names.add(n['event']['name'])
    shapes={};empty=[]
    for name in names:
        try:shapes[name]=ue.describe_function(bp.GeneratedClass,name)
        except AttributeError:
            if len(data.get(name,[]))!=1:raise
            empty.append(name)
    exports=[export(bp,out,'hero-default-blueprint'),export(bp.GeneratedClass.get_cdo(),out,'hero-default-cdo')];scs=bp.get_property('SimpleConstructionScript')
    if scs is not None:
        exports.append(export(scs,out,'hero-default-scs'))
        for n in scs.AllNodes:
            if n.ComponentTemplate is not None:exports.append(export(n.ComponentTemplate,out,'hero-default-'+n.get_name()+'-component'))
    (out/'hero-default-graphs.json').write_text(json.dumps(data,indent=2));refs=ue.get_asset_referencers(PACKAGE.split('.')[0],31)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in hashes.items()):raise RuntimeError('read-only parent audit changed bytes')
    return dict(status='passed',runtime_acceptance=False,full_acceptance=False,assets_modified=False,assets_saved_or_compiled=False,reference_hashes=hashes,asset=dict(package=PACKAGE,relative=RELATIVE,parent=path(bp.ParentClass),abstract_blueprint=bool(bp.bGenerateAbstractClass),graphs=data,signatures=shapes,unemitted_empty_graphs=empty,exports=exports,referencers=sorted(str(v) for v in refs),graph_hashes={g.get_name():semantics(g,{n.get_name() for n in g.Nodes},set()) for g in graphs}))
try:report=audit()
except Exception:report=dict(status='failed',error=traceback.format_exc());ue.log_error(report['error'])
Path(arg('UEPHeroDefaultResult')).write_text(json.dumps(report,indent=2))
if report['status']!='passed':raise RuntimeError(report['error'])
ue.log('UEP_HERO_DEFAULT_AUDIT_PASSED')
