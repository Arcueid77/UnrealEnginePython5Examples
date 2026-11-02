"""Read CPP-016..018 definitions without authoring assets or accepting migration."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

sys.dont_write_bytecode=True


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def object_path(obj):return obj.get_path_name() if obj is not None else None


def inspect(stage,output):
    from stage_safety import require_authoring_stage
    require_authoring_stage(str(stage),ue.convert_relative_path_to_full(ue.get_content_dir()))
    ue.wait_for_assets()
    query=ue.FARFilter();query.class_names=['Blueprint'];query.recursive_classes=True
    query.package_paths=['/Game','/ShooterCore','/TopDownArena','/ShooterExplorer','/ShooterMaps'];query.recursive_paths=True
    entries=ue.get_assets_by_filter(query,return_asset_data=True)
    selected=[];missing=[]
    for entry in entries:
        tags=entry.tags_and_values;native=tags.get('NativeParentClassPath',tags.get('NativeParentClass',''))
        if not native:missing.append(entry.object_path)
        if 'LyraInventoryItemDefinition' in native or 'LyraGameplayAbility' in native:
            selected.append((entry,native))
    item_base=ue.find_class('LyraInventoryItemDefinition');ability_base=ue.find_class('LyraGameplayAbility')
    stats_base=ue.find_class('InventoryFragment_SetStats');item_cost=ue.find_class('LyraAbilityCost_ItemTagStack');player_cost=ue.find_class('LyraAbilityCost_PlayerTagStack')
    report=dict(schema_version=1,status='passed',candidates=['CPP-016','CPP-017','CPP-018'],scope='asset definitions and binding reads only',runtime_acceptance=False,implementation_started=False,assets_saved=False,cpp_compile_executed=False,
        registry_blueprints=len(entries),missing_native_parent_tags=missing,selected_definitions=len(selected),items=[],abilities=[],target_fragments=[],target_costs=[],source_assets=[],read_failures=[])
    for index,(entry,native) in enumerate(sorted(selected,key=lambda row:row[0].object_path)):
        package=entry.package_name;mount=package.split('/')[1]
        physical=(stage/'Content'/package[len('/Game/'):] if mount=='Game' else stage/'Plugins/GameFeatures'/mount/'Content'/package[len('/'+mount+'/'):]).with_suffix('.uasset')
        reference=Path('F:/LyraStarterGame')/physical.relative_to(stage)
        fingerprint=dict(package=package,path=str(physical),sha256=sha(physical),reference_path=str(reference),reference_exists=reference.is_file())
        if reference.is_file():fingerprint['reference_sha256']=sha(reference)
        report['source_assets'].append(fingerprint)
        bp=entry.get_asset();cls=bp.get_property('GeneratedClass');rooted=cls.is_rooted()
        if not rooted:cls.add_to_root()
        try:
            cdo=cls.get_cdo();definition=dict(asset=entry.object_path,class_path=cls.get_path_name(),native_parent=native,definition_scope='original_lyra_asset' if reference.is_file() else 'stage_fixture')
            exporter=ue.new_object(ue.find_class('ObjectExporterT3D'));export=output/('definition-'+str(index)+'.t3d')
            if not exporter.export_to_file(cdo,str(export)):raise RuntimeError('Definition export failed: '+entry.object_path)
            definition['cdo_export']=dict(path=str(export),sha256=sha(export))
            if cdo.is_a(item_base):
                fragments=list(cdo.get_property('Fragments'));definition['fragment_count']=len(fragments);report['items'].append(definition)
                for slot,fragment in enumerate(fragments):
                    if fragment is None or not fragment.is_a(stats_base):continue
                    row=dict(owner=entry.object_path,slot=slot,object_path=fragment.get_path_name(),class_path=fragment.get_class().get_path_name())
                    try:row['initial_stats']=[dict(tag=str(tag.TagName),count=int(value)) for tag,value in fragment.get_property('InitialItemStats').items()];row['map_read_supported']=True
                    except Exception:row.update(map_read_supported=False,map_read_error=traceback.format_exc());report['read_failures'].append(dict(owner=entry.object_path,operation='InitialItemStats map read',error=row['map_read_error']))
                    report['target_fragments'].append(row)
            elif cdo.is_a(ability_base):
                costs=list(cdo.get_property('AdditionalCosts'));definition['additional_cost_count']=len(costs);report['abilities'].append(definition)
                for slot,cost in enumerate(costs):
                    if cost is None or not (cost.is_a(item_cost) or cost.is_a(player_cost)):continue
                    quantity=cost.get_property('Quantity')
                    row=dict(owner=entry.object_path,slot=slot,object_path=cost.get_path_name(),class_path=cost.get_class().get_path_name(),kind='item' if cost.is_a(item_cost) else 'player',tag=str(cost.get_property('Tag').TagName),quantity_base=float(quantity.Value),quantity_curve_table=object_path(quantity.Curve.CurveTable),quantity_curve_row=str(quantity.Curve.RowName),only_apply_on_hit=bool(cost.get_property('bOnlyApplyCostOnHit')))
                    if cost.is_a(item_cost):row['failure_tag']=str(cost.get_property('FailureTag').TagName)
                    report['target_costs'].append(row)
            else:raise RuntimeError('Native parent metadata differs from actual CDO type: '+entry.object_path)
        finally:
            if not rooted:cls.remove_from_root()
        if sha(physical)!=fingerprint['sha256']:raise RuntimeError('Read-only probe changed an asset')
    report['asset_hashes_unchanged']=all(sha(Path(row['path']))==row['sha256'] for row in report['source_assets'])
    report['counts']=dict(item_definitions=len(report['items']),ability_definitions=len(report['abilities']),original_item_definitions=sum(r['definition_scope']=='original_lyra_asset' for r in report['items']),original_ability_definitions=sum(r['definition_scope']=='original_lyra_asset' for r in report['abilities']),stat_fragments=len(report['target_fragments']),item_tag_costs=sum(c['kind']=='item' for c in report['target_costs']),player_tag_costs=sum(c['kind']=='player' for c in report['target_costs']))
    return report


result=Path(arg('UEPNativeStatsCostPreflightResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('probe_native_stats_cost_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    report=inspect(Path(arg('UEPNativeStatsCostStage')).resolve(),result.parent)
except Exception:report=dict(status='failed',runtime_acceptance=False,assets_saved=False,error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_STATS_COST_PREFLIGHT_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
