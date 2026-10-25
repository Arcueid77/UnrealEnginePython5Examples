"""Revalidate one original UI checklist item against pinned native evidence.

No native process is launched. Recorded runtime versions remain explicit;
current policy/assets must still match those runs and the current census.
"""
import argparse,hashlib,importlib,json,re
from pathlib import Path
from audit_candidate_dispositions import verify_documentation as verify_candidates

REQUIREMENT='Failures/cancellations are tested, not accepted only on the success path.'
HUD='Demos/UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_hud/'
ACCEPTANCE='Demos/UEPLyraIntegration/Migration/Acceptance'
RUNTIME='.build/LyraValidation/BlueprintPython/'

def require(value,message):
    if not value:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def normalized(path):return str(path).replace('\\','/')
def digest_bytes(value):return hashlib.sha256(value).hexdigest().upper()

def source_guard(path,hashes):
    path=Path(path).resolve();records=[r for r in hashes if Path(r['path']).resolve()==path]
    require(records,'Native run did not freeze required source/asset: '+str(path))
    data=path.read_bytes();variants={digest_bytes(data):'exact-bytes'}
    if path.suffix=='.py':
        text=data.decode('utf-8-sig').replace('\r\n','\n')
        for value in (text.encode('utf-8'),text.replace('\n','\r\n').encode('utf-8')):
            variants.setdefault(digest_bytes(value),'newline-or-bom-only')
            variants.setdefault(digest_bytes(b'\xef\xbb\xbf'+value),'newline-or-bom-only')
    expected={r['sha256'].upper() for r in records};require(len(expected)==1,'Mixed frozen source hashes')
    frozen=next(iter(expected));require(frozen in variants,'Current UI source/asset changed since native evidence: '+str(path))
    return dict(current_sha256=digest_bytes(data),native_sha256=frozen,equivalence=variants[frozen])

def process_gate(summary):
    require(summary['status']=='passed' and summary.get('error') is None,'Accepted native summary failed')
    processes=[summary['process']] if summary.get('process') else list(summary.get('processes',{}).values())
    require(processes and all(p['exit_code']==0 for p in processes),'Native processes did not all exit0')
    require(summary['external_gate']['exit_code']==0,'Independent native semantic gate failed')
    return len(processes)

def log_gate(text,marker,expected_errors=()):
    require(not any(value in text for value in ('Traceback','Ensure condition failed','Fatal error')),'Unexpected native diagnostic failure')
    actual=re.findall(r'Log\w+:\s*Error:\s*([^\r\n]+)',text)
    require(actual==list(expected_errors),'Unexpected/missing declared native error messages')
    needles=(marker+'_DIFFERENTIAL_PASSED','Goodbye Python',marker+'_SHUTDOWN_PASSED','Log file closed')
    require(all(value in text for value in needles),'Native shutdown marker missing')
    positions=[text.index(value) if value!='Log file closed' else text.rindex(value) for value in needles]
    require(positions==sorted(positions) and len(set(positions))==4,'Native shutdown ordering changed')

def ledger_record(ledger,directory):
    records=ledger.get('native_runs',ledger.get('runs',[]))
    if ledger.get('native_run'):records=[ledger['native_run']]
    rows=[r for r in records if normalized(r['directory'])==directory]
    require(len(rows)==1,'One exact accepted ledger run required: '+directory);return rows[0]

def report_pin(ledger,record,folder,name):
    for row in record.get('report_hashes',[]):
        if row['file']==name:return row['sha256'].upper()
    if record.get('report_sha256'):return record['report_sha256'].upper()
    relative=normalized(folder/name)
    matches=[r['sha256'].upper() for r in ledger.get('input_hashes',[]) if normalized(r['path'])==relative]
    require(len(matches)==1,'Accepted native report hash missing: '+relative);return matches[0]

def inspect(repo,current,initial):
    repo=Path(repo).resolve();migration=repo/'Demos/UEPLyraIntegration/Migration'
    candidate_path=migration/'candidate_dispositions.json'
    candidates=verify_candidates(read(candidate_path),current,initial,repo)
    require(len([r for r in current['assets'] if r['version']=='0.13.0'])==57,'Original57 UI candidates required')
    specs=[
        dict(key='host-request-failure',ledger='225-host-session-native-invalid-request-error-ui-and-unbind.json',directory=RUNTIME+'20261023-host-session-failure/Native01',reports=['failure.json'],contract='host_session_failure_contract',marker='UEP_HOST_FAILURE',policies=['host_session_mixin.py'],assets=['UI/Menu/Experiences/W_HostSessionScreen'],errors=['LogCommonSession: Error: FinishSessionCreation(InternalFailure): HostSession passed an invalid request.']),
        dict(key='search-failure-and-retired-receiver',ledger='226-session-browser-native-error-recovery-and-pending-receiver-lifetime.json',directory=RUNTIME+'20261023-browser-search-failure/Native01',reports=['failure.json'],contract='session_browser_failure_contract',marker='UEP_BROWSER_FAILURE',policies=['session_browser_mixin.py'],assets=['UI/Menu/Experiences/W_SessionBrowserScreen']),
        dict(key='join-rejection-and-ui-retry',ledger='227-session-entry-native-duplicate-join-failure-cleanup-and-retry.json',directory=RUNTIME+'20261023-session-join-failure/Native01',reports=['host.json','BlueprintFallback.json','Python.json'],contract='session_join_failure_contract',marker='UEP_SESSION_JOIN_FAILURE',policies=['session_entry_mixin.py','session_browser_mixin.py'],assets=['UI/Menu/Experiences/W_SessionBrowserEntry','UI/Menu/Experiences/W_SessionBrowserScreen']),
        *[dict(key='replay-decline-'+profile,ledger='163-replay-browser-entry-native-recordings-and-current-item-playback.json',directory=RUNTIME+'20261021-replays/'+name,reports=['jump.json'],contract='replay_browser_contract',marker='UEP_REPLAY_BROWSER',policies=['replay_browser_mixin.py','replay_entry_mixin.py'],assets=['UI/Menu/Replays/W_ReplayBrowserScreen','UI/Menu/Replays/W_ReplayListEntry']) for profile,name in [('original','Playback03FallbackGeneratedID'),('python','Playback04Python')]],
        *[dict(key='represented-settings-cancel-'+profile,ledger='244-native-settings-cancel-action-dirty-rollback-and-reopen.json',directory=RUNTIME+'20261025-settings-cancel/'+name,reports=['failure.json'],contract='settings_cancel_action_contract',marker='UEP_SETTINGS_CANCEL',policies=['settings_screens_mixin.py','settings_editors_mixin.py','bound_action_mixin.py','menu_layers_mixin.py'],assets=['UI/Settings/W_LyraSettingScreen','UI/Settings/Editors/W_SettingsListEntry_Scalar','UI/Foundation/Widgets/BottomBar/W_BoundActionButton','UI/Hud/W_LyraGameMenu']) for profile,name in [('original','Original03'),('python','Python01')]],
    ]
    results=[];native_processes=0
    for spec in specs:
        ledger_path=repo/ACCEPTANCE/spec['ledger'];ledger=read(ledger_path);folder=Path(spec['directory']);record=ledger_record(ledger,spec['directory'])
        summary_path=repo/folder/'summary.json';require(sha(summary_path)==record['summary_sha256'].upper(),'Pinned native summary changed')
        original_summary=read(summary_path);summary=original_summary;correction=None
        if spec['key']=='host-request-failure':
            corrected=ledger['corrected_read_only_review'];path=repo/corrected['directory']/'summary.json'
            require(sha(path)==corrected['summary_sha256'].upper(),'Corrected host log review changed')
            summary=read(path)
            require(original_summary['status']=='failed' and original_summary['error']=='Exactly four declared native invalid-request errors required','Original rejected host summary must remain preserved')
            require(summary['original_outer_failure_preserved'] is True and summary['new_native_processes']==0 and summary['process']==original_summary['process'],'Read-only host correction must reuse the exact original process')
            correction=dict(path=normalized(path.relative_to(repo)),sha256=sha(path),original_failed_summary_preserved=True)
        native_processes+=process_gate(summary)
        raw=[];report_hashes=[]
        for name in spec['reports']:
            path=repo/folder/name;require(sha(path)==report_pin(ledger,record,folder,name),'Pinned native UI report changed: '+str(path))
            raw.append(read(path));report_hashes.append(dict(path=normalized(path.relative_to(repo)),sha256=sha(path)))
        module=importlib.import_module('uep_lyra_hud.'+spec['contract'])
        if spec['key']=='join-rejection-and-ui-retry':module.validate(repo/folder)
        else:
            for report in raw:module.validate(report)
        logs=[]
        for i,name in enumerate(spec['reports']):
            log_name=name.replace('.json','.log');path=repo/folder/log_name
            errors=[]
            if spec['key']=='host-request-failure':errors=['FinishSessionCreation(InternalFailure): HostSession passed an invalid request.']*4
            elif spec['key']=='search-failure-and-retired-receiver':errors=['SearchingPlayer is invalid']*2
            elif spec['key']=='join-rejection-and-ui-retry' and i>0:errors=['FinishJoinSession(Failed with Result: Join failed.)']
            log_gate(path.read_text(encoding='utf-8-sig'),spec['marker'],errors);logs.append(dict(path=normalized(path.relative_to(repo)),sha256=sha(path),declared_native_error_count=len(errors)))
        guards=[]
        for relative in [HUD+n for n in spec['policies']+[spec['contract']+'.py']]+['Demos/UEPLyraIntegration/Overlay/Content/'+name+'.uasset' for name in spec['assets']]:
            guards.append(dict(path=relative,**source_guard(repo/relative,original_summary['hashes'])))
        results.append(dict(obligation=spec['key'],ledger=normalized(ledger_path.relative_to(repo)),ledger_sha256=sha(ledger_path),directory=spec['directory'],summary_sha256=sha(summary_path),
            reports=report_hashes,logs=logs,current_source_and_asset_guards=guards,corrected_host_review=correction,native_runtime_reexecuted=False))
    return dict(schema_version=1,status='passed',criterion=REQUIREMENT,version='0.13.0',completion_proven=True,
        proof_scope='Original/Python native UI failure and cancellation paths,not only success:invalid hosting,bad-player search,pending receiver collection,duplicate join/recovery,replay decline and represented settings Cancel/rollback/reopen.',
        source_candidate_guard=dict(path='Demos/UEPLyraIntegration/Migration/candidate_dispositions.json',sha256=sha(candidate_path),**candidates),
        original_candidate_paths_versions_sha256=digest_bytes(json.dumps([(r['path'],r['version']) for r in initial['assets']],separators=(',',':')).encode()),
        verified_obligations=results,accepted_historical_native_processes=native_processes,new_native_processes=0,cpp_compile_executed=False,cook_package_executed=False,
        original_runtime_versions_retained=True,current_policy_or_assets_changed=False,all57_ui_candidates_accepted=False,full_version_acceptance=False,full_migration_acceptance_proven=False,
        limits=['Native errors are declared stimuli and exactly matched;every other Error/Traceback/Ensure/Fatal fails.',
            'Recorded native SDK/configurations remain historical;this review launches no new runtime and does not claim all paths refreshed on the newest SDK.',
            'NULL/local sessions,replay decline and owned settings rollback are covered;authenticated provider behavior,backend search cancellation,hardware/pixels/package and other original criteria remain unclaimed.',
            'The full original22 criteria and246 candidates remain;this accepts only the original failure/cancellation-testing condition.'])

def verify_documentation(document,current,initial,repo):
    require(document.get('schema_version')==1 and document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original UI criterion and native evidence required')
    expected=inspect(repo,current,initial);require(document==expected,'UI failure/cancellation review differs from current pinned evidence/source')
    return dict(status='passed',criterion=REQUIREMENT,verified_obligations=len(expected['verified_obligations']),accepted_historical_native_processes=expected['accepted_historical_native_processes'],new_native_processes=0,full_version_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);parser.add_argument('--original-inventory',required=True);parser.add_argument('--result',required=True);args=parser.parse_args()
    manifest=Path(args.manifest).resolve();result=inspect(manifest.parents[3],read(manifest),read(args.original_inventory))
    Path(args.result).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ('status','criterion','completion_proven','accepted_historical_native_processes','new_native_processes','full_migration_acceptance_proven')}))
