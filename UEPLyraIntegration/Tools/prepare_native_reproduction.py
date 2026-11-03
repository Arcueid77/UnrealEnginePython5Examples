"""Build a fresh source/asset stage from versioned migration recipes only."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil

REPO=Path(__file__).resolve().parents[3]
PATCHES=('native_gameplay_patches','native_team_patches','native_bot_patches',
 'native_spawn_patches','native_inventory_patches','native_spawner_patches',
 'native_accolade_patches','native_interaction_patches','native_escape_patches',
 'native_stats_patches','native_cost_patches','native_lifecycle_patches',
 'native_policy_carrier_patches','native_world_policy_patches','native_rule_policy_patches')
SKIP={'Binaries','Intermediate','Saved','DerivedDataCache','.git','.vs','.codegraph','__pycache__'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def pin(p):return dict(path=str(p),sha256=sha(p))
def require(v,m):
    if not v:raise ValueError(m)


def versioned_target(source,stage):
    relative=source.relative_to(REPO)
    for root,destination in (('Demos/UEPLyraIntegration/Overlay',stage),
        ('Demos/UEPLyraIntegration/Plugins/UEPLyraBridge',stage/'Plugins/UEPLyraBridge'),
        ('Demos/UEPLyraIntegration/NativeFixtures',stage/'Source/LyraGame/UEPValidation')):
        if relative.is_relative_to(root):return destination/relative.relative_to(root)
    return stage/'Plugins/UnrealEnginePython'/relative


def production_sources(reference):
    modules=[importlib.import_module(n) for n in PATCHES]
    for module in modules:module.REFERENCE=reference
    rows={};history=[]
    for module in modules:
        values=module.cpp01_sources() if module.__name__=='native_gameplay_patches' else module.sources()
        history.append(dict(recipe=module.__name__,source=pin(Path(module.__file__)),files=len(values)))
        for row in values:
            prior=rows.get(row['relative'])
            if prior is not None:require(row['before']==prior['after'] or row['after']==prior['after'],'Uncomposed overlapping production recipe: '+row['relative'])
            rows[row['relative']]=row
    require(len(rows)==63,'Complete current production source recipe required')
    return rows,history

def prepare(reference,stage,result):
    reference,stage,result=(Path(p).resolve() for p in (reference,stage,result))
    require(stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') and result.is_relative_to(REPO/'.build'),'Owned fresh reproduction stage required')
    require(not stage.exists() and not result.exists() and (reference/'LyraStarterGame.uproject').is_file(),'Original reference and absent stage/report required')
    rows,history=production_sources(reference);stage.mkdir(parents=True);result.parent.mkdir(parents=True,exist_ok=True)
    report=dict(schema_version=1,status='failed',source=str(reference),stage=str(stage),reference_inputs=[],versioned_inputs=[],production_sources=[],recipes=history,copied_files=0,copied_bytes=0,hardlinks_used=False,junctions_used=False,old_stage_or_compiler_outputs_reused=False,runtime_acceptance=False,error=None)
    def copy_tree(source,target,reference_input=False):
        if not source.exists():return
        for directory,dirs,files in os.walk(source,followlinks=False):
            dirs[:]=[d for d in dirs if d not in SKIP]
            for name in dirs+files:require(not (Path(directory)/name).is_symlink() and not ((Path(directory)/name).lstat().st_file_attributes&0x400),'Reparse input requires explicit handling')
            for name in files:
                src=Path(directory)/name
                if src.suffix in ('.pyc','.pyo','.pdb','.obj','.ilk'):continue
                dst=target/src.relative_to(source);dst.parent.mkdir(parents=True,exist_ok=True);before=pin(src);shutil.copy2(src,dst);require(sha(dst)==before['sha256'],'Copied reproduction input differs')
                report['reference_inputs' if reference_input else 'versioned_inputs'].append(before);report['copied_files']+=1;report['copied_bytes']+=dst.stat().st_size
    try:
        for folder in ('Source','Content','Plugins','Config','Build','Platforms'):copy_tree(reference/folder,stage/folder,True)
        project=reference/'LyraStarterGame.uproject';shutil.copy2(project,stage/project.name);report['reference_inputs'].append(pin(project))
        sdk=stage/'Plugins/UnrealEnginePython'
        for folder in ('Source','Content','Config','Resources'):copy_tree(REPO/folder,sdk/folder)
        descriptor=REPO/'UnrealEnginePython.uplugin';shutil.copy2(descriptor,sdk/descriptor.name);report['versioned_inputs'].append(pin(descriptor))
        copy_tree(REPO/'Demos/UEPLyraIntegration/Plugins/UEPLyraBridge',stage/'Plugins/UEPLyraBridge')
        copy_tree(REPO/'Demos/UEPLyraIntegration/Overlay',stage)
        for relative,row in rows.items():
            dst=stage/relative;dst.parent.mkdir(parents=True,exist_ok=True)
            if row['original_sha256'] is not None:require(sha(reference/relative)==row['original_sha256'],'Original source census changed')
            dst.write_text(row['after'],encoding='utf-8',newline='\n');report['production_sources'].append(dict(relative=relative,sha256=sha(dst),original_sha256=row['original_sha256']))
        copy_tree(REPO/'Demos/UEPLyraIntegration/NativeFixtures',stage/'Source/LyraGame/UEPValidation')
        path=stage/project.name;data=json.loads(path.read_text(encoding='utf-8-sig'));plugins=data['Plugins']
        for name,enabled in (('UnrealEnginePython',True),('UEPLyraBridge',True),('AndroidFileServer',False),('RuntimeTests',False),('ShooterTests',False)):
            entry=next((v for v in plugins if v['Name']==name),None)
            if entry is None:plugins.append(dict(Name=name,Enabled=enabled))
            else:entry['Enabled']=enabled
        path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
        game=stage/'Config/DefaultGame.ini';game.write_text(game.read_text(encoding='utf-8-sig')+'\n; UEP isolated reproduction packaging payload.\n[/Script/UnrealEd.ProjectPackagingSettings]\n+DirectoriesToAlwaysStageAsNonUFS=(Path="Scripts")\n',encoding='utf-8',newline='\n')
        marker=dict(schema_version=1,purpose='approved-native-gameplay-migration',source=str(project),independent_file_copies=True,reproduced_from_versioned_recipes=True)
        (stage/'.uep-lyra-full-stage.json').write_text(json.dumps(marker,indent=2)+'\n',encoding='utf-8',newline='\n')
        for row in report['reference_inputs']+report['versioned_inputs']:require(sha(Path(row['path']))==row['sha256'],'Source changed during reproduction prepare')
        report.update(status='prepared_requires_fresh_build',stage_project=str(path),generated_inputs=[pin(path),pin(game)],production_source_count=len(rows))
    except Exception as error:report['error']=str(error);raise
    finally:result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    return {k:report[k] for k in ('status','copied_files','copied_bytes','production_source_count','old_stage_or_compiler_outputs_reused')}

def verify(report):
    report=Path(report).resolve();data=json.loads(report.read_text(encoding='utf-8-sig'));stage=Path(data['stage'])
    require(report.is_relative_to(REPO/'.build') and stage.is_relative_to(REPO/'.build'),'Owned prepared report and stage required')
    require(data['status']=='prepared_requires_fresh_build' and not data['old_stage_or_compiler_outputs_reused'],'Fresh preparation proof required')
    for row in data['reference_inputs']+data['versioned_inputs']+data['generated_inputs']:
        require(sha(Path(row['path']))==row['sha256'],'Prepared source/config input changed: '+row['path'])
    for recipe in data['recipes']:require(sha(Path(recipe['source']['path']))==recipe['source']['sha256'],'Versioned production recipe changed')
    rows,_=production_sources(Path(data['source']))
    require(set(rows)=={v['relative'] for v in data['production_sources']},'Production recipe file set differs')
    for row in data['production_sources']:
        expected=hashlib.sha256(rows[row['relative']]['after'].encode('utf-8')).hexdigest().upper()
        require(sha(stage/row['relative'])==row['sha256']==expected,'Prepared/current production source differs: '+row['relative'])
    # Recreate the ordered copy/overlay/patch composition, including unchanged
    # original content. A staged edit must not become its own trusted baseline.
    staged={stage/Path(row['path']).relative_to(data['source']):row['sha256'] for row in data['reference_inputs']}
    staged.update({versioned_target(Path(row['path']),stage):row['sha256'] for row in data['versioned_inputs']})
    staged.update({stage/row['relative']:row['sha256'] for row in data['production_sources']})
    staged.update({Path(row['path']):row['sha256'] for row in data['generated_inputs']})
    for path,expected in staged.items():require(sha(path)==expected,'Staged copy differs from its composed source: '+str(path))
    return dict(status='passed',production_sources=len(rows),reference_inputs=len(data['reference_inputs']),versioned_inputs=len(data['versioned_inputs']),verified_staged_files=len(staged),old_stage_or_compiler_outputs_reused=False)


def refresh_unbuilt(report,result):
    """Refresh reviewed source bytes before the first build; retain its parent proof."""
    report,result=Path(report).resolve(),Path(result).resolve()
    data=json.loads(report.read_text(encoding='utf-8-sig'));stage=Path(data['stage'])
    require(report.is_relative_to(REPO/'.build') and result.is_relative_to(REPO/'.build') and not result.exists(),'Owned parent and fresh report required')
    require(data['status']=='prepared_requires_fresh_build' and not data['old_stage_or_compiler_outputs_reused'],'Unbuilt independent preparation required')
    require(not any(p.is_dir() and p.name in ('Binaries','Intermediate') for p in stage.rglob('*')),'Source refresh is forbidden after compiler outputs exist')
    for row in data['reference_inputs']+data['generated_inputs']:
        require(sha(Path(row['path']))==row['sha256'],'Reference/generated preparation input changed')
    for row in data['production_sources']:require(sha(stage/row['relative'])==row['sha256'],'Prepared production source changed')
    for recipe in data['recipes']:require(sha(Path(recipe['source']['path']))==recipe['source']['sha256'],'Production recipe changed')
    changes=[]
    for row in data['versioned_inputs']:
        source=Path(row['path']);target=versioned_target(source,stage)
        require(target.is_file() and sha(target)==row['sha256'],'Unbuilt staged source was independently edited: '+str(target))
        current=sha(source)
        if current!=row['sha256']:
            changes.append(dict(source=str(source),stage=str(target),before=row['sha256'],after=current));shutil.copy2(source,target)
        row['sha256']=current
    data['parent_preparation']=pin(report);data['unbuilt_source_refresh']=changes
    result.parent.mkdir(parents=True,exist_ok=True);result.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    answer=verify(result);answer['refreshed_unbuilt_source_files']=len(changes);return answer


def configure_production(report,result):
    """Derive only the production test-plugin configuration; preserve compiled code."""
    report,result=Path(report).resolve(),Path(result).resolve();verify(report)
    require(result.is_relative_to(REPO/'.build') and not result.exists(),'fresh owned configuration report required')
    data=json.loads(report.read_text(encoding='utf-8-sig'));project=Path(data['stage'])/'LyraStarterGame.uproject'
    result.parent.mkdir(parents=True,exist_ok=True);previous=result.parent/'previous-project.json';shutil.copy2(project,previous)
    before=sha(project);descriptor=json.loads(project.read_text(encoding='utf-8-sig'))
    for name in ('RuntimeTests','ShooterTests'):
        entry=next((row for row in descriptor['Plugins'] if row['Name']==name),None)
        require(entry is not None and entry['Enabled'] is True,'expected reference test plugin must be explicitly enabled')
        entry['Enabled']=False
    project.write_text(json.dumps(descriptor,indent=2)+'\n',encoding='utf-8',newline='\n')
    data['configuration_only_parent']=pin(report)
    data['production_test_plugin_update']=dict(project=str(project),before_sha256=before,after_sha256=sha(project),disabled=['RuntimeTests','ShooterTests'],previous_project=pin(previous),cpp_sources_changed=False)
    for row in data['generated_inputs']:
        if Path(row['path'])==project:row['sha256']=sha(project)
    result.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    return verify(result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reference',default='F:/LyraStarterGame');p.add_argument('--stage');p.add_argument('--result');p.add_argument('--verify-report');p.add_argument('--refresh-unbuilt');p.add_argument('--configure-production');a=p.parse_args()
    if a.verify_report:result=verify(a.verify_report)
    elif a.refresh_unbuilt:
        if not a.result:p.error('--result required for unbuilt source refresh')
        result=refresh_unbuilt(a.refresh_unbuilt,a.result)
    elif a.configure_production:
        if not a.result:p.error('--result required for production test-plugin configuration')
        result=configure_production(a.configure_production,a.result)
    else:
        if not a.stage or not a.result:p.error('--stage and --result required for preparation')
        result=prepare(a.reference,a.stage,a.result)
    print(json.dumps(result))
