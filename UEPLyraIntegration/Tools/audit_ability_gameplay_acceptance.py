"""Original six-behavior gameplay criterion; saved native evidence only."""
import ast
from pathlib import Path
import re

from audit_ability_identity_acceptance import (execute_gate,policy_modules,
    report_dependency_guard,runtime_guards)
from audit_effects_match_acceptance import closure
from audit_ui_failure_cancellation_acceptance import source_guard
from audit_ui_navigation_acceptance import index_hashes,key,read,sha

REQUIREMENT = ('Fire, reload, ammo exhaustion, switching, death and respawn pass BP/Python '
               'comparison in Standalone and one-server/two-client play.')
A,C,W='uep_lyra_abilities.','uep_lyra_characters.','uep_lyra_weapons.'
LEGACY = (
 (92,'Differential07NativeGASEnds'),(95,'AbilityRuntime03NativeViewTarget'),(70,'StandaloneRegression02'),(75,'Differential03'),
 (93,'PistolNetwork05WeaponTrace'),(93,'RifleNetwork05WeaponTrace'),(93,'ShotgunNetwork03WeaponTrace'),
 (97,'ImpactNetwork04BoundedLifeSamples'),(85,'Network03NativeRPC'),(70,'Network09'),
 (26,'PostFamily-pistol-Standalone01'),(26,'PostFamily-rifle-Standalone01'),(26,'PostFamily-shotgun-Standalone01'),(26,'NetShooterStandalone01'),
 (219,'Pistol01'),(219,'Rifle01'),(219,'Shotgun01'),(219,'NetShooter01'),
 (220,'Pistol03'),(220,'Rifle01'),(220,'Shotgun01'),(220,'Standalone01'),(20,'Network01'),
 (25,'Differential03'),(25,'Network01'),(21,'Differential05'),(21,'Network05'),
 (238,'OriginalA03CaptureBarrier'),(238,'OriginalB02CaptureBarrier'),(238,'PythonA03CaptureBarrier'),(238,'PythonB01CaptureBarrier'),
 (239,'Original01'),(239,'Python01'),
 (260,'QuickslotStandalone01'),(260,'RifleStandalone01'),(260,'ShotgunStandalone01'),
 (261,'Standalone02'),(261,'Network01'),
)
RESPAWN_POLICIES=[W+'weapon_ability_fire_mixin',A+'death_mixin',A+'auto_respawn_activation_mixin',
                  C+'hero_default_death_mixin',C+'death_started_mixin']
COVERAGE = {
 'fire':dict(Standalone=[(92,'Differential07NativeGASEnds'),(95,'AbilityRuntime03NativeViewTarget'),(70,'StandaloneRegression02'),(75,'Differential03')],
             network=[(93,'PistolNetwork05WeaponTrace'),(93,'RifleNetwork05WeaponTrace'),(93,'ShotgunNetwork03WeaponTrace'),(97,'ImpactNetwork04BoundedLifeSamples'),(85,'Network03NativeRPC'),(70,'Network09')]),
 'reload':dict(Standalone=[(26,n) for n in ('PostFamily-pistol-Standalone01','PostFamily-rifle-Standalone01','PostFamily-shotgun-Standalone01','NetShooterStandalone01')],
               network=[(219,n) for n in ('Pistol01','Rifle01','Shotgun01','NetShooter01')]),
 'ammo-exhaustion':dict(Standalone=[(220,'Standalone01'),(260,'RifleStandalone01'),(260,'ShotgunStandalone01'),(261,'Standalone02')],
                        network=[(220,'Pistol03'),(220,'Rifle01'),(220,'Shotgun01'),(261,'Network01')]),
 'switching':dict(Standalone=[(260,'QuickslotStandalone01'),(25,'Differential03')],network=[(20,'Network01'),(25,'Network01')]),
 'death':dict(Standalone=[(21,'Differential05'),(239,'Original01'),(239,'Python01')],
              network=[(21,'Network05'),(238,'OriginalA03CaptureBarrier'),(238,'OriginalB02CaptureBarrier'),(238,'PythonA03CaptureBarrier'),(238,'PythonB01CaptureBarrier')]),
 'respawn':dict(Standalone=[(239,'Original01'),(239,'Python01')],
                network=[(238,'OriginalA03CaptureBarrier'),(238,'OriginalB02CaptureBarrier'),(238,'PythonA03CaptureBarrier'),(238,'PythonB01CaptureBarrier')]),
}


def require(value,message):
    if not value:raise ValueError(message)


def record_for(migration,batch,name):
    path,=(migration/'Acceptance').glob(f'{batch:02}-*.json');ledger=read(path)
    rows=[r for r in ledger.get('runs',ledger.get('native_runs',[])) if Path(r['directory']).name==name and
          (batch!=20 or '20261016-quickslot/' in r['directory'].replace('\\','/')) and
          (batch!=25 or '20261016-drop-weapon/' in r['directory'].replace('\\','/'))]
    require(len(rows)==1,'Exactly the related native gameplay record is required')
    return path,ledger,rows[0]


def report_hash(ledger,record,directory,name):
    for rows in (record.get('report_hashes'),record.get('reports'),record.get('logs')):
        if isinstance(rows,list):
            matches=[r['sha256'].upper() for r in rows if r['file']==name]
            if matches:require(len(matches)==1,'Duplicate report pins');return matches[0]
        elif isinstance(rows,dict) and name.endswith('.json') and Path(name).stem in rows:return rows[Path(name).stem].upper()
    if name.endswith('.json') and record.get('report_sha256'):return record['report_sha256'].upper()
    if name.endswith('.log') and record.get('log_sha256'):return record['log_sha256'].upper()
    relative=(Path(directory)/name).as_posix()
    matches=[r['sha256'].upper() for r in ledger.get('input_hashes',[]) if r['path'].replace('\\','/')==relative]
    require(len(matches)==1,'Exact native gameplay report/log pin missing: '+relative)
    return matches[0]


def arguments(values):
    args=list(values)
    if args[:1]==['-B']:args.pop(0)
    if args[:2]==['-X','utf8']:args=args[2:]
    require(args and (args[0]=='-m' or Path(args[0]).name.startswith('validate_')),'Explicit pure gameplay gate required')
    return ['-B',*args]


def processes(summary,integrated=False):
    require(summary['status']=='passed' and summary.get('error') is None and not summary['cpp_compile_executed'] and
            not summary['cook_package_executed'],'Native gameplay summary failed or changed build scope')
    peers=summary.get('processes')
    if peers:
        require(set(peers)==({'server','A','B0','B1'} if integrated else {'server','A','B0'}),'Actual authority and two independent clients required')
        rows=list(peers.values());mode='network'
    else:
        rows=[summary['process']];mode='Standalone';args=rows[0]['arguments']
        require('-game' in args and '-server' not in args and args[1].startswith('/') and '?listen' not in args[1].lower(),
                'Single generic/editor or listen-server process cannot prove Standalone')
    require(len({r['pid'] for r in rows})==len(rows) and all(r['pid']>0 and r['exit_code']==0 for r in rows),'Native process identity/exit differs')
    if not integrated:require(summary['external_gate']['exit_code']==0,'Independent native gameplay gate failed')
    return rows,mode


def matrix(jobs):
    by_spec={(r['batch'],r['name']):r for r in jobs};rows=[]
    require(len(by_spec)==len(jobs),'Native gameplay records must not be duplicated')
    for behavior,modes in COVERAGE.items():
        for mode,specs in modes.items():
            require(specs and all(spec in by_spec and by_spec[spec]['mode']==mode for spec in specs),
                    'Missing original behavior/family/mode: '+behavior+'/'+mode)
            rows.append(dict(behavior=behavior,mode=mode,native_directories=[by_spec[spec]['directory'] for spec in specs]))
    require(len(rows)==12,'All six original behaviors in both native modes required')
    return rows


def integrated_outcome(report):
    rows=[]
    for row in report['phases']:
        models={}
        for peer,state in row.get('server_after',{}).items():
            weapon=state.get('weapon')
            models[peer]=None if weapon is None else {k:weapon[k] for k in ('definition','magazine','spare','maximum','slot')}
        rows.append(dict(phase=row['phase'],models=models))
    return rows


def inspect(repo,current,initial):
    repo=Path(repo).resolve();migration=repo/'Demos/UEPLyraIntegration/Migration';scripts=migration.parent/'Overlay/Content/Scripts'
    identity_path,=(migration/'Acceptance').glob('256-*.json');identity=read(identity_path)['review']
    scope=[r for r in initial['assets'] if r['version']=='0.11.0']
    require(len(scope)==37 and [r['path'] for r in scope]==[r['asset'] for r in identity['candidates']],'Exact original thirty-seven candidates required')
    require([(r['path'],r['version']) for r in current['assets']]==[(r['path'],r['version']) for r in initial['assets']],'Original paths/versions changed')
    for pin in (identity['source_candidate_guard'],identity['native_class_census']):require(sha(repo/pin['path'])==pin['sha256'],'Current source/census review changed')
    for candidate in identity['candidates']:
        for pin in candidate['asset_guards']:require(sha(pin['current_path'])==pin['current_sha256'],'Current class/typed transport asset changed')
    latent=next(j for j in identity['native_execution_runs'] if j['batch']==60);latent_summary=repo/latent['directory']/'summary.json'
    require(sha(latent_summary)==latent['summary_sha256'],'Pinned native latent allocator proof changed')
    latent_path=scripts/'uep_lyra_characters/latent_keys.py';ix=index_hashes(read(latent_summary)['hashes'])
    latent_proof=dict(directory=latent['directory'],summary_sha256=sha(latent_summary),**source_guard(latent_path,ix[key(latent_path)]))
    macro=next(r for r in read(migration/'effects_match_acceptance.json')['review']['native_runs'] if r['contract'].endswith('macro_closure_contract'))
    contexts=dict(macro_native_directory=macro['directory'],macro_native_guard=sha(scripts/'uep_lyra_weapons/macro_policies.py'))
    jobs=[]
    for batch,name in (*LEGACY,(221,'Original01'),(221,'Python01')):
        lp,ledger,record=record_for(migration,batch,name);folder=repo/record['directory'];summary_path=folder/'summary.json'
        require(sha(summary_path)==record['summary_sha256'].upper(),'Pinned native gameplay summary changed')
        summary=read(summary_path);peers,mode=processes(summary,batch==221)
        index=index_hashes(summary.get('hashes',summary.get('input_hashes')))
        report_names=[peer+'.json' for peer in summary['processes']] if summary.get('processes') else [Path(summary['external_gate']['arguments'][-1]).name]
        pins=[];raw={}
        for filename in report_names:
            path=folder/filename;require(sha(path)==report_hash(ledger,record,record['directory'],filename),'Pinned native gameplay report changed')
            pins.append(dict(file=filename,sha256=sha(path)));raw[Path(filename).stem]=read(path)
        if batch==221:
            from uep_lyra_weapon_protocol import validate_reports
            from uep_lyra_weapons.integrated_profile_contract import validate as validate_profile
            profile=summary['gameplay_profile'];profile_checks={peer:validate_profile(value['integrated_gameplay'],profile) for peer,value in raw.items()}
            flags={name:summary[name] for name in ('combat_hud','debug_spread','production_reticles','reticle_hosts','ability_progress','ability_failure','dash_cooldown','respawn_timer','quickbar_slots','nameplates')}
            semantic=validate_reports(raw,summary['run_id'],**flags)
            require(semantic==summary['protocol_validation'] and semantic['phase_count']==19 and semantic['rejoin_tested'],'Integrated native protocol differs')
            seeds=[W+'weapon_ability_fire_mixin',A+'reload_magazine_mixin',A+'autoreload_mixin',A+'quickslot_mixin',W+'integrated_profile_validation']
            contracts=['uep_lyra_weapon_protocol',W+'integrated_profile_contract'];args=None
        else:
            args=arguments(summary['external_gate']['arguments']);contract=args[args.index('-m')+1] if '-m' in args else Path(args[1]).name
            if batch in (238,239):seeds=RESPAWN_POLICIES
            elif batch==260 and name!='QuickslotStandalone01':seeds=[A+'autoreload_mixin']
            elif batch==261:seeds=[W+'netshooter_ability_mixin',W+'netshooter_actor_mixin']
            else:seeds=policy_modules(contract)
            if '-m' in args:contracts=[contract]
            else:
                path=migration.parent/'Tools'/contract
                contracts=[n.module for n in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))) if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('uep_')]
            semantic=execute_gate(args);profile_checks=None
        dependencies=[report_dependency_guard(module,path,index.get(key(path),[])) for module,path in sorted(closure(scripts,contracts).items())]
        guards=runtime_guards(repo,dict(hashes=summary.get('hashes',summary.get('input_hashes'))),seeds,contexts,latent_proof)
        logs=[]
        for process in peers:
            path=Path(next(a.split('=',1)[1] for a in process['arguments'] if a.startswith('-abslog=')))
            require(path.resolve().parent==folder.resolve(),'Native gameplay log escaped its selected directory')
            text=path.read_text(encoding='utf-8-sig')
            require('Traceback' not in text and 'Fatal error' not in text and 'Goodbye Python' in text and 'Log file closed' in text and
                    text.index('Goodbye Python')<text.rindex('Log file closed'),'Native gameplay interpreter/shutdown failed')
            diagnostics=re.findall(r'[^\r\n]*(?:Ensure condition failed|Log\w+:\s*Error:)[^\r\n]*',text)
            if diagnostics:require(batch==97 and sha(path)==report_hash(ledger,record,record['directory'],path.name),'Unexpected/unpinned native gameplay diagnostic')
            logs.append(dict(file=path.name,sha256=sha(path),preserved_original_template_diagnostics=len(diagnostics)))
        jobs.append(dict(batch=batch,name=name,directory=record['directory'],ledger=lp.relative_to(repo).as_posix(),ledger_sha256=sha(lp),
                         summary_sha256=sha(summary_path),mode=mode,native_pids=[p['pid'] for p in peers],native_processes=len(peers),
                         report_pins=pins,log_pins=logs,policy_modules=seeds,current_policy_guards=guards,
                         current_report_dependency_guards=dependencies,semantic_gate=semantic,integrated_profile_checks=profile_checks))
    require(len(jobs)==40 and sum(r['native_processes'] for r in jobs)==88,'Complete native gameplay evidence set differs')
    coverage=matrix(jobs)
    from compare_weapon_respawn_runs import compare as compare_network_respawn
    from uep_lyra_weapons.weapon_respawn_standalone_contract import compare_runs as compare_standalone_respawn
    network_respawn=compare_network_respawn([repo/j['directory'] for j in jobs if j['batch']==238],verify_frozen=False)
    standalone_respawn=compare_standalone_respawn([repo/j['directory'] for j in jobs if j['batch']==239],verify_frozen=False)
    outcomes=[integrated_outcome(read(repo/j['directory']/'server.json')) for j in jobs if j['batch']==221]
    require(len(outcomes)==2 and outcomes[0]==outcomes[1] and len(outcomes[0])==19,'Original/Python integrated authority weapon outcomes differ')
    return dict(schema_version=1,status='passed',version='0.11.0',criterion=REQUIREMENT,completion_proven=True,original_candidates=37,
                source_identity_ledger=dict(path=identity_path.relative_to(repo).as_posix(),sha256=sha(identity_path)),
                behavior_mode_matrix=coverage,native_gameplay_runs=jobs,native_gameplay_runs_revalidated=40,referenced_native_processes=88,
                natural_network_death_respawn_comparison=network_respawn,natural_standalone_death_respawn_comparison=standalone_respawn,
                integrated_nineteen_phase_original_python_outcomes=outcomes[0],
                mutable_whole_stage_hashes_not_used_as_current_equivalence=True,current_selected_policy_and_class_transport_guards_required=True,
                prototype_original_zero_autoreload_grant_preserved=True,original_netshooter_component_defect_preserved=True,
                general_netshooter_component_correctness_accepted=False,all_historical_runs_use_current_sdk=False,
                new_native_processes_launched_by_review=0,production_policy_or_assets_changed=False,
                cpp_compile_executed=False,cook_package_executed=False,full_regression_executed=False,
                full_version_acceptance=False,full_migration_acceptance_proven=False)


def verify_documentation(document,current,initial,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original six-behavior gameplay criterion required')
    expected=inspect(repo,current,initial)
    require(document['review']==expected,'Ability gameplay review differs from the current pinned native evidence')
    return {name:expected[name] for name in ('status','criterion','original_candidates','native_gameplay_runs_revalidated',
        'referenced_native_processes','new_native_processes_launched_by_review','full_migration_acceptance_proven')}
