"""Check the original documented Mixin contract; do not certify an entire release."""
import re
from pathlib import Path

from audit_ability_lifetime_acceptance import generic_boundaries, native_log
from audit_ui_navigation_acceptance import read, sha

REQUIREMENT = ('A checked-in call/lifecycle matrix labels every path as tested supported, '
               'intentionally rejected, or bypass/unsupported, with reproducible fixtures.')
BASE = '.build/LyraValidation/BlueprintPython/20261027-call-lifecycle-matrix'
SDK = '96049A85163F7EBE98CDDBB324BDC7973F640E0CBC13CA758AA8499772F2044F'
CASES = ('signature-shared', 'callsite', 'experimental-body', 'named-outputs',
         'named-outputs-negative', 'inherited-selector', 'construction-forwarder',
         'soft-class-path', 'mixin-exception')
MARKERS = dict(zip(CASES, ('UEP_MIXIN_SIGNATURE_PASSED', 'UEP_MIXIN_CALLSITE_PASSED',
    'UEP_BLUEPRINT_SCRIPT_BODY_PASSED', 'UEP_MIXIN_NAMED_OUTPUT_PASSED',
    'UEP_MIXIN_NAMED_OUTPUT_PASSED', 'UEP_INHERITED_SELECTOR_PASSED',
    'UEP_CONSTRUCTION_FORWARDER_PASSED', 'UEP_SOFT_CLASS_PATH_PASSED',
    'UEP_MIXIN_EXCEPTION_PASSED')))
GROUPS = {
    'C01':'callsite', 'C02':'callsite', 'C03':'signature', 'C04':'third-person',
    'C05':'signature', 'C06':'inheritance', 'C07':'callsite', 'C08':'exception',
    'C09':'delegate', 'C10':'third-person', 'C11':'signature', 'C12':'signature',
    'C13':'signature', 'C14':'rejection', 'C15':'rpc-gateway', 'C16':'rejection',
    'C17':'source-boundary', 'C18':'experimental', 'C19':'named-outputs',
    'C20':'named-outputs', 'C21':'construction-forwarder', 'L01':'pie', 'L02':'pie',
    'L03':'pie', 'L04':'third-person', 'L05':'inheritance', 'L06':'weapon',
    'L07':'weapon', 'L08':'pie', 'L09':'follow', 'L10':'follow',
    'L11':'travel', 'L12':'source-boundary'}
TESTS = 'Validation/UEP58Host/Tests/'
LYRA = 'Demos/UEPLyraIntegration/'
FIXTURES = {
    'callsite':[TESTS+'mixin_callsite_validation.py'],
    'signature':[TESTS+'mixin_signature_validation.py'],
    'exception':[TESTS+'mixin_exception_validation.py'],
    'delegate':[TESTS+'delegate_broadcast_validation.py'],
    'rejection':[TESTS+'mixin_rejection_validation.py', TESTS+'mixin_rejection_contract.py'],
    'experimental':[TESTS+'blueprint_script_body_validation.py'],
    'named-outputs':[TESTS+'mixin_named_output_validation.py'],
    'construction-forwarder':[TESTS+'mixin_construction_forwarder_validation.py'],
    'pie':[TESTS+'mixin_pie_validation.py', 'Validation/Run-UEP58FocusedLifecycleValidation.ps1'],
    'third-person':['Demos/UEPPythonThirdPerson/Mixin/Content/Scripts/uep_third_person_mixin/'+n+'.py'
                    for n in ('interface_probe','smoke','character_mixin')],
    'inheritance':[LYRA+'Tools/generate_mixin_inheritance_probe.py',
                   LYRA+'Overlay/Content/Scripts/uep_lyra_abilities/dash_selector_probe_policy.py'],
    'rpc-gateway':[LYRA+'Tools/generate_dash_rpc_input_assets.py',
                   LYRA+'Overlay/Content/Scripts/uep_lyra_abilities/dash_rpc_input_contract.py'],
    'weapon':[LYRA+'Overlay/Content/Scripts/uep_lyra_hud/weapon_validation.py',
              'Validation/Run-UEP58PackagedWeaponHUDValidation.ps1', 'Validation/LyraHUDContracts.ps1'],
    'follow':[LYRA+'Overlay/Content/Scripts/uep_lyra_world/'+n+'.py'
              for n in ('explorer_follow_validation','explorer_follow_contract')],
    'travel':[LYRA+'Overlay/Content/Scripts/uep_lyra_weapon_protocol.py',
              'Validation/Run-UEP58FocusedNetworkValidation.ps1'],
    'source-boundary':['Source/UnrealEnginePython/Private/UEPyMixin.cpp',
                       'Source/UnrealEnginePython/Private/PythonFunction.cpp',
                       TESTS+'mixin_callsite_validation.py']}
REJECTED = {'C11','C12','C13','C14','C16','C20'}
UNSUPPORTED = {'C17','C18','L12'}


def require(value, message):
    if not value:
        raise ValueError(message)


def matrix_rows(text):
    rows = []
    section = None
    for line in text.splitlines():
        if line.startswith('## '):
            section = line[3:] if line[3:] in ('Calls','Lifecycle') else None
        if not section or not line.startswith('| '):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if cells[0] in ('ID','---'):
            continue
        require(len(cells) == 4, 'One classification and reproducer column per path required')
        identity, entry, classification, evidence = cells
        require(identity in GROUPS and identity.startswith('C' if section=='Calls' else 'L') and
                len(entry) > 10, 'Unknown or empty contract path')
        category = ('Intentionally rejected' if identity in REJECTED else
                    'Bypass/unsupported' if identity in UNSUPPORTED else 'Tested supported')
        require(classification.startswith(category), 'Contract category changed: '+identity)
        require('`'+GROUPS[identity]+'`' in evidence, 'Path lacks its reproducible proof group: '+identity)
        rows.append(dict(id=identity, entry=entry, classification=classification,
                         category=category, proof_group=GROUPS[identity]))
    require([r['id'] for r in rows] == list(GROUPS), 'Every original call/lifecycle path exactly once and in order')
    for boundary in ('No sparse-delegate coverage claim', 'No RPC invocation/network test is implied',
                     'not a universal runtime interception claim', 'not a synchronous-GC guarantee',
                     'Restart for generated type/signature changes'):
        require(boundary in text, 'Missing unsupported/deferred contract boundary: '+boundary)
    return rows


def log_gate(name, text, exit_code):
    expected_error = name in ('named-outputs-negative','mixin-exception')
    require(exit_code in ((0,1) if expected_error else (0,)), 'Unexpected native fixture exit')
    require(not re.search(r'Fatal error:|Assertion failed|Unhandled Exception|Ensure condition failed', text),
            'Unexpected crash/ensure in native fixture')
    require(re.search(MARKERS[name]+r'.*Goodbye Python.*Log file closed', text, re.S),
            'Native fixture did not reach its marker and normal shutdown')
    errors = [line for line in text.splitlines() if re.search(r'Log\w+:\s*Error:', line)]
    if name == 'mixin-exception':
        require('LogPython: Error: UEP_EXPECTED_MIXIN_EXCEPTION' in text, 'Expected traceback absent')
        allowed = (r'LogPython:\s*Error:\s*(UEP_EXPECTED_MIXIN_EXCEPTION|'
                   r'RuntimeError: UEP_EXPECTED_MIXIN_EXCEPTION|Traceback \(most recent call last\):|'
                   r'File ".*mixin_exception_validation\.py", line \d+, in BroadcastSignal)')
        require(all(re.search(allowed, line) for line in errors), 'Unexpected exception diagnostic')
    elif name == 'named-outputs-negative':
        reasons = ('named mixin outputs require a dictionary','named mixin output omitted Command.Accepted',
                   'named mixin output dictionary has unexpected keys')
        require(all(reason in text for reason in reasons), 'Missing actual named-output rejections')
        require(all(re.search(r'LogPython:\s*Error:\s*(Invalid named outputs for mixin function Command|'+
                             '|'.join(re.escape(r) for r in reasons)+r')\s*$', line) for line in errors),
                'Unexpected rejection diagnostic')
    else:
        require(not errors and 'Traceback' not in text, 'Unexpected native error')


def case_gate(name, report):
    require(report.get('status') == 'passed', 'Native fixture report failed')
    if name == 'signature-shared':
        require(report['same_class'] and len(report['supported']) == 7 and
                [r['profile'] for r in report['rejected']] == ['BadSignature','NonConstOutputs','StaticFunction'],
                'Supported/rejected signature proof incomplete')
    elif name == 'callsite':
        value = report['evidence']
        require(all(value[k] is True for k in ('caller_compiled_before_registration',
                'zero_parameter_native_fallback','same_class','restoration_passed')), 'Caller boundary missing')
        expected = [('original',[(1,0,1),(1,0,1)]), ('mixed',[(1,1,2),(2,0,1)]),
                    ('mixed_again',[(1,2,2),(3,0,1)]), ('profiles_swapped',[(2,2,1),(3,1,2)]),
                    ('restored',[(3,2,1),(4,1,1)])]
        actual = [(r['name'],[(t['blueprint_calls'],t['python_calls'],t['last_route']) for t in r['targets']])
                  for r in value['phases']]
        require(actual == expected, 'Original/Python call counts or restoration differ')
    elif name == 'experimental-body':
        require(all(report[k] for k in ('precompiled_caller','class_identity_preserved','no_blueprint_fallthrough')) and
                [report[k] for k in ('output_parameters','repeated_output_parameters','restored_outputs')] ==
                [dict(Result=33,Accepted=False),dict(Result=-6,Accepted=False),dict(Result=13,Accepted=True)],
                'Separate experimental body proof incomplete')
    elif name == 'named-outputs':
        require(report['same_class'] and len(set(report['cases'])) == 7 and not report['full_acceptance'],
                'Named-output positive fixture incomplete')
    elif name == 'named-outputs-negative':
        require(report['cases'] == ['wrong-dictionary-type','missing-second-output','extra-key-after-conversion',
                'valid-profile-recovery','original-restoration-after-rejection'] and not report['full_acceptance'],
                'Named-output rejection/recovery fixture incomplete')
    elif name == 'inherited-selector':
        require(all(report[k] for k in ('inherited_selector_reused','parent_unchanged','same_class_independent_instances')),
                'Inherited selector altered parent/instance ownership')
    elif name == 'construction-forwarder':
        require(all(report[k] for k in ('explicit_parent_call','virtual_helper','same_class','no_bp_fallthrough',
                'original_body_preserved','profile_round_trip','restore')) and not report['related_child_router_used'] and
                report['construction_nodes'] == 2 and report['body_nodes'] == 4, 'Construction forwarding boundary differs')
    elif name == 'soft-class-path':
        require(all(report[k] for k in ('no_load','empty_null','loaded_class_compatible')) and len(report['rejected']) == 5,
                'Lazy class path unexpectedly loaded or accepted malformed input')
    elif name == 'mixin-exception':
        require(report['no_original_after_python_exception'] and report['recovered'] and
                report['native_signals'] == [11,33,44], 'Exception caused original fallthrough or lost recovery')
    else:
        raise ValueError('Unknown focused fixture')


def pie_gate(report):
    require(report['status'] == 'passed' and report['same_editor_process'] is True and
            len(report['sessions']) == 3 and report['error'] is None, 'Three actual same-Editor PIE sessions required')
    for index, session in enumerate(report['sessions'],1):
        require(session['cycle'] == index and all(session[k] is True for k in
                ('placed_and_spawned','construction','native_gc_collected','router_restored')) and
                session['closed_scopes'] == 2 and session['begin_end_counts'] == [2,2],
                'PIE construction/cleanup/GC/router restoration incomplete')


def inspect(repo, current, initial):
    repo = Path(repo); migration = repo/'Demos/UEPLyraIntegration/Migration'
    require([(r['path'],r['version']) for r in current['assets']] ==
            [(r['path'],r['version']) for r in initial['assets']] and len(current['assets']) == 246,
            'Original migration scope changed')
    document = repo/'docs/Mixin_Call_Lifecycle_Matrix.md'
    rows = matrix_rows(document.read_text(encoding='utf-8-sig'))
    fixtures = [dict(group=group,path=path,sha256=sha(repo/path))
                for group, paths in FIXTURES.items() for path in paths]
    generic = generic_boundaries(repo,migration)  # Only the three already accepted affected processes.
    folder = repo/BASE/'MissingCalls01'; summary = read(folder/'summary.json')
    require(summary['status'] == 'passed' and summary['error'] is None and
            tuple(summary['selected_test_names']) == CASES and not summary['full_matrix_executed'] and
            not summary['cpp_compile_executed'] and not summary['cook_package_executed'] and
            tuple(t['name'] for t in summary['tests']) == CASES, 'Exact nine missing current-SDK cases required')
    for item in summary['input_hashes']:
        require(sha(item['path']) == item['sha256'].upper(), 'Frozen current call input changed')
    require({r['sha256'].upper() for r in summary['input_hashes']
             if Path(r['path']).name == 'UnrealEditor-UnrealEnginePython.dll'} == {SDK},
            'Current call cases used a different SDK DLL')
    cases = []
    for test in summary['tests']:
        process = test['process']; path = Path(test['report']); name = test['name']
        require(test['status'] == 'passed' and process['pid'] > 0 and '-run=Py' in process['arguments'],
                'Actual completed Py commandlet required')
        require(('-DisablePython' not in process['arguments']) is (name == 'signature-shared'),
                'Shared/standalone interpreter mode differs')
        case_gate(name,read(path)); log_gate(name,path.with_suffix('.log').read_text(encoding='utf-8-sig'),process['exit_code'])
        cases.append(dict(name=name,pid=process['pid'],exit_code=process['exit_code'],
                          report_sha256=sha(path),log_sha256=sha(path.with_suffix('.log'))))
    pie_folder = repo/BASE/'PIE01'; pie = read(pie_folder/'summary.json')
    require(pie['status'] == 'passed' and pie['error'] is None and pie['process']['pid'] > 0 and
            pie['process']['exit_code'] == 0 and not pie['cpp_compile_executed'] and not pie['cook_package_executed'],
            'Actual current-SDK lifecycle process did not finish')
    for item in pie['source_hashes']+pie['binary_hashes']:
        require(sha(item['path']) == item['sha256'].upper(), 'Frozen PIE input changed')
    require({r['sha256'].upper() for r in pie['binary_hashes']
             if Path(r['path']).name == 'UnrealEditor-UnrealEnginePython.dll'} == {SDK},
            'PIE used a different SDK DLL')
    pie_gate(read(pie_folder/'pie.json'))
    native_log(pie_folder/'pie.log')
    text = (pie_folder/'pie.log').read_text(encoding='utf-8-sig')
    require(re.search(r'UEP_MIXIN_PIE_PASSED.*Preparing to exit.*UEP_MIXIN_PIE_SHUTDOWN_PASSED.*Goodbye Python.*Log file closed',text,re.S)
            and 'Attaching UnrealEnginePython to the existing CPython interpreter' in text,
            'Shared interpreter PIE exit ordering differs')
    # These supplement the contract, with their original configurations explicitly retained.
    historical = []
    for batch, name in ((217,'NativeFixed05'),(62,'Assets06'),(63,'Network02'),
                        (211,'PackagedWeaponHUD01'),(231,'Python03DeferredGC')):
        path, = (migration/'Acceptance').glob(f'{batch:02}-*.json'); ledger = read(path)
        record, = [r for r in ledger['runs'] if Path(r['directory']).name == name]
        summary_path = repo/record['directory']/'summary.json'
        require(sha(summary_path) == record['summary_sha256'] and read(summary_path)['status'] == 'passed',
                'Historical bounded matrix evidence changed')
        historical.append(dict(batch=batch,ledger=path.relative_to(repo).as_posix(),ledger_sha256=sha(path),
            directory=record['directory'],summary_sha256=sha(summary_path),
            current_sdk_equivalence_claimed=False,new_native_execution_claimed=False))
    path = migration/'Acceptance/265-original-all-small-batch-comparisons-and-python-business-ownership.json'
    record, = [r for r in read(path)['review']['native_comparison_runs']
               if r['directory'].endswith('20261016-device-color/CombinedNetwork01')]
    travel_folder = repo/record['directory']
    require(sha(travel_folder/'summary.json') == record['summary_sha256'], 'Accepted travel capture changed')
    for peer in record['native_peers']:
        require(peer['exit_code'] == 0 and sha(travel_folder/(peer['peer']+'.json')) == peer['report_sha256'] and
                sha(travel_folder/(peer['peer']+'.log')) == peer['log_sha256'], 'Accepted native owner/travel output changed')
    historical.append(dict(batch=265,ledger=path.relative_to(repo).as_posix(),ledger_sha256=sha(path),
        directory=record['directory'],summary_sha256=record['summary_sha256'],
        pinned_native_peers=record['native_peers'],current_sdk_equivalence_claimed=False,new_native_execution_claimed=False))
    return dict(status='passed',criterion=REQUIREMENT,completion_proven=True,
        matrix_path=document.relative_to(repo).as_posix(),matrix_sha256=sha(document),paths=rows,
        call_paths=21,lifecycle_paths=12,tested_supported_paths=24,intentionally_rejected_paths=6,
        bypass_unsupported_paths=3,reproducible_source_fixtures=fixtures,current_generic_boundary_runs=generic,
        missing_current_call_run=dict(directory=folder.relative_to(repo).as_posix(),summary_sha256=sha(folder/'summary.json'),
            selected_cases=cases,frozen_input_records=len(summary['input_hashes'])),
        current_pie_run=dict(directory=pie_folder.relative_to(repo).as_posix(),summary_sha256=sha(pie_folder/'summary.json'),
            pid=pie['process']['pid'],exit_code=0,report_sha256=sha(pie_folder/'pie.json'),log_sha256=sha(pie_folder/'pie.log'),
            same_editor_sessions=3,closed_scopes=6),historical_bounded_references=historical,
        current_generic_call_cases=11,new_native_processes=10,current_editor_sdk_sha256=SDK,cpp_compile_executed=False,
        cook_package_executed=False,full_regression_executed=False,full_version_acceptance=False,
        full_migration_acceptance_proven=False,
        limits=['Class-map bypasses and arbitrary recompile/state migration are unsupported contracts, not tested universal interception.',
                'The experimental body API is tested separately and excluded from production Mixin support.',
                'Historical Third Person, Dash, packaged reload and Explorer captures retain their own SDK/configuration scope.',
                'This accepts the checked-in classification/reproducer criterion only; the other 0.9 criteria require separate acceptance.'])


def verify_documentation(document,current,initial,repo):
    require(document.get('criterion') == REQUIREMENT and document.get('completion_proven') is True,
            'Exact original call/lifecycle matrix requirement required')
    expected = inspect(repo,current,initial)
    require(document.get('review') == expected, 'Recorded call/lifecycle matrix proof differs')
    return {k:expected[k] for k in ('status','criterion','call_paths','lifecycle_paths',
        'tested_supported_paths','intentionally_rejected_paths','bypass_unsupported_paths','current_generic_call_cases')}
