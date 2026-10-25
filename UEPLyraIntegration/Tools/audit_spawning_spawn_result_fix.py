"""Verify the three current native boundaries for the private null-result guard."""
import hashlib,importlib,json,re,sys
from pathlib import Path
ROOT='.build/LyraValidation/BlueprintPython/20261026-playable-startup'
SPECS=(('SpawningNull01GateReview','SpawningNull01','spawning_null_effect_contract','UEP_SPAWNING_NULL_EFFECT'),('SpawningRendered01','SpawningRendered01','spawning_cue_contract','UEP_SPAWNING_CUE'),('SpawningDestroyed01','SpawningDestroyed01','spawning_destroyed_target_contract','UEP_SPAWNING_DESTROYED_TARGET'))

def require(value,message):
    if not value:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def driver_cli_only(before,after):
    expected=before.replace("'-X','utf8',$contract,'--report'","'-X','utf8','-m',\"uep_lyra_weapons.$contractName\",'--report'")
    expected=expected.replace("'Native Spawning destroyed-target semantic gate'","'Native Spawning result semantic gate'")
    require(expected!=before and expected==after,'Only the independent Python CLI invocation may differ from the archived native driver')

def verify(repo,path):
    repo=Path(repo).resolve();path=Path(path).resolve();root=repo/ROOT;proofs=[]
    scripts=str(repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts')
    if scripts not in sys.path:sys.path.insert(0,scripts)
    for summary_dir,native_dir,contract,marker in SPECS:
        folder=root/native_dir;summary_path=root/summary_dir/'summary.json';summary=read(summary_path)
        require(summary['status']=='passed' and summary['error'] is None and summary['process']['exit_code']==summary['external_gate']['exit_code']==0,'Current native spawning boundary failed')
        require(not summary['cpp_compile_executed'] and not summary['cook_package_executed'],'The spawning guard must reuse the accepted build')
        archives={}
        if summary_dir!=native_dir:
            raw=read(folder/'summary.json');require(raw['status']=='failed' and raw['process']==summary['process'] and summary['new_native_processes']==0 and summary['independent_review_only'],'Read-only gate repair changed/restarted its native process')
            require(sha(folder/'summary.json')==summary['original_failed_summary_sha256'] and sha(folder/'failure.json')==summary['raw_report_sha256'] and sha(folder/'failure.log')==summary['raw_log_sha256'],'Original null-run failure/report/log changed')
            archive=summary['source_archive'];require(sha(archive['archive_path'])==archive['sha256'],'Original native driver archive changed')
            driver_cli_only(Path(archive['archive_path']).read_text(encoding='utf-8-sig'),Path(archive['original_path']).read_text(encoding='utf-8-sig'))
            archives[Path(archive['original_path']).resolve()]=Path(archive['archive_path'])
        source_records=[r for r in summary['hashes'] if Path(r['path']).name==path.name and Path(r['path']).resolve()==path]
        require(source_records and {r['sha256'].upper() for r in source_records}=={sha(path)},'Changed spawning policy was not frozen by its native boundary')
        for row in summary['hashes']:
            current=Path(row['path']);current=archives.get(current.resolve(),current)
            require(sha(current)==row['sha256'].upper(),'Native spawning frozen input changed: '+str(current))
        report=read(folder/'failure.json');module=importlib.import_module('uep_lyra_weapons.'+contract);gate=module.validate(report)
        log=(folder/'failure.log').read_text(encoding='utf-8-sig')
        require(not re.search(r'Log\w+:\s*Error:',log) and not any(n in log for n in ('Traceback','Ensure condition failed','Fatal error')),'Unexpected native spawning diagnostic')
        needles=(marker+'_DIFFERENTIAL_PASSED','Goodbye Python',marker+'_SHUTDOWN_PASSED','Log file closed');require(all(n in log for n in needles),'Native spawning completion markers missing')
        positions=[log.index(n) if n!='Log file closed' else log.rindex(n) for n in needles];require(positions==sorted(positions) and len(set(positions))==4,'Native spawning teardown order differs')
        proofs.append(dict(directory=str((root/summary_dir).relative_to(repo)),native_directory=str(folder.relative_to(repo)),summary_sha256=sha(summary_path),report_sha256=sha(folder/'failure.json'),log_sha256=sha(folder/'failure.log'),semantic_gate=gate,
            native_pid=summary['process']['pid'],exit_code=0,original_null_setter_warnings=len(re.findall(r'Accessed None[^\r\n]*SpawnSystemAttached',log))))
    require(proofs[0]['semantic_gate']['native_null_results']==4 and proofs[1]['semantic_gate']['native_timelines']==8 and proofs[2]['semantic_gate']['native_target_destructions']==4,'Null,normal and destroyed-target native proof incomplete')
    return dict(status='passed',ledger='253-spawning-null-result-guard-and-current-startup-validation.json',sha256=sha(path),public_declarations_unchanged=True,native_profile_methods=8,native_runs=proofs,native_processes=3,cpp_compile_executed=False,cook_package_executed=False,full_acceptance=False)
