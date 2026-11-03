"""Accept fresh-source reproduction and actual current packaged execution."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence,require
from check_hardening_log import validate as hardening_log
from inspect_migration_container import inspect as inspect_container
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.hardening_validation_contract import validate as hardening_contract
from uep_lyra_native.world_validation_contract import validate as frontend_contract
from uep_lyra_native.rule_network_contract import validate as network_contract


def closed(directory,scope=None):
    value=load(directory/'summary.json')
    require(value['status']=='passed' and value.get('error') is None,'delivery run is not closed and passed: '+str(directory))
    if scope:require(value['scope']==scope,'delivery evidence scope differs')
    if value.get('process'):require(value['process']['exit_code']==0,'delivery process failed')
    return value


def frozen(rows):
    for row in rows:require(sha(Path(row['path']))==row['sha256'],'delivery fingerprint changed: '+row['path'])


def dependencies(path,loaded,package):
    report=load(path)
    require(report['status']=='passed' and report['runtime_home_inside_package'] and loaded['inside_package'] and loaded['actual_loaded_module'] and loaded['source_engine_modules_loaded']==0,'packaged runtime dependency locality not proven')
    require(Path(loaded['path']).is_relative_to(package) and sha(Path(loaded['path']))==loaded['sha256'],'actual loaded packaged CPython changed')
    for row in report['dependency_files']:require(sha(package/row['relative_path'])==row['sha256'],'packaged CPython receipt file changed')
    return dict(receipt_python_files=report['receipt_python_files'],actual_loaded_python=loaded,actual_python_home=report['actual_python_home'],evidence=evidence(path))


def collect(root,group,output):
    root,output=root.resolve(),output.resolve()
    require(root.is_relative_to(REPO/'.build') and output.is_relative_to(REPO/'Demos') and not output.exists(),'owned closed evidence and fresh delivery ledger required')
    common=dict(schema_version=1,status='accepted',group=group,target='UE5.8.1 / CPython3.11 / Win64 Development',
        physical_input_tested=False,cpp09_actual_desktop_input_user_deferred=True,engine_full_compile_executed=False,
        other_platforms_or_shipping_build_claimed=False,rendered_graphics_audio_or_hardware_input_claimed=False)
    if group=='H03':
        directory=root/'H03-Reproduce05';result=closed(directory,'fresh-current-native-migration-reproduction')
        require(result['cpp_compile_executed'] and result['runtime_acceptance'] and not result['old_stage_or_compiler_outputs_reused'],'fresh native reproduction proof missing')
        frozen(result['hashes']+result['engine_inputs']+result['products'])
        from prepare_native_reproduction import verify
        preparation=verify(result['preparation'])
        runtime=directory/'ActualExceptions';closed(runtime);actual=hardening_contract(load(runtime/'runtime.json'))
        hardening_log((runtime/'runtime.log').read_text(encoding='utf-8-sig'),13)
        build=next(Path(row['path']) for row in result['engine_inputs'] if row['path'].replace('\\','/').endswith('/Build.version'))
        version=load(build);require((version['MajorVersion'],version['MinorVersion'],version['PatchVersion'])==(5,8,1),'actual reproduction Engine is not 5.8.1')
        modules=load(directory/'editor-modules.json');require(modules['status']=='passed' and modules['engine_manifest_unchanged'] and modules['project_modules']==23,'fresh project module manifest assembly missing')
        actions=load(directory/'ProjectPlan/actions.json')['Actions'];stage=Path(load(Path(result['preparation']))['stage'])
        for action in actions:
            for path in action.get('ProducedItems',[])+action.get('DeleteItems',[]):require(Path(path).resolve().is_relative_to(stage),'reviewed project action writes outside the stage')
        ledger=dict(common,fresh_preparation=preparation,actual_engine_version={k:version[k] for k in ('MajorVersion','MinorVersion','PatchVersion')},
            actual_native_failure_recovery=actual,current_editor_products=len(result['products']),all_frozen_source_and_engine_inputs_verified=True,
            production_recipes_composed_from_versioned_sources=True,old_stage_or_compiler_outputs_reused=False,cook_package_executed=False,
            project_module_count=modules['project_modules'],reviewed_project_actions=len(actions),all_project_action_outputs_inside_stage=True,
            production_test_plugins_disabled=['RuntimeTests','ShooterTests'],
            retained_attempts=['H03-Reproduce01/02: the NoEngineChanges guard refused a full-target refresh of existing Engine modules/metadata before project compilation. Selecting all project modules scopes every action to the stage.','H03-Reproduce03: content-only plugin descriptors omitted Modules; the entry point now skips those descriptors.','H03-Reproduce04 compiled all 24 initial project modules. Startup exposed the original RuntimeTests/ShooterTests settings enabling an unavailable Engine test plugin. The owned descriptor now matches the prior production configuration, disabling only those test plugins. The plugin graph change regenerated shared headers, so UBT rebuilt the affected project modules in H03-Reproduce05; no Engine build or source change was allowed.'],
            evidence=[evidence(Path(result['preparation'])),evidence(directory/'summary.json'),evidence(directory/'editor-modules.json'),evidence(directory/'ProjectPlan/actions.json'),evidence(runtime/'summary.json'),evidence(runtime/'runtime.json')])
    else:
        require(group=='H04','supported delivery group required')
        # A cold unique Game target compiles its Engine runtime dependencies
        # into this project. That is distinct from rebuilding the Engine
        # distribution, Editor, tools, or changing the installed binaries.
        common.pop('engine_full_compile_executed')
        build_dir=root/'H04-GameBuild01';build=closed(build_dir,'current-Development-LyraGame-build-only')
        require(build['cpp_compile_executed'] and build['no_engine_changes_requested'],'current protected Game build missing')
        frozen(build['products']+build['engine_inputs'])
        cook_dir=root/'H04-Cook01';cook=closed(cook_dir,'current-original-migration-content-cook-package')
        require(cook['cook_package_executed'],'actual cook/package process missing');frozen(cook['products'])
        plan_path=root/'H04-package-plan.json';plan=load(plan_path)
        with (cook_dir/'containers.csv').open(encoding='utf-8-sig',newline='') as source:inventory=inspect_container(plan,source)
        require(inventory['status']=='passed' and inventory['coverage']['candidate_assets']['present']==246 and inventory['coverage']['validation_fixture_assets']['present']==3,'complete original/native cooked content missing')
        game=Path(cook['packaged_executable']);require(sha(game)==next(row['sha256'] for row in build['products'] if Path(row['path']).name=='LyraGame.exe'),'package executable is not the current Game build')
        standalone={};python_dependencies={};package=game.parents[3]
        for mode in ('Exceptions','Frontend'):
            directory=root/('H04-Packaged'+mode+'01');run=closed(directory,'actual-current-packaged-native-runtime')
            require(run['packaged_runtime'] and Path(run['process']['executable'])==game,'standalone execution did not use the actual packaged Game')
            report=load(directory/'runtime.json')
            standalone[mode]=(hardening_contract if mode=='Exceptions' else frontend_contract)(report)
            python_dependencies[mode]=dependencies(directory/'dependencies.json',run['loaded_python'],package)
            if mode=='Exceptions':hardening_log((directory/'runtime.log').read_text(encoding='utf-8-sig'),13)
        networks={}
        for family in ('Damage','Pawn'):
            directory=root/('H04-Packaged'+family+'Network01');run=closed(directory)
            require(run['packaged_runtime'] and run['actual_native_rule_network'],'packaged authority/client network missing')
            lane=run['lanes']['rule'];require(lane['status']=='passed' and set(lane['processes'])=={'server','A','B0'},'three real network processes missing')
            for process in lane['processes'].values():require(process['exit_code']==0 and Path(process['executable'])==game,'network peer did not cleanly run the package executable')
            reports={peer:load(directory/'rule'/(peer+'.json')) for peer in ('server','A','B0')}
            networks[family]=network_contract(reports,family)
            for peer in reports:python_dependencies[family+'-'+peer]=dependencies(directory/'rule'/(peer+'-dependencies.json'),lane['loaded_python'][peer],package)
        names=['H04-GameBuild01/summary.json','H04-Fixtures01/summary.json','H04-Cook01/summary.json','H04-Cook01/package-inventory.json','H04-package-plan.json']
        names += ['H04-Packaged'+mode+'01/summary.json' for mode in ('Exceptions','Frontend')]
        names += ['H04-Packaged'+family+'Network01/summary.json' for family in ('Damage','Pawn')]
        ledger=dict(common,cook_package_executed=True,game_target_runtime_dependencies_compiled=True,
            engine_distribution_rebuild_executed=False,protected_engine_distribution_files_unchanged=True,
            actual_packaged_executable=evidence(game),package_inventory=inventory,
            standalone=standalone,networks=networks,python_dependencies=python_dependencies,all_network_peers_use_actual_packaged_game=True,
            independent_client_rule_views=sum(value['independent_client_views'] for value in networks.values()),
            original_candidate_logic_coverage_not_inferred_from_content_presence=True,
            evidence=[evidence(root/name) for name in names])
    output.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='accepted',group=group,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--group',choices=('H03','H04'),required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(collect(a.root,a.group,a.output)))
