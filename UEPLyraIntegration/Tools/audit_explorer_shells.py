"""Read-only current UE audit of original forwarding shells and empty prompt."""
import hashlib,json,sys,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='audit_explorer_shells.py');sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from explorer_shell_review import classify_actor,classify_prompt
from mixin_graph_gates import semantics
ASSETS={'character':('/Game/Characters/Character_Default.Character_Default','Content/Characters/Character_Default.uasset'),'base':('/Game/Characters/Heroes/B_SimpleHeroPawn.B_SimpleHeroPawn','Content/Characters/Heroes/B_SimpleHeroPawn.uasset'),'simple':('/ShooterExplorer/Blueprint/B_SimpleFollowPawn.B_SimpleFollowPawn','Plugins/GameFeatures/ShooterExplorer/Content/Blueprint/B_SimpleFollowPawn.uasset'),'big':('/ShooterExplorer/Blueprint/B_SimpleFollowPawn_Big.B_SimpleFollowPawn_Big','Plugins/GameFeatures/ShooterExplorer/Content/Blueprint/B_SimpleFollowPawn_Big.uasset'),'prompt':('/ShooterExplorer/UserInterface/W_InteractionPrompt.W_InteractionPrompt','Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_InteractionPrompt.uasset')}
def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def path(obj):return obj.get_path_name() if obj is not None else None
def rows(graph):
    result=[]
    for node in graph.Nodes:
        n=dict(node=node.get_name(),cls=node.get_class().get_name(),pins=[])
        for label,field in (('function','FunctionReference'),('event','EventReference')):
            try:r=node.get_property(field);n[label]=dict(name=str(r.MemberName),owner=path(r.MemberParent))
            except Exception:pass
        for p in node.node_pins():n['pins'].append(dict(name=p.name,direction=p.direction,category=p.category,links=[q.owning_node.get_name()+'.'+q.name for q in p.get_linked_to()]))
        result.append(n)
    return result
def audit():
    stage=require_authoring_stage(arg('UEPExplorerShellStage'),ue.convert_relative_path_to_full(ue.get_content_dir()));out=Path(arg('UEPExplorerShellResult')).parent;official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;assets={};hashes={}
    for key,(package,relative) in ASSETS.items():
        values={str(root/relative):hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (official,stage)}
        if len(set(values.values()))!=1:raise RuntimeError('retained shell/prompt original asset changed')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,package);ue.unregister_all_mixins();graphs=ue.blueprint_get_all_graphs(bp);data={g.get_name():rows(g) for g in graphs};classification=classify_prompt(data) if key=='prompt' else classify_actor(data);exports=[]
        for obj,label in ((bp,'blueprint'),(bp.GeneratedClass.get_cdo(),'cdo'),*(([(bp.get_property('WidgetTree'),'widget-tree')] if key=='prompt' else []))):
            file=out/(key+'-'+label+'.t3d')
            if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file)):raise RuntimeError('native retained shell export failed')
            exports.append(dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
        shapes={name:ue.describe_function(bp.GeneratedClass,name) for name in (('BindIndicator','Construct','PreConstruct','Tick') if key=='prompt' else ('UserConstructionScript','ReceiveBeginPlay','ReceiveTick','ReceiveActorBeginOverlap'))};(out/(key+'-graphs.json')).write_text(json.dumps(data,indent=2));assets[key]=dict(package=package,relative=relative,parent=path(bp.ParentClass),abstract_blueprint=bool(bp.bGenerateAbstractClass),classification=classification,signatures=shapes,exports=exports,graph_hashes={g.get_name():semantics(g,{n.get_name() for n in g.Nodes},set()) for g in graphs});hashes.update(values)
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=v for p,v in values.items()):raise RuntimeError('read-only retained shell audit changed bytes')
    return dict(status='passed',runtime_acceptance=False,full_acceptance=False,assets_modified=False,assets_saved_or_compiled=False,reference_hashes=hashes,assets=assets,original_candidate_paths_retained=True,inherited_parent_business_migrated=False)
try:report=audit()
except Exception:report=dict(status='failed',error=traceback.format_exc());ue.log_error(report['error'])
Path(arg('UEPExplorerShellResult')).write_text(json.dumps(report,indent=2))
if report['status']!='passed':raise RuntimeError(report['error'])
ue.log('UEP_EXPLORER_SHELL_AUDIT_PASSED')
