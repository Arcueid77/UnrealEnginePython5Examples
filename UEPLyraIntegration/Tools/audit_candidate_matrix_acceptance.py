"""Aggregate the original 0.9 candidate cells without extending later version gates."""
from pathlib import Path

from audit_batch1a_acceptance import inspect as inspect_batch1a
from audit_playable_startup_acceptance import inspect as inspect_startup
from audit_reload_cleanup_acceptance import SDK, require
from audit_ui_navigation_acceptance import read, sha
from audit_weapon_example_acceptance import inspect as inspect_weapon

REQUIREMENT = ('Generic, both Third Person variants and Lyra pass the candidate regression matrix; '
               'the missing Mixin Third Person visible gate is closed.')
BASE='.build/LyraValidation/BlueprintPython/'


def matrix_gate(components):
    require(set(components)=={'generic','third_person','lyra'},'All original candidate families required')
    generic=components['generic']
    require(generic['clean_suites']==6 and generic['clean_checks']==70 and generic['packaged_checks']==21 and
            generic['current_call_cases']==11 and generic['same_editor_pie_sessions']==3,'Original Generic candidate cell incomplete')
    third=components['third_person']
    require([r['variant'] for r in third]==['Mixin','PythonFirst'],'Both original Third Person variants required')
    for row in third:
        require(row['current_editor_sdk']==SDK and row['rendered_editor_images']==3 and row['editor_exit_code']==0 and
                row['actual_packaged_game'] is True and row['game_exit_code']==0 and row['behavior_and_cleanup_passed'] is True,
                'Third Person Editor/visible/actual Game cell incomplete')
    lyra=components['lyra']
    require(lyra['normal_no_probe_observation_seconds']==20 and lyra['normal_stop_is_owned_and_intentional'] is True and
            lyra['current_network_phases']==19 and lyra['native_clients']==2 and lyra['travel_and_rejoin'] is True and
            lyra['direct_component_visual_pairs']==5 and lyra['actual_packaged_weapon_scenarios']==42,
            'Original Lyra0.9 startup/presentation/lifetime/native-owner/package cell incomplete')


def inspect(repo,current,initial):
    repo=Path(repo);migration=repo/'Demos/UEPLyraIntegration/Migration'
    require(len(current['assets'])==246 and [(r['path'],r['version']) for r in current['assets']]==
            [(r['path'],r['version']) for r in initial['assets']], 'Original candidate inventory changed')
    ledgers={}
    for number in (266,267,268,270,271,272):
        path,=(migration/'Acceptance').glob(str(number)+'-*.json')
        ledgers[number]=(path,read(path))
    generic=ledgers[268][1]['native_review'];clean=generic['clean_candidate'];folder=repo/clean['directory']
    require(generic['complete_six_suite_core_gate'] and sha(folder/'summary.json')==clean['summary_sha256'],
            'Pinned clean Generic candidate changed')
    clean_summary=read(folder/'summary.json');require(clean_summary['status']=='passed' and clean_summary['actual_checks']==70,
            'Generic clean core gate incomplete')
    require([r['checks'] for r in clean['suites']]==[21,21,1,1,5,21],'Original six-suite cases changed')
    for row in clean['suites']:
        parent=folder if row['name']=='packaged' else folder/'Editor'
        require(sha(parent/(row['name']+'.json'))==row['report_sha256'] and sha(parent/(row['name']+'.log'))==row['log_sha256'],
                'Generic actual native report/log changed')
        require(row['exit_code']==int(row['name'].startswith('exception-')), 'Expected/ordinary exit boundary differs')
    calls=ledgers[266][1]['review']
    require(calls['current_generic_call_cases']==11 and calls['current_pie_run']['same_editor_sessions']==3,
            'Current call/PIE boundary reference absent')
    tp_folder=repo/(BASE+'20261027-candidate-regressions/ThirdPerson01')
    tp=read(tp_folder/'summary.json');tp_review=ledgers[267][1]['native_review'] if 'native_review' in ledgers[267][1] else read(tp_folder.parent/'native-review.json')
    require(tp['status']=='passed' and sha(tp_folder/'summary.json')==tp_review['third_person_summary_sha256'],
            'Pinned rendered Third Person capture changed')
    package=ledgers[272][1]['review'];require(package['status']=='passed' and package['native_target_compiled_once_for_both_variants'],
            'Current actual Third Person package review absent')
    source_archive=read(repo/(BASE+'20261028-third-person-package/original-demo-runner-archive.json'))
    require(sha(source_archive['archive'])==source_archive['sha256'], 'Original rendered-run control archive changed')
    source_rows=tp['native_source_hashes']
    for row in source_rows:require(sha(row['path'])==row['sha256'].upper(),'Current native source differs from rendered Third Person capture')
    third=[]
    for variant in ('Mixin','PythonFirst'):
        native,=[r for r in tp['variants'] if r['variant']==variant]
        pinned,=[r for r in tp_review['third_person_variants'] if r['variant']==variant]
        packed,=[r for r in package['variants'] if r['variant']==variant]
        require(native['status']=='passed' and native['process']['exit_code']==packed['exit_code']==0,'Third Person native process failed')
        for row in native['binary_hashes']+native['script_hashes']:
            require(sha(row['path'])==row['sha256'].upper(),'Exact rendered-run binary/script snapshot changed')
        sdk={r['sha256'].upper() for r in native['binary_hashes'] if Path(r['path']).name=='UnrealEditor-UnrealEnginePython.dll'}
        require(sdk=={SDK},'Rendered Third Person used a different SDK')
        require(sha(native['smoke'])==pinned['smoke_sha256'] and sha(native['visible'])==pinned['visible_sha256'], 'Third Person state/visual report changed')
        visible=read(native['visible']);require(visible['status']=='passed' and visible['rendered'] and len(visible['frames'])==3 and not visible['errors'],
            'Missing actual movement/look/jump visible frames')
        for frame in visible['frames']:
            image=frame.get('image',frame.get('path'))
            if isinstance(image,dict):require(sha(image['path'])==image['sha256'].upper(),'Visible native image changed')
            elif image is not None:
                expected=frame.get('sha256');require(expected and sha(image)==expected.upper(),'Visible native image changed')
            else:raise ValueError('Visible frame has no actual image reference')
        packed_folder=repo/packed['directory']
        require(sha(packed_folder/'summary.json')==packed['summary_sha256'] and sha(packed_folder/'smoke.json')==packed['report_sha256'] and
                sha(packed_folder/'smoke.log')==packed['log_sha256'],'Packaged Third Person actual output changed')
        game=read(packed_folder/'summary.json');require(sha(game['process']['executable'])==packed['executable_sha256'], 'Packaged executable changed')
        third.append(dict(variant=variant,current_editor_sdk=SDK,rendered_editor_images=3,editor_exit_code=0,
            actual_packaged_game=True,game_exit_code=0,behavior_and_cleanup_passed=True,
            editor_pid=native['process']['pid'],game_pid=packed['pid'],packaged_executable_sha256=packed['executable_sha256']))
    archive_path=repo/(BASE+'20261028-candidate-matrix/startup-retired-test-inputs.json')
    archives=read(archive_path)
    startup=inspect_startup(repo,retired_probe_archives={r['native_input_path']:r['archive'] for r in archives['inputs']})
    weapon=inspect_weapon(repo,current,initial);batch=inspect_batch1a(repo,current,initial)
    components=dict(generic=dict(clean_suites=6,clean_checks=70,packaged_checks=21,current_call_cases=11,same_editor_pie_sessions=3),
        third_person=third,lyra=dict(normal_no_probe_observation_seconds=20,normal_stop_is_owned_and_intentional=startup['normal_process_exit_is_intentional_driver_stop'],
            current_network_phases=batch['native_protocol']['phase_count'],native_clients=2,
            travel_and_rejoin=batch['native_protocol']['rejoin_tested'],direct_component_visual_pairs=batch['visual_checkpoint_pairs'],
            actual_packaged_weapon_scenarios=weapon['weapon_scenarios_per_runtime']))
    matrix_gate(components)
    return dict(status='passed',criterion=REQUIREMENT,completion_proven=True,platform='Win64',configuration='Development',
        scope='Original0.9 Generic/Third Person/Lyra candidate cells',components=components,
        pinned_ledgers=[dict(batch=n,path=p.relative_to(repo).as_posix(),sha256=sha(p)) for n,(p,_) in sorted(ledgers.items())],
        startup_source_and_output_rechecked=True,current_weapon_and_batch1a_sources_rechecked=True,
        retired_unselected_startup_test_inputs=startup['retired_unselected_probe_archives'],
        retired_startup_test_input_recovery=dict(path=archive_path.relative_to(repo).as_posix(),sha256=sha(archive_path)),
        original_rendered_run_control_archive=source_archive,cpp_compile_executed=False,cook_package_executed=False,
        new_native_processes=0,full_migration_regression_executed=False,full_migration_acceptance_proven=False,
        limits=['Aggregate already verified native cells;do not call this a fresh all-family runtime run.',
                'Generic retains its one clean six-suite70 run. Third Person visible proof remains rendered Editor;actual packages retain NullRHI native input/gameplay/lifetime scope.',
                'Lyra0.9 covers normal no-probe startup,actual two-owner weapons,controlled reload/travel and visible/packaged presenters. Full Explorer/TopDownArena belongs to the separate original0.14 criterion.',
                'Intentional owner-stop normal startup and declared exception exits retain their exact boundaries. No hardware,pixel/audio parity,other platform/configuration,RC tag or publication claim.'])


def verify_documentation(document,current,initial,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original candidate requirement required')
    expected=inspect(repo,current,initial);require(document.get('review')==expected,'Recorded candidate matrix differs')
    return {k:expected[k] for k in ('status','criterion','platform','configuration','scope','new_native_processes')}
