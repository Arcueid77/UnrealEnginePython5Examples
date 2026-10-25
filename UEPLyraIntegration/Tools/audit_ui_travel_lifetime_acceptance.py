"""Recheck the original CommonUI reopen/travel criterion from pinned native runs."""
import hashlib,json
from pathlib import Path
from audit_ui_failure_cancellation_acceptance import process_gate,log_gate,source_guard
from uep_lyra_hud.ui_travel_lifetime_contract import validate
REQUIREMENT='Repeated screen open/close and travel restore subscriptions and state.'
BASE='.build/LyraValidation/BlueprintPython/20261026-ui-travel-lifetime'
def require(value,message):
    if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def pair(reports):
    require([r['profile'] for r in reports]==['BlueprintFallback','Python'],'Both separate native profiles required')
    for report in reports:validate(report)
    fields=('origin','cycle','parent_focus','settings_focus','parent_selected_callbacks','parent_other_callbacks','back_selected_callbacks','back_other_callbacks','settings_closed','settings_focus_removed')
    values=[[tuple(row[k] for k in fields) for row in r['cases']] for r in reports]
    require(values[0]==values[1],'Original/Python native UI reopen checkpoints differ')
def verify_documentation(document,repo):
    repo=Path(repo).resolve()
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original UI lifetime criterion required')
    runs=document.get('native_runs',[])
    require([r.get('directory') for r in runs]==[BASE+'/Original01',BASE+'/Python01'],'Two exact native run records required')
    reports=[];frozen=0
    for row in runs:
        folder=repo/row['directory'];summary=folder/'summary.json';report=folder/'failure.json';log=folder/'failure.log'
        require(sha(summary)==row['summary_sha256'] and sha(report)==row['report_sha256'] and sha(log)==row['log_sha256'],'Pinned native lifetime report changed')
        native=read(summary);require(process_gate(native)==1,'One owned UI runtime per profile required')
        log_gate(log.read_text(encoding='utf-8-sig'),'UEP_UI_TRAVEL_LIFETIME');reports.append(read(report))
        # Original01 ran before adding the stricter world/report cross-check.
        # Preserve that exact old contract; execute the current gate on both raw
        # reports. Every production input and the observer itself stays frozen.
        for entry in native['hashes']:
            path=Path(entry['path'])
            if row['directory'].endswith('/Original01') and path.name=='ui_travel_lifetime_contract.py':
                archive=folder/'Inputs/ui_travel_lifetime_contract.py';require(sha(archive)==entry['sha256'],'Original native contract archive changed')
            else:source_guard(path,[entry])
            frozen+=1
    pair(reports)
    return dict(status='passed',criterion=REQUIREMENT,native_processes=2,settings_reopen_cycles=8,actual_confirmed_map_travels=2,current_semantic_gate_rechecked=True,frozen_native_input_records=frozen,
        original_runtime_contract_preserved=True,new_native_processes=0,all57_ui_behavior_accepted=False,full_version_acceptance=False)
