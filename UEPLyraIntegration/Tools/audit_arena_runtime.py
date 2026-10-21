"""Read-only original graph/CDO/ABI inventory for every remaining Arena path."""
import hashlib,json,sys,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='audit_arena_runtime.py');sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics

def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def path(obj):return obj.get_path_name() if obj is not None else None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def nodes(g):
    rows=[]
    for node in g.Nodes:
        row=dict(node=node.get_name(),cls=node.get_class().get_name(),guid=node.NodeGuid.as_dict(),pins=[])
        for key,field in (('function','FunctionReference'),('event','EventReference'),('variable','VariableReference'),('delegate','DelegateReference')):
            try:ref=node.get_property(field);row[key]=dict(name=str(ref.MemberName),owner=path(ref.MemberParent))
            except Exception:pass
        if row['cls'] in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):row['custom_event']=str(node.CustomFunctionName)
        for pin in node.node_pins():row['pins'].append(dict(name=pin.name,category=pin.category,sub_category=pin.sub_category,direction=pin.direction,default=pin.default_value,default_object=path(pin.default_object),links=[p.owning_node.get_name()+'.'+p.name for p in pin.get_linked_to()]))
        rows.append(row)
    return rows

def audit():
    stage=require_authoring_stage(arg('UEPArenaStage'),ue.convert_relative_path_to_full(ue.get_content_dir()));out=Path(arg('UEPArenaResult')).parent;manifest=Path(script).resolve().parents[1]/'Migration/batches.json';scope=json.loads(manifest.read_text(encoding='utf-8-sig'));packages=[r['path'] for r in scope['assets'] if r['path'].startswith('/TopDownArena/') and r['status']=='not_accepted'];official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;hashes={str(manifest):sha(manifest)};assets={}
    if len(packages)!=20:raise RuntimeError('exact remaining20 original Arena candidates required')
    for package in packages:
        stem=package.split('.')[0];relative='Plugins/GameFeatures/TopDownArena/Content/'+stem.removeprefix('/TopDownArena/')+'.uasset';values={str(root/relative):sha(root/relative) for root in (official,stage)}
        if len(set(values.values()))!=1:raise RuntimeError('Arena original official/stage bytes differ: '+package)
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,package);ue.unregister_all_mixins();graphs=ue.blueprint_get_all_graphs(bp);data={g.get_name():nodes(g) for g in graphs};macros={g.get_name() for g in bp.get_property('MacroGraphs')};names={g.get_name() for g in bp.get_property('FunctionGraphs')}
        for entries in data.values():
            for entry in entries:
                if entry.get('custom_event'):names.add(entry['custom_event'])
                if entry['cls']=='K2Node_Event':names.add(entry['event']['name'])
        shapes={};unemitted=[]
        for name in sorted(names):
            try:shapes[name]=ue.describe_function(bp.GeneratedClass,name)
            except AttributeError:
                if len(data.get(name,[]))!=1:raise
                unemitted.append(name)
        name=stem.rsplit('/',1)[-1];folder=out/name;folder.mkdir();(folder/'graphs.json').write_text(json.dumps(data,indent=2));exports=[]
        objects=[(bp,'blueprint'),(bp.GeneratedClass.get_cdo(),'cdo')]
        for field,label in (('WidgetTree','widget-tree'),('SimpleConstructionScript','scs')):
            if field in bp.properties() and bp.get_property(field) is not None:objects.append((bp.get_property(field),label))
        for obj,label in objects:
            file=folder/(label+'.t3d')
            if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file)):raise RuntimeError('Arena original export failed')
            exports.append(dict(file=str(file.relative_to(out)),sha256=sha(file)))
        assets[package]=dict(relative=relative,parent=path(bp.ParentClass),abstract_blueprint=bool(bp.bGenerateAbstractClass),graph_nodes={g.get_name():len(g.Nodes) for g in graphs},graph_hashes={g.get_name():semantics(g,{n.get_name() for n in g.Nodes},set()) for g in graphs},macro_graphs=sorted(macros),signatures=shapes,unemitted_empty_graphs=unemitted,exports=exports,referencers=sorted(str(v) for v in ue.get_asset_referencers(stem,31)));hashes.update(values)
    if any(sha(p)!=digest for p,digest in hashes.items()):raise RuntimeError('read-only Arena audit changed inputs')
    return dict(status='passed',runtime_acceptance=False,full_acceptance=False,assets_modified=False,assets_saved_or_compiled=False,original_candidate_paths_retained=True,remaining_arena_business_migrated=False,reference_hashes=hashes,assets=assets,candidate_paths=packages)

try:report=audit()
except Exception:report=dict(status='failed',error=traceback.format_exc());ue.log_error(report['error'])
Path(arg('UEPArenaResult')).write_text(json.dumps(report,indent=2))
if report['status']!='passed':raise RuntimeError(report['error'])
ue.log('UEP_ARENA_RUNTIME_AUDIT_PASSED')
