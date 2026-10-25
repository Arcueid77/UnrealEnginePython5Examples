"""Source-bound native evidence for the original multi-client match criterion."""
import importlib,re
from pathlib import Path
from audit_ui_failure_cancellation_acceptance import source_guard,process_gate,log_gate,ledger_record,report_pin
from audit_ui_navigation_acceptance import read,sha,key,index_hashes
from audit_effects_match_acceptance import verify_source,historical_source
from audit_static_scope_dispositions import relative_asset
from uep_lyra_weapons.cp_network_contract import compare_profiles

REQUIREMENT='Multi-client score/phase state, local notifications and cleanup agree.'
BASE='.build/LyraValidation/BlueprintPython/'
CP=BASE+'20261026-cp-network/'
ACCEPTANCE='Demos/UEPLyraIntegration/Migration/Acceptance/'
RELAY=('uep_lyra_hud.elimination_feed_relay_mixin','uep_lyra_hud.accolade_relay_mixin')
TDM=('uep_lyra_weapons.scoring_base_mixin','uep_lyra_weapons.tdm_scoring_mixin','uep_lyra_weapons.game_phases_mixin',*RELAY)
CONTROL=('uep_lyra_weapons.scoring_base_mixin','uep_lyra_weapons.cp_scoring_mixin','uep_lyra_weapons.game_phases_mixin','uep_lyra_world.control_point_feedback_mixin','uep_lyra_hud.control_point_widgets_mixin','uep_lyra_hud.cue_widget_mixin','uep_lyra_hud.match_message_mixin','uep_lyra_hud.waiting_message_mixin')
SPECS=[
    (129,BASE+'20261020-gameplay-relays/Network02CleanupBarrier','uep_lyra_hud.notification_relays_network_contract','UEP_NOTIFICATION_RELAYS_NETWORK',RELAY),
    (205,BASE+'20261021-tdm-lethal-network/Fallback04','uep_lyra_weapons.tdm_lethal_network_contract','UEP_TDM_LETHAL_NETWORK',TDM),
    (205,BASE+'20261021-tdm-lethal-network/Python01','uep_lyra_weapons.tdm_lethal_network_contract','UEP_TDM_LETHAL_NETWORK',TDM),
    (252,CP+'Original03','uep_lyra_weapons.cp_network_contract','UEP_CP_NETWORK',CONTROL),
    (252,CP+'Python01','uep_lyra_weapons.cp_network_contract','UEP_CP_NETWORK',CONTROL),
]
TDM_CHECKPOINTS=('attacker_health','victim_health','attacker_kills_delta','victim_deaths_delta','attacker_team_score_delta','other_team_score_delta','target_score','postgame_damage_immunity','native_postgame_phase_active','native_playing_phase_inactive')

def require(value,message):
    if not value:raise ValueError(message)

def compare_tdm(original,python):
    require(set(original)==set(python)=={'server','A','B0'},'Two complete TDM native groups required')
    require({r['requested_profile'] for r in original.values()}=={'BlueprintFallback'} and {r['requested_profile'] for r in python.values()}=={'Python'},'Paired original/Python TDM profiles required')
    require(original['server']['run_id']!=python['server']['run_id'],'Independent TDM process groups required')
    for peer in original:
        for name in TDM_CHECKPOINTS:require(original[peer]['result'][name]==python[peer]['result'][name],'Original/Python TDM checkpoint differs: '+peer+'/'+name)
    return dict(status='passed',native_processes=6,actual_clients=4,native_lethal_cases=2)

def semantic_gate(name,directory,reports):
    module=importlib.import_module(name)
    if name.endswith('notification_relays_network_contract'):return module.validate(reports['server'],{p:reports[p] for p in ('A','B0')})
    return module.validate_all(directory)

def relay_log_gate(text,peer='server'):
    require(peer in ('server','A','B0'),'Known native relay peer required')
    require(not any(v in text for v in ('Traceback','Ensure condition failed','Fatal error')) and not re.search(r'Log\w+:\s*Error:',text),'Unexpected native relay diagnostic')
    marker='UEP_NOTIFICATION_RELAYS_NETWORK_PASSED' if peer=='server' else 'UEP_NOTIFICATION_RELAYS_SHUTDOWN_PASSED'
    needles=('Goodbye Python',marker,'Log file closed')
    require(all(n in text for n in needles),'Native relay completion/shutdown marker missing')
    positions=[text.index(n) if n!='Log file closed' else text.rindex(n) for n in needles]
    require(positions==sorted(positions) and len(set(positions))==3,'Native relay shutdown ordering differs')

def inspect(repo):
    repo=Path(repo).resolve();scripts=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts';migration=repo/'Demos/UEPLyraIntegration/Migration'
    prior_path=repo/ACCEPTANCE/'251-original-effect-audio-phase-score-notification-checkpoint-acceptance.json';prior=read(prior_path)['review']
    require(prior['completion_proven'] and prior['checkpoint_candidates']==63,'Accepted original checkpoint inventory required')
    macro=next(r for r in prior['native_runs'] if r['batch']==141 and r['contract'].endswith('macro_closure_contract'))
    contexts=dict(macro_native_directory=macro['directory'],macro_native_guard=sha(scripts/'uep_lyra_weapons/macro_policies.py'))
    jobs=[];raw=[]
    for batch,directory,contract,marker,seeds in SPECS:
        folder=repo/directory;summary_path=folder/'summary.json';summary=read(summary_path)
        require(process_gate(summary)==3 and set(summary['processes'])=={'server','A','B0'},'One actual authority/two-client group required')
        require(not summary['cpp_compile_executed'] and not summary['cook_package_executed'],'This review must reuse builds without cooking')
        require(contract in summary['external_gate']['arguments'],'Different native semantic gate recorded')
        reports={p:read(folder/(p+'.json')) for p in ('server','A','B0')};pins=[];ledger_path=None
        if batch!=252:
            ledger_path=next((repo/ACCEPTANCE).glob(str(batch)+'-*.json'));ledger=read(ledger_path);record=ledger_record(ledger,directory)
            require(sha(summary_path)==record['summary_sha256'].upper(),'Historical native summary changed')
            for peer in reports:require(sha(folder/(peer+'.json'))==report_pin(ledger,record,Path(directory),peer+'.json'),'Historical native report changed')
        for peer,report in reports.items():
            process=summary['processes'][peer];args=process['arguments'];require(process['pid']>0 and process['exit_code']==0,'Actual native peer exit0 required')
            log=folder/(peer+'.log')
            recorded_log=Path(next(a.split('=',1)[1] for a in args if a.startswith('-abslog=')))
            require(recorded_log.resolve()==log.resolve(),'Recorded native log escaped its process directory')
            text=log.read_text(encoding='utf-8-sig')
            if batch==129:relay_log_gate(text,peer)
            else:log_gate(text,marker)
            pins.append(dict(peer=peer,report_sha256=sha(folder/(peer+'.json')),log_sha256=sha(log),pid=process['pid'],exit_code=0))
        require(len({p['pid'] for p in summary['processes'].values()})==3,'A native process was reused for two peers')
        gate=semantic_gate(contract,folder,reports);index=index_hashes(summary['hashes']);contract_path=scripts/Path(*contract.split('.')).with_suffix('.py')
        try:contract_guard=source_guard(contract_path,index.get(key(contract_path),[]))
        except ValueError:
            require(batch!=252,'Current CP runtime contract changed after its native run')
            text,history=historical_source(repo,contract_path,index.get(key(contract_path),[]))
            namespace=dict(__name__=contract+'_pinned',__package__=contract.rsplit('.',1)[0],__file__=str(contract_path))
            exec(compile(text,str(contract_path),'exec'),namespace)
            require('validate_all' in namespace,'Historical contract must independently validate all native peers')
            original_gate=namespace['validate_all'](folder);require(original_gate['status']=='passed','Original native contract rejected its raw peer reports')
            contract_guard=dict(current_sha256=sha(contract_path),**history,original_semantic_gate=original_gate,current_semantic_gate_also_passed=True)
        guards=verify_source(repo,summary,seeds,contexts);assets=[]
        selected=[r for r in prior['candidate_asset_guards'] if set(r['effective_policy_modules']).intersection(seeds)]
        require(selected,'Native score/phase/notification asset family missing')
        stage=Path(summary['processes']['server']['arguments'][0]).parent
        for candidate in selected:
            for row in candidate['guards']:
                path=Path(row['current_path']);rows=index.get(key(path),[]);stage_path=None
                if not rows:
                    stage_path=stage/relative_asset(row['asset'],Path('F:/LyraStarterGame'));rows=[dict(r,path=str(path)) for r in index.get(key(stage_path),[])]
                if not rows:
                    # Native Cue children retain their original packages. Their
                    # separately pinned checkpoint fingerprints are historical;
                    # all replacement/transport assets still need this run's hash.
                    require(path.is_relative_to(Path('F:/LyraStarterGame')),'Replacement asset was not frozen by its network run: '+str(path))
                    matches=row['matching_native_fingerprints'];require(matches,'Retained native child lacks original checkpoint fingerprints')
                    current_sha=sha(path);require(all(current_sha==m['native_sha256'] for m in matches) and sha(stage_path)==current_sha,'Retained native child/stage differs from its pinned original checkpoint')
                    assets.append(dict(asset=row['asset'],current_path=str(path),recorded_stage_path=str(stage_path),current_sha256=current_sha,equivalence='retained-native-package-matches-separately-pinned-checkpoint-and-current-stage',frozen_during_network_run=False,historical_checkpoint_fingerprints=matches))
                    continue
                assets.append(dict(asset=row['asset'],current_path=str(path),recorded_stage_path=str(stage_path) if stage_path else None,**source_guard(path,rows)))
        extra=[]
        if batch==252:
            for module in ('uep_lyra_weapons.cp_network_validation','uep_lyra_hud.startup'):
                path=scripts/Path(*module.split('.')).with_suffix('.py');extra.append(dict(module=module,**source_guard(path,index.get(key(path),[]))))
            for dependency,status in (('20261023-pawn-sdk-causality/SDKBuild01/summary.json','built_requires_native_acceptance'),('20261026-pawn-init-guard/Build04LinkResume/summary.json','passed')):
                path=repo/BASE/dependency;source_guard(path,index.get(key(path),[]));proof=read(path);require(proof['status']==status and proof['error'] is None,'Reviewed current SDK/isolated guard build missing')
                processes=[proof['process']] if status=='built_requires_native_acceptance' else [r['process'] for r in proof['processes']]
                require(processes and all(p['exit_code']==0 for p in processes),'Reused build did not exit0')
                for row in proof.get('source_hashes',[])+proof.get('binary_after',[])+proof.get('products',[])+proof.get('protected',[]):require(sha(row['path'])==row['sha256'].upper(),'Reused current native source/binary/protected input changed')
                extra.append(dict(path=str(path),sha256=sha(path),status=status,historical_build_artifact_not_new_build=True))
        jobs.append(dict(batch=batch,directory=directory,summary_sha256=sha(summary_path),ledger=str(ledger_path.relative_to(repo)) if ledger_path else None,ledger_sha256=sha(ledger_path) if ledger_path else None,
            contract=contract,contract_guard=contract_guard,semantic_gate=gate,native_peers=pins,current_production_source_guards=guards,asset_guards=assets,current_observer_and_build_guards=extra,native_processes=3,historical_binary= batch!=252))
        raw.append(reports)
    tdm=compare_tdm(raw[1],raw[2]);cp=compare_profiles(raw[3],raw[4]);failed=[]
    for name in ('Original01','Original02'):
        folder=repo/CP/name;summary=read(folder/'summary.json');require(summary['status']=='failed','Failed observer attempts must remain failed')
        archives=[]
        for file in ('cp_network_validation.py','cp_network_contract.py','Run-UEP58CPNetworkValidation.ps1'):
            path=folder/'Inputs'/file;matches=[r for r in summary['hashes'] if Path(r['path']).name==file];require(matches and {r['sha256'].upper() for r in matches}=={sha(path)},'Failed attempt source archive differs')
            archives.append(dict(file=file,sha256=sha(path)))
        failed.append(dict(directory=str(folder.relative_to(repo)),status='failed',summary_sha256=sha(folder/'summary.json'),error=summary['error'],native_processes=len(summary['processes']),archived_inputs=archives))
    return dict(schema_version=1,status='passed',criterion=REQUIREMENT,completion_proven=True,version='0.12.0',prior_checkpoint_ledger=dict(path=str(prior_path.relative_to(repo)),sha256=sha(prior_path)),
        native_runs=jobs,tdm_profile_comparison=tdm,cp_profile_comparison=cp,preserved_failed_observer_attempts=failed,referenced_native_processes=15,historical_native_processes=9,current_cp_native_processes=6,preserved_failed_native_processes=6,actual_client_processes=10,
        reliable_kill_multicast_cases=2,unreliable_owner_notification_cases=6,negative_notification_cases=2,authority_relay_cases=10,client_relay_observations=20,natural_lethal_cases=2,natural_capture_cases=2,
        client_phase_evidence='Replicated native PostGame DamageImmunity and native MatchDecided Cue/presentation;the phase subsystem itself runs on authority',
        current_sdk_used_for_every_historical_run=False,new_native_processes_launched_by_review=0,packet_loss_guarantee=False,travel_rejoin_tested_by_this_review=False,physical_audio_output_tested=False,pixels_tested=False,packaged_runtime=False,
        cpp_compile_executed=False,cook_package_executed=False,full_regression_executed=False,full_version_acceptance=False,full_migration_acceptance_proven=False)

def verify_documentation(document,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original multi-client score/phase/notification criterion required')
    expected=inspect(repo);require(document['review']==expected,'Network match review differs from current pinned native/source evidence')
    return {k:expected[k] for k in ('status','criterion','referenced_native_processes','historical_native_processes','current_cp_native_processes','natural_capture_cases','new_native_processes_launched_by_review','full_migration_acceptance_proven')}
