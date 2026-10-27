"""Original Explorer/Arena component and current Experience acceptance evidence."""
import importlib
from pathlib import Path
import re
import sys

from audit_ability_identity_acceptance import execute_gate,report_dependency_guard
from audit_effects_match_acceptance import closure,verify_source
from audit_reload_cleanup_acceptance import SDK,require,log_gate as scoped_log_gate
from audit_static_scope_dispositions import relative_asset
from audit_ui_failure_cancellation_acceptance import log_gate,process_gate,source_guard
from audit_ui_navigation_acceptance import index_hashes,key,read,sha

REQUIREMENT='Both Experiences pass original-BP/Python gameplay, presentation and applicable multi-client/local-player comparisons.'
BASE='.build/LyraValidation/BlueprintPython/20261028-experience-acceptance'
PROFILES=('BlueprintFallback','Python')
SCENARIOS=('ExplorerExperience','ExplorerGameplay','ExplorerFollow','ExplorerActionsNetwork','ArenaLocalInput','ArenaOpponentBomb')
COMPONENTS=(
 (113,('Differential04NativeGuard',),'uep_lyra_hud.cue_widget_mixin'),
 (167,('Runtime06Fallback','Runtime07Python'),'uep_lyra_world.explorer_state_mixin'),
 (168,('Helpers07Fallback','Helpers08Python'),'uep_lyra_characters.explorer_helpers_mixin'),
 (169,('Style02Fallback','Style03Python'),'uep_lyra_characters.explorer_style_mixin'),
 (170,('Callbacks05Fallback','Callbacks06Python'),'uep_lyra_characters.explorer_callbacks_mixin'),
 (171,('Init06Fallback','Init07Python'),'uep_lyra_characters.explorer_init_mixin'),
 (172,('Begin01Fallback','Begin02Python'),'uep_lyra_characters.explorer_beginplay_mixin'),
 (173,('Input02Fallback','Input04Python'),'uep_lyra_characters.explorer_input_mixin'),
 (174,('Behavior02Fallback','Behavior03Python'),'uep_lyra_characters.explorer_behavior_mixin'),
 (175,('Screens01',),'uep_lyra_hud.explorer_screens_mixin'),
 (176,('Grid02',),'uep_lyra_hud.explorer_grid_mixin'),
 (177,('Toast04',),'uep_lyra_hud.explorer_toast_mixin'),
 (178,('List01',),'uep_lyra_hud.explorer_item_list_mixin'),
 (179,('Interact01',),'uep_lyra_abilities.explorer_interact_mixin'),
 (180,('Actions02',),'uep_lyra_abilities.explorer_actions_mixin'),
 (181,('Cue03',),'uep_lyra_weapons.collect_cue_mixin'),
 (182,('Marker02',),'uep_lyra_abilities.explorer_marker_mixin'),
 (183,('Runtime01',),'uep_lyra_characters.explorer_shells_validation'),
 *[(n,('Python02','Fallback01') if n==194 else ('Python01','Fallback01'),module) for n,module in (
 (189,'uep_lyra_hud.arena_ready_mixin'),(190,'uep_lyra_hud.arena_player_ui_mixin'),
 (191,'uep_lyra_hud.arena_player_tile_mixin'),(192,'uep_lyra_hud.arena_powerup_stat_mixin'),
 (193,'uep_lyra_hud.arena_hud_mixin'),(194,'uep_lyra_world.arena_phases_mixin'),
 (195,'uep_lyra_world.arena_mode_mixin'),(196,'uep_lyra_world.arena_actor_mixin'),
 (197,'uep_lyra_world.arena_level_mixin'),(198,'uep_lyra_world.arena_bomb_visual_mixin'),
 (199,'uep_lyra_world.arena_bomb_base_mixin'),(200,'uep_lyra_abilities.arena_drop_bomb_mixin'))])


def component_review(repo):
    repo=Path(repo);migration=repo/'Demos/UEPLyraIntegration/Migration';scripts=migration.parent/'Overlay/Content/Scripts'
    sys.path.insert(0,str(scripts));rows=[]
    for number,names,module in COMPONENTS:
        ledger_path,=(migration/'Acceptance').glob(str(number)+'-*.json');ledger=read(ledger_path)
        for name in names:
            record,=[r for r in ledger['runs'] if Path(r['directory']).name==name]
            folder=repo/record['directory'];summary_path=folder/'summary.json';summary=read(summary_path)
            require(sha(summary_path)==record['summary_sha256'].upper(),'Pinned component summary changed')
            process_gate(summary)
            for report in record['report_hashes']:require(sha(folder/report['file'])==report['sha256'].upper(),'Pinned actual component report changed')
            if number==183:
                source=scripts/'uep_lyra_characters/explorer_shells_validation.py'
                guards=[dict(module=module,scope='Retained original shell/prompt observation;no inherited-parent migration claim',
                    **source_guard(source,summary['hashes']))]
            else:guards=verify_source(repo,summary,[module],{})
            arguments=summary['external_gate']['arguments'];target=arguments[arguments.index('-m')+1]
            require(target.endswith('_contract') and set(a for a in arguments if a.startswith('--'))<={'--report','--log'},
                    'Only recorded read-only component report contracts may execute')
            current_gate=execute_gate(arguments)
            index=index_hashes(summary['hashes'])
            dependencies=[report_dependency_guard(n,p,index.get(key(p),[])) for n,p in sorted(closure(scripts,[target]).items())]
            logfile,=[a.split('=',1)[1] for a in summary['process']['arguments'] if a.lower().startswith('-abslog=')]
            text=Path(logfile).read_text(encoding='utf-8-sig');markers=set(re.findall(r'(UEP_[A-Z0-9_]+)_DIFFERENTIAL_PASSED',text))
            require(len(markers)==1,'One native component differential completion marker required')
            try:
                marker=markers.pop()
                if number==195:scoped_log_gate(text,marker+'_DIFFERENTIAL_PASSED','UEP_ARENA_MODE_SHUTDOWN_PASSED')
                else:log_gate(text,marker)
            except ValueError as error:raise ValueError(str(number)+'/'+name+': '+str(error)) from error
            rows.append(dict(batch=number,name=name,directory=folder.relative_to(repo).as_posix(),
                ledger_sha256=sha(ledger_path),summary_sha256=sha(summary_path),reports=record['report_hashes'],
                pid=summary['process']['pid'],exit_code=0,log_sha256=sha(logfile),source_guards=guards,
                report_contract_dependencies=dependencies,current_post_exit_semantic_gate=current_gate,
                sdk_scope='Original component capture retains its recorded SDK;current Experience integration is checked separately'))
    require(len(rows)==50,'All forty-nine original component records plus the shared GetReady Cue parent required')
    return rows


def integration_gate(cells):
    require([r['scenario'] for r in cells]==list(SCENARIOS),'All six original Experience integration comparisons required')
    for cell in cells:
        require(cell['profiles']==list(PROFILES) and cell['pair_semantics_passed'] is True and cell['current_editor_sdk']==SDK,
                'Both original/Python profiles and current SDK required')
        require(cell['native_processes']==(6 if cell['scenario']=='ExplorerActionsNetwork' else 2) and
                cell['all_native_exits_zero'] is True,'Actual completed native peers required')
    require(next(r for r in cells if r['scenario']=='ExplorerActionsNetwork')['distinct_clients']==2,
            'Explorer must compare two distinct actual clients')
    for scenario in ('ArenaLocalInput','ArenaOpponentBomb'):
        require(next(r for r in cells if r['scenario']==scenario)['local_players']==2,'Arena requires two native local players')


def frozen_input(row,repo,archives,digest=sha):
    path=Path(row['path']).resolve();expected=row['sha256'].upper()
    if digest(path)==expected:return None
    scripts=Path(repo)/'Demos/UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_abilities'
    stage=Path(repo)/'.build/LyraValidation/Full/Stage/Lyra/Content/Scripts/uep_lyra_abilities'
    allowed={str((base/name).resolve()) for base in (scripts,stage) for name in
        ('explorer_actions_network_validation.py','explorer_actions_network_contract.py')}
    allowed.add(str((Path(repo)/'Validation/Run-UEP58CurrentExperienceValidation.ps1').resolve()))
    archive=archives.get((str(path),expected))
    require(str(path) in allowed and archive is not None,'Current production/native frozen input changed: '+str(path))
    archive=Path(archive).resolve()
    require(archive.is_relative_to(Path(repo)/'.build') and digest(archive)==expected,'Exact old test/control bytes required')
    return dict(native_input_path=str(path),recorded_sha256=expected,current_sha256=digest(path),archive=str(archive))


def candidate_review(repo,current,initial,components):
    repo=Path(repo);migration=repo/'Demos/UEPLyraIntegration/Migration';overlay=migration.parent/'Overlay'
    scope=[r['path'] for r in initial['assets'] if r['version']=='0.14.0']
    require(len(scope)==40 and scope==[r['path'] for r in current['assets'] if r['version']=='0.14.0'],'Exact original forty0.14 candidates required')
    dispositions=read(migration/'candidate_dispositions.json');by_asset={r['asset']:r for r in dispositions['candidates']}
    ledger_path=repo/dispositions['evidence_paths']['native_ledger'];ledger=read(ledger_path);record=ledger['runs'][0]
    folder=repo/record['directory'];summary=read(folder/'summary.json')
    require(summary['status']=='passed' and summary['process']['exit_code']==0,'Completed native class census required')
    pin,=[r for r in record['report_hashes'] if r['file']=='audit.json']
    require(sha(folder/'audit.json')==pin['sha256'].upper(),'Current-SDK class census report changed')
    census={r['asset']:r for r in read(folder/'audit.json')['assets']};index=index_hashes(summary['hashes'])
    modules={g['module'] for row in components for g in row['source_guards']};rows=[]
    for asset in scope:
        row=by_asset[asset];native=census[asset]
        require(native['original_class']==asset+'_C' and native['class_identity_preserved'] is True,'Original native class identity changed')
        if row['disposition']=='native-python-router':
            require(row['effective_python_class'].rsplit('.',1)[0] in modules,'Original gameplay/presentation component has no source-bound semantic comparison')
        else:
            require(row['disposition'] in ('retained-forwarder-inherited-python-parent','retained-unobservable-prompt-shell') and
                    set(row['original_entry_dispositions'])<={'direct-parent-forwarder-review','no-connected-execution-business','retained-native-source-review'},
                    'Unreviewed business in retained Explorer shell')
        relative=relative_asset(asset,Path('F:/LyraStarterGame'));source=overlay/relative
        if not source.is_file():source=Path('F:/LyraStarterGame')/relative
        stage=repo/'.build/LyraValidation/Full/Stage/Lyra'/relative
        recorded=index.get(key(source),index.get(key(stage),[]));require(recorded,'Original candidate asset absent from native census inputs')
        proof=source_guard(source,[dict(r,path=str(source.resolve())) for r in recorded]);require(sha(stage)==sha(source),'Current Experience asset differs from census source')
        rows.append(dict(asset=asset,version='0.14.0',disposition=row['disposition'],python_class=row.get('effective_python_class'),
            original_entry_dispositions=row['original_entry_dispositions'],original_class=asset+'_C',class_identity_preserved=True,
            asset_guard=proof,retained_reason=row['explicit_retention_reasons']))
    return dict(candidates=rows,native_census_ledger_sha256=sha(ledger_path),native_census_report_sha256=sha(folder/'audit.json'))


def control_source_guard(original,derived,repo,provenance):
    original=original.replace('\r\n','\n');restored=derived.replace('\r\n','\n')
    quoted="'"+str((Path(repo)/'Validation').resolve()).replace("'","''")+"'"
    if '$uepOriginalValidationRoot' in restored:
        binding='\n$uepOriginalValidationRoot='+quoted+'\n'
        require(restored.count(binding)==1,'One explicit original helper root binding required')
        restored=restored.replace(binding,'',1).replace('$uepOriginalValidationRoot','$PSScriptRoot')
    else:restored=restored.replace(quoted,'$PSScriptRoot')
    if provenance.get('shared_python_live_reader',False):
        pattern=r'function Read-ExplorerLiveJson\([^\n]+\n.*?\n\}'
        old=re.findall(pattern,original,re.S);new=re.findall(pattern,restored,re.S)
        require(len(old)==len(new)==1 and 'from uep_lyra_network_io import read_json' in new[0] and
                '[IO.FileStream]' not in new[0],'Exact shared live-reader boundary required')
        restored=restored.replace(new[0],old[0],1)
    if provenance['sdk_path_replacements']:
        new='.build/LyraValidation/BlueprintPython/20261023-pawn-sdk-causality/SDKBuild01/summary.json'
        old='.build/LyraValidation/BlueprintPython/20261023-current-third-person/SDKBuild01/summary.json'
        require(restored.count(new)==provenance['sdk_path_replacements'],'Exact current SDK path replacement required')
        restored=restored.replace(new,old)
    require(restored==original,'Experience control changed beyond helper root,SDK and scoped shared live-reader')


def integration_review(repo):
    from functools import lru_cache
    repo=Path(repo);root=repo/BASE;scripts=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts'
    sys.path.insert(0,str(scripts))
    catalogue=read(root/'retired-inputs.json');archives={(r['native_input_path'],r['sha256']):r['archive'] for r in catalogue['inputs']}
    @lru_cache(maxsize=None)
    def digest(path):return sha(path)
    cells=[];runs=[];retired=[];images=[]
    for scenario in SCENARIOS:
        revision='02' if scenario in ('ExplorerExperience','ArenaLocalInput','ArenaOpponentBomb') else ('05' if scenario=='ExplorerActionsNetwork' else '01')
        groups=[];folders=[];peers=0;network_reports=[]
        for profile in PROFILES:
            control=root/(scenario+'-'+profile+'-'+revision);folder=control/'Runtime';folders.append(folder)
            summary=read(folder/'summary.json');process_gate(summary)
            provenance=read(control/'control-provenance.json')
            require(not provenance['cpp_compile_executed'] and not provenance['cook_package_executed'] and
                    provenance['sdk_path_replacements']==int(scenario.startswith('Explorer')),
                    'Scoped current SDK control provenance differs')
            control_source_guard(Path(provenance['original']['archive']).read_text(encoding='utf-8-sig'),
                Path(provenance['derived']['path']).read_text(encoding='utf-8-sig'),repo,provenance)
            for name in ('original','derived','wrapper'):
                item=provenance[name];proof=frozen_input(item,repo,archives,digest)
                if proof:retired.append(proof)
            for item in provenance['sdk']['guards']+summary['hashes']:
                proof=frozen_input(item,repo,archives,digest)
                if proof:retired.append(proof)
            sdk={r['sha256'].upper() for r in provenance['sdk']['guards'] if Path(r['path']).name=='UnrealEditor-UnrealEnginePython.dll'}
            require(sdk=={SDK},'Current Experience used a different Editor SDK')
            processes=list(summary['processes'].values()) if summary.get('processes') else [summary['process']]
            peers+=len(processes)
            require(all(p['pid']>0 and p['exit_code']==0 for p in processes),'Current Experience native process failure')
            if scenario=='ExplorerActionsNetwork':
                group={p:read(folder/(p+'.json')) for p in ('server','A','B0')};network_reports.append(group)
                require(provenance['shared_python_live_reader'] is True,'Current network monitor must use shared JSON reader')
                reports=[folder/(p+'.json') for p in ('server','A','B0')]
            else:
                report=folder/('failure.json' if scenario.startswith('Explorer') else 'result.json');group=read(report);reports=[report]
            groups.append(group)
            runs.append(dict(scenario=scenario,profile=profile,directory=control.relative_to(repo).as_posix(),
                summary_sha256=sha(folder/'summary.json'),control_provenance_sha256=sha(control/'control-provenance.json'),
                reports=[dict(path=p.relative_to(repo).as_posix(),sha256=sha(p)) for p in reports],
                processes=[dict(pid=p['pid'],exit_code=0,duration_seconds=p['duration_seconds']) for p in processes],
                frozen_input_records=len(summary['hashes'])))
        if scenario=='ArenaLocalInput':
            module=importlib.import_module('uep_lyra_abilities.arena_natural_bomb_contract')
            for report in groups:module.validate(report)
            def outcome(report):
                return dict(remaining_before=report['drop']['remaining_before'],remaining_after=report['drop']['remaining_after'],
                    health_before=report['natural']['health_before'],health_after=report['natural']['health_after'],
                    refund=report['natural']['remaining_after_refund'],
                    hud={phase:sorted((r['target_owner'],r['value'],r['text']) for r in rows) for phase,rows in report['hud'].items()})
            require(outcome(groups[0])==outcome(groups[1]),'Original/Python natural bomb,death,refund or HUD outcome differs')
            for profile,report in zip(PROFILES,groups):
                require(report['native_timing_mode']=='variable','Current Arena variable-frame native delay coverage missing')
                for row in report['images']:
                    image=Path(row['path']);images.append(dict(profile=profile,phase=row['phase'],path=image.relative_to(repo).as_posix(),sha256=sha(image)))
        elif scenario=='ArenaOpponentBomb':
            importlib.import_module('uep_lyra_abilities.arena_opponent_bomb_contract').compare(folders)
        else:
            module={'ExplorerExperience':'uep_lyra_characters.explorer_experience_contract',
                'ExplorerGameplay':'uep_lyra_abilities.explorer_gameplay_contract',
                'ExplorerFollow':'uep_lyra_world.explorer_follow_contract',
                'ExplorerActionsNetwork':'uep_lyra_abilities.explorer_actions_network_contract'}[scenario]
            importlib.import_module(module).validate_pair(groups)
        cell=dict(scenario=scenario,profiles=list(PROFILES),pair_semantics_passed=True,current_editor_sdk=SDK,
            native_processes=peers,all_native_exits_zero=True)
        if scenario=='ExplorerActionsNetwork':
            require(all(g['A']['player_id']!=g['B0']['player_id'] for g in network_reports),'Actual network owners not distinct')
            cell['distinct_clients']=2
        if scenario.startswith('Arena'):cell['local_players']=2
        cells.append(cell)
    integration_gate(cells)
    visual=read(root/'visual-review.json')
    require(visual['status']=='passed' and visual['images']==[dict(r,actual_native_image_reviewed=True,owner_hud_readable=True) for r in images],
            'Direct original/Python Arena native frame review required')
    return dict(cells=cells,runs=runs,images=images,retired_test_control_inputs=retired,
        retired_input_catalogue_sha256=sha(root/'retired-inputs.json'),visual_review_sha256=sha(root/'visual-review.json'))


def inspect(repo,current,initial):
    repo=Path(repo);components=component_review(repo);candidates=candidate_review(repo,current,initial,components)
    integration=integration_review(repo)
    return dict(status='passed',criterion=REQUIREMENT,completion_proven=True,platform='Win64',configuration='Development',
        original_candidates=40,candidate_review=candidates,original_component_records=49,shared_cue_parent_records=1,
        component_records=components,current_integration=integration,current_accepted_native_processes=16,
        production_policy_or_assets_changed=False,cpp_compile_executed=False,cook_package_executed=False,
        full_migration_regression_executed=False,full_migration_acceptance_proven=False,
        limits=['The exact original0.14 Explorer and TopDownArena criterion is accepted;older component captures retain their own SDK and current integration uses SDK236 plus approved guard246.',
            'Explorer uses original placed targets/native input,actual two-client prediction/inventory/local progress,menus and navigation/cancel/travel. Retained empty prompt and inherited follow-Pawn shells keep their explicit native boundaries.',
            'Arena uses two native local players,variable-frame natural bomb/death/refund/HUD images and opponent death/kill/team scoring. The opponent fixture retains its bounded pose setup.',
            'Server local montage callback count is not a universal GAS completion signal. Correlate actual active-at-entry/native inactive/spec-zero/task-zero state,client callback and authoritative outcomes for the same action. No native C++ event interception claim.',
            'No whole-frame pixel/audio equality,hardware input,packaged Experience networking,other platform/configuration,tag or publication claim. Failed captures and exact retired test/control inputs remain preserved.'])


def verify_documentation(document,current,initial,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original two-Experience requirement required')
    expected=inspect(repo,current,initial);require(document.get('review')==expected,'Recorded Experience proof differs from source-bound actual evidence')
    return {k:expected[k] for k in ('status','criterion','original_candidates','current_accepted_native_processes','platform','configuration')}
