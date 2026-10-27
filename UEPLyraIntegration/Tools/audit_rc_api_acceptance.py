"""Check the bounded original API freeze and retain explicit native-game findings."""
from pathlib import Path
import re
import subprocess

from audit_candidate_matrix_acceptance import matrix_gate
from audit_reload_cleanup_acceptance import require
from audit_ui_navigation_acceptance import read,sha

REQUIREMENT='The supported API inventory and migration/deprecation rules are ready for RC freeze, with no known release-blocking correctness defects.'
BASELINE='e1199d2b02937bbddb947d660916a2c5c6b55464'
CAPABILITIES=('Interpreter','UObject reflection','Lazy soft-class input','Dynamic types','Production Mixin',
    'Delegate / Enhanced Input lifetime','Runtime subscription scope','Actor / World / exit','World lookup convenience',
    'Editor / asset / Slate helpers','Construction extraction authoring','Experimental Blueprint body scripting')
TABLES=('unreal_engine_methods','ue_PyUObject_methods')


def method_tables(source):
    result={}
    for name in TABLES:
        matches=re.findall(r'static\s+PyMethodDef\s+'+name+r'\s*\[\s*\]\s*=\s*\{(.*?)\n\s*\};',source,re.S)
        require(len(matches)==1,'Exactly one method registration table required: '+name)
        body=matches[0]
        entries=re.findall(r'\{\s*"([^"\n]+)"\s*,\s*([^,\n]+)\s*,\s*([^,\n]+)\s*,',body)
        require(len(entries)==len(re.findall(r'\{\s*"',body)),'Unparsed public registration entry')
        require(len({r[0] for r in entries})==len(entries),'Duplicate public registration name')
        result[name]=[(n,re.sub(r'\s+','',function),re.sub(r'\s+','',flags)) for n,function,flags in entries]
    return result


def compare_tables(before,after):
    old=method_tables(before);new=method_tables(after);result={}
    for name in TABLES:
        a={r[0]:r[1:] for r in old[name]};b={r[0]:r[1:] for r in new[name]}
        removed=sorted(a.keys()-b.keys());added=sorted(b.keys()-a.keys())
        changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k])
        require(not(removed or added or changed),'Public method registration compatibility changed: '+name)
        result[name]=dict(baseline=len(a),current=len(b),removed=removed,added=added,changed_function_or_flags=changed)
    return result


def freeze_gate(review):
    require(review['candidate_matrix_accepted'] is True and review['other_original_009_criteria_accepted']==6,
            'All other original0.9 criteria must be accepted before freeze')
    require(review['supported_capabilities']==list(CAPABILITIES),'Supported inventory changed without explicit review')
    require(review['registration_counts']==[213,462],'Public registration table coverage differs')
    require(review['known_release_blocking_api_defects']==[],'A known release-blocking API defect prevents freeze')
    require(review['sdk_bootstrap_fix_verified'] is True and review['isolated_lyra_guard_required'] is True and
            review['official_lyra_issue_retained'] is True and review['original_netshooter_native_discrepancy_retained'] is True,
            'Known correctness findings need explicit evidence and disposition')


def inspect(repo,current,initial):
    repo=Path(repo);m=repo/'Demos/UEPLyraIntegration/Migration';root=repo/'.build/LyraValidation/BlueprintPython'
    require([(r['path'],r['version']) for r in current['assets']]==[(r['path'],r['version']) for r in initial['assets']],
            'Original candidate inventory changed')
    baseline=read(root/'20261028-candidate-matrix/acceptance-final.json')
    others=[r for r in baseline['requirements'] if r['version']=='0.9.0' and r['text']!=REQUIREMENT]
    require(len(others)==6 and all(r['completion_proven'] for r in others),'Other original0.9 checks remain open')
    candidate_path,=(m/'Acceptance').glob('273-*.json');candidate=read(candidate_path)
    require(candidate['completion_proven'] is True,'Original candidate matrix not accepted');matrix_gate(candidate['review']['components'])
    source=repo/'Source/UnrealEnginePython/Private/UEPyModule.cpp'
    old=subprocess.check_output(['git','show',BASELINE+':Source/UnrealEnginePython/Private/UEPyModule.cpp'],cwd=repo).decode('utf-8-sig')
    tables=compare_tables(old,source.read_text(encoding='utf-8-sig'))
    inventory=repo/'docs/Supported_API_Inventory.md';text=inventory.read_text(encoding='utf-8-sig')
    capabilities=[line.split('|')[1].strip() for line in text.splitlines() if line.startswith('| ')][2:]
    guard_path=root/'20261026-widget-actor-lifetime/preflight.json'
    for row in read(guard_path)['binary_source_guards']:require(sha(row['path'])==row['sha256'].upper(),'Current native dependency changed')
    sdk_path=root/'20261023-pawn-sdk-causality/SDKBuild01/summary.json';sdk=read(sdk_path)
    sdk_ledger,=(m/'Acceptance').glob('236-*.json');sdk_record=read(sdk_ledger)
    pinned=[r for r in sdk_record['input_hashes'] if r['path'].endswith('SDKBuild01/summary.json')]
    require(len(pinned)==1 and sha(sdk_path)==pinned[0]['sha256'].upper() and sdk['process']['exit_code']==0,
            'Pinned SDK236 build missing')
    for row in sdk['source_hashes']+sdk['binary_after']:require(sha(row['path'])==row['sha256'].upper(),'SDK236 current input changed')
    issue=current['melee_two_owner_damage_pilot']['replica_readiness_issue'];follow=issue['isolated_native_guard_followup']
    require(follow['stage_native_added_lines']==8 and follow['guarded_waits']==12 and follow['canonical_ready_empty_bindings_observed']==0 and
            follow['authority_interactions']==40 and follow['replicated_viewer_checks']==80 and follow['official_source_unchanged'],
            'Approved isolated native guard disposition differs')
    native_ledger,=(m/'Acceptance').glob('246-*.json')
    discrepancy,=(m/'Acceptance').glob('97-*.json')
    dispositions=read(m/'candidate_dispositions.json')
    retained=[r for r in dispositions['candidates'] if r['asset']=='/ShooterCore/Weapons/NetShooter_PROTO/B_NetShooter.B_NetShooter']
    require(len(retained)==1 and any(discrepancy.name in s for s in retained[0]['explicit_retention_reasons']),
            'Original native NetShooter discrepancy must remain explicit')
    findings=dict(candidate_matrix_accepted=True,other_original_009_criteria_accepted=6,supported_capabilities=capabilities,
        registration_counts=[tables[n]['current'] for n in TABLES],known_release_blocking_api_defects=[],sdk_bootstrap_fix_verified=True,
        isolated_lyra_guard_required=True,official_lyra_issue_retained=follow['official_source_issue_remains_recorded'],
        original_netshooter_native_discrepancy_retained=True)
    freeze_gate(findings)
    docs=[inventory,repo/'docs/RC_API_Review_0.9.md',repo/'docs/Mixin_Call_Lifecycle_Matrix.md']
    return dict(status='passed',criterion=REQUIREMENT,completion_proven=True,scope='UE5.8 CPython3.11 Win64 Development supported API inventory',
        findings=findings,source_table_comparison=dict(baseline_core_commit=BASELINE,source_sha256=sha(source),tables=tables,
            all_legacy_wrapper_or_abi_certification=False),
        reviewed_documents=[dict(path=p.relative_to(repo).as_posix(),sha256=sha(p)) for p in docs],
        evidence_ledgers=[dict(path=p.relative_to(repo).as_posix(),sha256=sha(p)) for p in (candidate_path,sdk_ledger,native_ledger,discrepancy)],
        native_dependency_guard_sha256=sha(guard_path),new_native_processes=0,cpp_compile_executed=False,cook_package_executed=False,
        full_migration_regression_executed=False,full_migration_acceptance_proven=False,rc_tag_or_release_created=False,
        limits=['Source registration compatibility checks names,function expressions and flags only;runtime coverage retains its individual fixture boundaries.',
            'No known release-blocking defect is a scoped review of the supported API after explicit findings disposition;unknown defects and every legacy wrapper are not certified.',
            'The isolated user-approved Hero guard is required for Lyra acceptance. Official Lyra remains unchanged and its original finding stays open.',
            'Original0.11 NetShooter native baseline discrepancy remains explicit;full0.14 Experience and publication gates stay separate.'])


def verify_documentation(document,current,initial,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original RC API freeze requirement required')
    expected=inspect(repo,current,initial);require(document.get('review')==expected,'Recorded RC review differs from current evidence')
    return {k:expected[k] for k in ('status','criterion','scope','new_native_processes','rc_tag_or_release_created')}
