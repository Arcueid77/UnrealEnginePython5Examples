"""Recheck the original CommonUI reopen/travel criterion from pinned native runs."""
import ast,hashlib,json,subprocess
from pathlib import Path
from audit_ui_failure_cancellation_acceptance import process_gate,log_gate,source_guard
from uep_lyra_hud.ui_travel_lifetime_contract import validate
REQUIREMENT='Repeated screen open/close and travel restore subscriptions and state.'
BASE='.build/LyraValidation/BlueprintPython/20261026-ui-travel-lifetime'
STARTUP_BASE_COMMIT='3944cc0733f5149ee9f0e730ee1e08c8ebd21e39'
AI_FLAG='-UEPShooterAILifetimeResult='
SPAWNING_FLAG='-UEPSpawningDestroyedResult='
CP_FLAG='-UEPCPNetworkResult='
def require(value,message):
    if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def startup_selector_equivalent(before,after,arguments):
    require(not any(a.startswith((AI_FLAG,SPAWNING_FLAG,CP_FLAG)) for a in arguments),'Historical UI process enabled a new unrelated validation selector')
    old,new=ast.parse(before),ast.parse(after)
    functions=[n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='validation_module']
    require(len(functions)==1,'One startup validation selector required')
    expected=ast.parse("def validation_module(arguments):\n    if any(a.startswith('-UEPCPNetworkResult=') for a in arguments) and not any(a.startswith('-run=') for a in arguments):\n        return 'uep_lyra_weapons.cp_network_validation'\n    if any(a.startswith('-UEPSpawningDestroyedResult=') for a in arguments) and not any(a.startswith('-run=') for a in arguments):\n        return 'uep_lyra_weapons.spawning_destroyed_target_validation'\n    if any(a.startswith('-UEPShooterAILifetimeResult=') for a in arguments) and not any(a.startswith('-run=') for a in arguments):\n        return 'uep_lyra_world.shooter_ai_lifetime_validation'\n").body[0].body
    function=functions[0]
    shapes={ast.dump(n,include_attributes=False) for n in expected};removed=[]
    while function.body and ast.dump(function.body[0],include_attributes=False) in shapes:removed.append(ast.dump(function.body.pop(0),include_attributes=False))
    require(removed and len(set(removed))==len(removed) and ast.dump(expected[-1],include_attributes=False) in removed,'Only the exact reviewed opt-in branches may be added')
    require(ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False),'Existing startup behavior changed beyond the reviewed opt-in branches')

def startup_guard(repo,path,entry,arguments):
    relative='UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_hud/startup.py'
    before=subprocess.check_output(['git','show',STARTUP_BASE_COMMIT+':'+relative],cwd=repo/'Demos').decode('utf-8-sig')
    text=before.replace('\r\n','\n');variants={hashlib.sha256(bom+value.encode()).hexdigest().upper() for value in (text,text.replace('\n','\r\n')) for bom in (b'',b'\xef\xbb\xbf')}
    require(entry['sha256'] in variants,'Historical startup Git source does not match the frozen native input')
    startup_selector_equivalent(before,path.read_text(encoding='utf-8-sig'),arguments)

def spawning_null_guard_equivalent(before,after,arguments):
    from audit_candidate_dispositions import null_spawn_guard_only
    require('-UEPSpawningNullEffect' not in arguments and not any(a.startswith('-UEPSpawningDestroyedResult=') for a in arguments),'Historical UI run enabled the new unrelated spawning fixture')
    require(null_spawn_guard_only(ast.parse(before),ast.parse(after)),'Only the exact two null effect setters may differ from the historical UI input')

def spawning_policy_guard(repo,path,entry,arguments):
    relative='UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_weapons/spawning_cue_mixin.py'
    before=subprocess.check_output(['git','show','f74d5ff96ed3e69cff75e391b4927944717aaac8:'+relative],cwd=repo/'Demos').decode('utf-8-sig')
    text=before.replace('\r\n','\n');variants={hashlib.sha256(bom+value.encode()).hexdigest().upper() for value in (text,text.replace('\n','\r\n')) for bom in (b'',b'\xef\xbb\xbf')}
    require(entry['sha256'].upper() in variants,'Historical spawning source must match its frozen native UI input')
    spawning_null_guard_equivalent(before,path.read_text(encoding='utf-8-sig'),arguments)
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
    reports=[];frozen=0;spawning_fix=None
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
            else:
                try:source_guard(path,[entry])
                except ValueError:
                    if path.parts[-2:]==('uep_lyra_hud','startup.py'):startup_guard(repo,path,entry,native['process']['arguments'])
                    elif path.parts[-2:]==('uep_lyra_weapons','spawning_cue_mixin.py'):
                        spawning_policy_guard(repo,path,entry,native['process']['arguments'])
                        if spawning_fix is None:
                            from audit_spawning_spawn_result_fix import verify
                            spawning_fix=verify(repo,repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_weapons/spawning_cue_mixin.py')
                    else:raise
            frozen+=1
    pair(reports)
    return dict(status='passed',criterion=REQUIREMENT,native_processes=2,settings_reopen_cycles=8,actual_confirmed_map_travels=2,current_semantic_gate_rechecked=True,frozen_native_input_records=frozen,
        original_runtime_contract_preserved=True,new_native_processes=0,all57_ui_behavior_accepted=False,full_version_acceptance=False,
        exact_spawning_null_setter_guard_separately_native_verified=spawning_fix is not None)
