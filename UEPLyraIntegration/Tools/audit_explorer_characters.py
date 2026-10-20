"""Read-only remaining Explorer character/interaction/UI family graphs."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint

script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='audit_explorer_characters.py')
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics

ASSETS={'hero': ('/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer', 'Plugins/GameFeatures/ShooterExplorer/Content/Blueprint/B_Hero_Explorer.uasset'), 'pawn': ('/ShooterExplorer/Blueprint/B_Pawn_Explorer.B_Pawn_Explorer', 'Plugins/GameFeatures/ShooterExplorer/Content/Blueprint/B_Pawn_Explorer.uasset'), 'simple': ('/ShooterExplorer/Blueprint/B_SimpleFollowPawn.B_SimpleFollowPawn', 'Plugins/GameFeatures/ShooterExplorer/Content/Blueprint/B_SimpleFollowPawn.uasset'), 'big': ('/ShooterExplorer/Blueprint/B_SimpleFollowPawn_Big.B_SimpleFollowPawn_Big', 'Plugins/GameFeatures/ShooterExplorer/Content/Blueprint/B_SimpleFollowPawn_Big.uasset'), 'interact': ('/ShooterExplorer/Input/Abilities/GA_Interact.GA_Interact', 'Plugins/GameFeatures/ShooterExplorer/Content/Input/Abilities/GA_Interact.uasset'), 'marker': ('/ShooterExplorer/Input/Abilities/GA_ToggleMarkerInWorld.GA_ToggleMarkerInWorld', 'Plugins/GameFeatures/ShooterExplorer/Content/Input/Abilities/GA_ToggleMarkerInWorld.uasset'), 'collect': ('/ShooterExplorer/Interact/GA_Interaction_Collect.GA_Interaction_Collect', 'Plugins/GameFeatures/ShooterExplorer/Content/Interact/GA_Interaction_Collect.uasset'), 'sit': ('/ShooterExplorer/Interact/GA_Interaction_Sit.GA_Interaction_Sit', 'Plugins/GameFeatures/ShooterExplorer/Content/Interact/GA_Interaction_Sit.uasset'), 'prompt': ('/ShooterExplorer/UserInterface/W_InteractionPrompt.W_InteractionPrompt', 'Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_InteractionPrompt.uasset'), 'grid': ('/ShooterExplorer/UserInterface/W_InventoryGrid.W_InventoryGrid', 'Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_InventoryGrid.uasset'), 'screen': ('/ShooterExplorer/UserInterface/W_InventoryScreen.W_InventoryScreen', 'Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_InventoryScreen.uasset'), 'list': ('/ShooterExplorer/UserInterface/W_ItemAcquiredList.W_ItemAcquiredList', 'Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_ItemAcquiredList.uasset'), 'toast': ('/ShooterExplorer/UserInterface/W_ItemAcquiredToastRow.W_ItemAcquiredToastRow', 'Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_ItemAcquiredToastRow.uasset'), 'map': ('/ShooterExplorer/UserInterface/W_MapScreen.W_MapScreen', 'Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/W_MapScreen.uasset'), 'cue': ('/ShooterMaps/GameplayCues/GC_Collect_Effect.GC_Collect_Effect', 'Plugins/GameFeatures/ShooterMaps/Content/GameplayCues/GC_Collect_Effect.uasset'), 'reference_shooter': ('/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin', 'Plugins/GameFeatures/ShooterCore/Content/Game/B_Hero_ShooterMannequin.uasset')}


def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def path(value):return value.get_path_name() if value is not None else None


def rows(graph):
    result=[]
    for node in graph.Nodes:
        row=dict(node=node.get_name(),cls=node.get_class().get_name(),pins=[])
        for label,field in (('function','FunctionReference'),('event','EventReference'),('variable','VariableReference'),('delegate','DelegateReference')):
            try:
                ref=node.get_property(field);row[label]=dict(name=str(ref.MemberName),owner=path(ref.MemberParent),scope=str(ref.MemberScope),self_context=bool(ref.bSelfContext))
            except Exception:pass
        if node.get_class().get_name() in ('K2Node_CustomEvent','K2Node_ComponentBoundEvent'):row['custom_event']=str(node.CustomFunctionName)
        for p in node.node_pins():row['pins'].append(dict(name=p.name,direction=p.direction,category=p.category,subcategory=p.sub_category,object=path(p.sub_category_object),default=p.default_value,default_object=path(p.default_object),links=[v.owning_node.get_name()+'.'+v.name for v in p.get_linked_to()]))
        result.append(row)
    return result


def export(obj,file):
    if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file)):raise RuntimeError('native object export failed: '+str(file))
    return dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest())


def templates(bp,root,label):
    result=[];scs=bp.get_property('SimpleConstructionScript')
    if scs is not None:
        result.append(export(scs,root/(label+'-scs.t3d')))
        for node in scs.AllNodes:
            if node.ComponentTemplate is not None:result.append(export(node.ComponentTemplate,root/(label+'-'+node.get_name()+'-component.t3d')))
    return result


def audit():
    stage=require_authoring_stage(arg('UEPExplorerCharacterAuditStage'),ue.convert_relative_path_to_full(ue.get_content_dir()));root=Path(arg('UEPExplorerCharacterAuditResult')).parent
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;assets={}
    for label,(package,relative) in ASSETS.items():
        file=stage/relative;digest=hashlib.sha256(file.read_bytes()).hexdigest()
        if digest!=hashlib.sha256((official/relative).read_bytes()).hexdigest():raise RuntimeError('original frontend widget asset required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,package);ue.unregister_all_mixins();graphs=ue.blueprint_get_all_graphs(bp)
        data={g.get_name():rows(g) for g in graphs};(root/(label+'-graphs.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
        methods={g.get_name() for g in graphs if g.get_name()!='EventGraph' and any(n.get_class().get_name()=='K2Node_FunctionEntry' for n in g.Nodes)}
        for values in data.values():
            for n in values:
                if 'custom_event' in n:methods.add(n['custom_event'])
                if n['cls']=='K2Node_Event' and n.get('event',{}).get('name') not in (None,'None'):methods.add(n['event']['name'])
        signatures={};unemitted=[]
        for method in methods:
            try:signatures[method]=ue.describe_function(bp.GeneratedClass,method)
            except AttributeError:
                nodes=data.get(method,[])
                if len(nodes)!=1 or nodes[0]['cls']!='K2Node_FunctionEntry' or any(p['category']=='exec' and p['links'] for p in nodes[0]['pins']):raise
                unemitted.append(method)
        refs=ue.get_asset_referencers(package.split('.')[0],31)
        blueprint_export=export(bp,root/(label+'-blueprint.t3d'))
        asset=dict(blueprint_export=blueprint_export,package=package,relative=relative,asset_sha256=digest,parent=path(bp.ParentClass),abstract_blueprint=bool(bp.bGenerateAbstractClass),graphs=data,signatures=signatures,unemitted_empty_function_graphs=unemitted,registry_referencers=sorted(str(x) for x in refs),
            cdo=export(bp.GeneratedClass.get_cdo(),root/(label+'-cdo.t3d')),component_templates=templates(bp,root,label),graph_hashes={g.get_name():semantics(g,{n.get_name() for n in g.Nodes},set()) for g in graphs})
        if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError('read-only volume audit changed bytes')
        from generate_hero_burst_cue_assets import timeline_exports
        asset['timeline_exports']=timeline_exports(bp,root,'volume-original')
        if bp.ParentClass.is_child_of(ue.find_class('UserWidget')):
            asset['widget_tree']=export(bp.get_property('WidgetTree'),root/(label+'-widget-tree.t3d'))
            asset['widget_animations']=[export(anim,root/(label+'-animation-'+str(i)+'.t3d')) for i,anim in enumerate(bp.get_property('Animations'))]
        hierarchy=[];cls=bp.GeneratedClass
        while cls is not None:
            name=cls.get_path_name();hierarchy.append(name)
            if name=='/Script/CoreUObject.Object':break
            cls=cls.get_super_class()
        asset['class_hierarchy']=hierarchy
        try:asset['inherited_python_mixin_defaults']=dict(asset=path(bp.GeneratedClass.get_cdo().get_property('PythonMixinSet')),profile=str(bp.GeneratedClass.get_cdo().get_property('PythonMixinProfile')))
        except Exception:asset['inherited_python_mixin_defaults']=None
        assets[label]=asset
    macros=ue.load_object(Blueprint,'/Engine/EditorBlueprintResources/StandardMacros.StandardMacros')
    cosmetic={g.get_name():rows(g) for g in ue.blueprint_get_all_graphs(macros) if g.get_name()=='Can Execute Cosmetic Events'}
    if not cosmetic:raise RuntimeError('original cosmetic macro required')
    (root/'native-cosmetic-macro.json').write_text(json.dumps(cosmetic,indent=2),encoding='utf-8')
    return dict(status='passed',read_only=True,assets_saved=False,cpp_compile_executed=False,native_cosmetic_macro=cosmetic,assets=assets)


try:report=audit()
except Exception:report=dict(status='failed',error=traceback.format_exc());ue.log_error(report['error'])
Path(arg('UEPExplorerCharacterAuditResult')).write_text(json.dumps(report,indent=2),encoding='utf-8')
if report['status']!='passed':raise RuntimeError(report['error'])
ue.log('UEP_EXPLORER_CHARACTER_AUDIT_PASSED')
