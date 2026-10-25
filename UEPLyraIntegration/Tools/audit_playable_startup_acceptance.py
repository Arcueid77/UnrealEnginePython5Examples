"""Verify the original normal-startup/explicit-weapon-probe exit boundary."""
import ast,hashlib,json,re
from pathlib import Path
from audit_ui_failure_cancellation_acceptance import log_gate

REQUIREMENT='Normal playable startup does not auto-run validation or request exit; explicitly enabled test modes retain bounded timeouts and cleanup evidence. Focused rendered weapon mode exits cleanly; the no-test-flag Lyra observation is bounded and stopped only by its owning test driver, not by a probe.'
BASE='.build/LyraValidation/BlueprintPython/20261026-playable-startup/Current02'
RECORD='Demos/UEPLyraIntegration/Migration/Acceptance/253-spawning-null-result-guard-and-current-startup-validation.json'
GATE='.build/LyraValidation/BlueprintPython/20261026-startup-acceptance/WeaponReportGate01'

def require(value,message):
    if not value:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def needs_test_flag(node,aliases=()):
    if isinstance(node,ast.BoolOp):
        values=[needs_test_flag(v,aliases) for v in node.values]
        return any(values) if isinstance(node.op,ast.And) else all(values)
    if isinstance(node,ast.Call):
        if isinstance(node.func,ast.Name) and node.func.id=='any' and len(node.args)==1 and isinstance(node.args[0],ast.GeneratorExp):
            generator=node.args[0]
            return len(generator.generators)==1 and isinstance(generator.generators[0].iter,ast.Name) and generator.generators[0].iter.id=='arguments' and isinstance(generator.generators[0].target,ast.Name) and needs_test_flag(generator.elt,(generator.generators[0].target.id,))
        if isinstance(node.func,ast.Attribute) and node.func.attr=='startswith' and node.args:
            arg=node.args[0];values=arg.elts if isinstance(arg,ast.Tuple) else [arg]
            return isinstance(node.func.value,ast.Name) and node.func.value.id in aliases and all(isinstance(v,ast.Constant) and isinstance(v.value,str) and v.value.startswith('-UEP') for v in values)
    return isinstance(node,ast.Compare) and len(node.ops)==1 and isinstance(node.ops[0],ast.In) and isinstance(node.left,ast.Constant) and isinstance(node.left.value,str) and node.left.value.startswith('-UEP') and len(node.comparators)==1 and isinstance(node.comparators[0],ast.Name) and node.comparators[0].id=='arguments'

def selector_catalogue(source):
    tree=ast.parse(source);functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validation_module']
    require(len(functions)==1 and all(n in functions or isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str) for n in tree.body),'Startup selector may only define its pure routing function')
    modules=[]
    def returned(value,guarded):
        if isinstance(value,ast.IfExp):
            returned(value.body,guarded or needs_test_flag(value.test));returned(value.orelse,guarded);return
        require(isinstance(value,ast.Constant),'Startup return must be an explicit module or None')
        if value.value is not None:
            require(guarded and isinstance(value.value,str) and value.value.startswith('uep_'),'A validation module can be selected without an explicit UEP flag')
            modules.append(value.value)
    def visit(nodes,guarded=False):
        for node in nodes:
            if isinstance(node,ast.If):visit(node.body,guarded or needs_test_flag(node.test));visit(node.orelse,guarded)
            elif isinstance(node,ast.Return):returned(node.value,guarded)
            elif not(isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)):raise ValueError('Unreviewed executable statement in startup selector')
    visit(functions[0].body);namespace={};exec(compile(tree,'startup-selector','exec'),namespace);select=namespace['validation_module']
    flags=sorted({n.value for n in ast.walk(functions[0]) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('-UEP')})
    rows=[]
    for flag in flags:
        arg=flag+'result.json' if flag.endswith('=') else flag
        rows.append(dict(flag=flag,single_flag_selection=select([arg]),raw_selector_with_commandlet_flag=select(['-run=Py',arg]),effective_commandlet_selection=None))
    for args in ([],['LyraStarterGame.uproject','-game'],['LyraStarterGame.uproject','-server','-NullRHI'],['-culture=en','-unattended']):require(select(args) is None,'Normal startup selected validation')
    return dict(explicit_flag_literals=rows,returned_module_count=len(set(modules)),all_non_null_returns_require_explicit_test_flag=True),select

def site_guard(source):
    expected='''import sys
import importlib
sys.dont_write_bytecode = True
import unreal_engine as ue
ue.log("UEP_LYRA_SCRIPT_LOADED")
is_commandlet = any(argument.lower().startswith("-run=") for argument in sys.argv)
if is_commandlet:
    ue.log("UEP_LYRA_COMMANDLET_BOOTSTRAP_SKIPPED")
else:
    from uep_lyra_hud import bootstrap
    from uep_lyra_hud.startup import validation_module
    selected_validation = validation_module(sys.argv)
    if selected_validation:
        importlib.import_module(selected_validation)
    else:
        ue.log("UEP_LYRA_PLAYABLE_BOOTSTRAP_READY")
'''
    tree=ast.parse(source)
    if tree.body and isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Constant) and isinstance(tree.body[0].value.value,str):tree.body.pop(0)
    require(ast.dump(tree,include_attributes=False)==ast.dump(ast.parse(expected),include_attributes=False),'Startup commandlet/import/normal boundary changed beyond the pinned native bootstrap')

def report_gate(child,report,normal_log,focused_log):
    require(child['status']=='passed' and child['error'] is None and child['process']['exit_code']==0,'Focused weapon process failed')
    require('-RenderOffscreen' in child['process']['arguments'] and '-NullRHI' not in child['process']['arguments'],'Focused weapon mode must actually render')
    normal=child['playable_startup'];args=normal['process']['arguments']
    require(normal['status']=='passed' and normal['no_validation_flags'] and normal['native_experience_loaded'] and normal['intentional_owned_process_stop'] and not normal['graceful_exit_tested'],'Normal startup observation/owner-stop evidence missing')
    require(not any(a.lower().startswith('-uep') for a in args) and normal['process']['pid']!=child['process']['pid'] and normal['process']['exit_code']==-1,'Normal startup must be a separate no-test-flag process stopped by its owner')
    require(normal['alive_observation_seconds']==20 and normal['process']['duration_seconds']>=20,'Normal startup observation too short')
    require(all(n in normal_log for n in ('UEP_LYRA_SCRIPT_LOADED','UEP_LYRA_PLAYABLE_BOOTSTRAP_READY','UEP_LYRA_WEAPON_HUD_REGISTERED 4','OnExperienceLoadComplete')),'Normal native Experience/bootstrap readiness absent')
    require(not any(n in normal_log for n in ('Goodbye Python','_DIFFERENTIAL_PASSED','_SHUTDOWN_PASSED','UEP_LYRA_SMOKE_','UEP_LYRA_NETWORK_')),'Normal startup entered a probe/exit path')
    require(not re.search(r'Log\w+:\s*Error:',normal_log) and not any(n in normal_log for n in ('Traceback','Ensure condition failed','Fatal error')),'Normal startup diagnostic failure')
    log_gate(focused_log,'UEP_WEAPON_HUD')
    require(report['status']=='passed' and len(report['cases'])==42 and len(report['declarations'])==report['restored_classes']==4 and report['class_identity_preserved'],'Actual four-presenter native comparison incomplete')
    require(not report['full_acceptance'] and not report['network_acceptance'] and report['shutdown']==dict(phase='python_atexit',owned_resources_closed_before_exit=True),'Probe exit/owned cleanup missing')
    require(len(report['reload_cycles'])==3 and all(r['status']=='passed' and r['native_gc_collected'] and r['python_housekeeper_gc_executed'] for r in report['reload_cycles']),'Three controlled reload/native-GC boundaries required')
    final=report['reload_cycles'][-1]['after'];require(final['active_count']==final['active_scopes']==0 and not final['ticker_active'] and final['subscribed']==final['unsubscribed'] and not final['errors'],'Probe left owned subscriptions/ticker/errors')
    return dict(status='passed',native_processes=2,focused_exit_code=0,normal_intentional_owned_stop_exit_code=-1,normal_observation_seconds=20,rendered_presenter_cases=42,controlled_reload_gc_cycles=3,full_version_acceptance=False)

def inspect(repo):
    repo=Path(repo).resolve();folder=repo/BASE;child_path=folder/'Focused/summary.json';wrapper_path=folder/'summary.json';ledger_path=repo/RECORD
    ledger=read(ledger_path);record=ledger['current_startup_pair'];wrapper=read(wrapper_path);child=read(child_path)
    require(sha(wrapper_path)==record['summary_sha256'] and sha(child_path)==record['focused_summary_sha256'],'Pinned current startup summaries changed')
    require(wrapper['status']=='passed' and wrapper['error'] is None and wrapper['source_and_binary_reuse_verified'],'Current accepted SDK/isolated stage provenance missing')
    require(not wrapper['cpp_compile_executed'] and not wrapper['cook_package_executed'],'This review must reuse the accepted build')
    report_path=folder/'Focused/weapon.json';focused_log_path=folder/'Focused/weapon.log';normal_log_path=folder/'Focused/playable.log'
    for path,key in ((report_path,'focused_report_sha256'),(focused_log_path,'focused_log_sha256'),(normal_log_path,'normal_log_sha256')):require(sha(path)==record[key],'Pinned startup report/log changed')
    report=read(report_path);native=report_gate(child,report,normal_log_path.read_text(encoding='utf-8-sig'),focused_log_path.read_text(encoding='utf-8-sig'))
    frozen=[]
    for row in wrapper['hashes']+child['input_hashes']+child['reference_hashes']:
        require(sha(row['path'])==row['sha256'].upper(),'Frozen native startup input changed: '+row['path']);frozen.append(row)
    scripts=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts';source=(scripts/'uep_lyra_hud/startup.py').read_text(encoding='utf-8-sig');catalogue,select=selector_catalogue(source)
    require(select(child['playable_startup']['process']['arguments']) is None and select(child['process']['arguments'])=='uep_lyra_hud.weapon_validation','Actual normal/explicit command lines select another startup mode')
    site_source=(scripts/'ue_site.py').read_text(encoding='utf-8-sig');site_guard(site_source);site=ast.parse(site_source);bootstrap=ast.parse((scripts/'uep_lyra_hud/bootstrap.py').read_text(encoding='utf-8-sig'))
    require(not any(isinstance(n,ast.Attribute) and n.attr=='request_exit' for n in ast.walk(site)) and not any(isinstance(n,ast.Attribute) and n.attr=='request_exit' for n in ast.walk(bootstrap)),'Normal startup bootstrap requests exit')
    imports=[n.module or '' for n in ast.walk(bootstrap) if isinstance(n,ast.ImportFrom)];require(not any('validation' in n or 'probe' in n for n in imports),'Normal bootstrap imports a validation probe')
    fixture=(scripts/'uep_lyra_hud/weapon_validation.py').read_text(encoding='utf-8-sig');require('time.monotonic() - self.started < 120' in fixture and 'self.cleanup()' in fixture and 'ue.request_exit()' in fixture,'Explicit weapon probe lost its native-wait bound/cleanup/exit')
    helper=(repo/'Validation/UEPValidationProcesses.ps1').read_text(encoding='utf-8-sig');driver=(repo/'Validation/Run-UEP58FocusedWeaponHUDValidation.ps1').read_text(encoding='utf-8-sig')
    require('[int]$TimeoutSeconds=240' in helper and '$Handle.process.Kill($true)' in helper and '$playableHandle.stopwatch.Elapsed.TotalSeconds -gt 240' in driver and 'Stop-UEPValidationProcess $playableHandle' in driver,'Owned driver process bounds/stopping changed')
    gate_path=repo/GATE/'summary.json';gate=read(gate_path);require(gate['status']=='passed' and gate['process']['exit_code']==0 and gate['report_sha256']==sha(report_path) and gate['contract_sha256']==sha(repo/'Validation/LyraWeaponHUDContracts.ps1') and gate['checker_sha256']==sha(repo/'Validation/Test-UEP58PackagedWeaponHUDReport.ps1'),'Independent current presenter/lifetime gate missing or changed')
    independent=read(repo/GATE/'report-gate.json');require(independent['status']=='passed' and independent['cases']==42 and independent['controlled_reload_cycles']==3,'Independent full native presenter semantic gate rejected report')
    image=repo/record['image']['path'];require(sha(image)==record['image']['sha256'].upper() and record['image']['visually_inspected'] and independent['native_image']['sha256']==sha(image),'Pinned actual rendered weapon screenshot/visual review changed')
    return dict(schema_version=1,status='passed',criterion=REQUIREMENT,completion_proven=True,version='0.9.0',native_scope=native,source_selector_catalogue=catalogue,
        evidence_ledger=dict(path=RECORD,sha256=sha(ledger_path)),startup_summary_sha256=sha(wrapper_path),focused_summary_sha256=sha(child_path),focused_report_sha256=sha(report_path),focused_log_sha256=sha(focused_log_path),normal_log_sha256=sha(normal_log_path),
        independent_gate=dict(directory=GATE,summary_sha256=sha(gate_path),report_sha256=sha(repo/GATE/'report-gate.json')),frozen_input_records=len(frozen),explicit_weapon_probe_timeout_seconds=120,owned_process_timeout_seconds=240,commandlet_outer_bootstrap_guard_verified=True,
        normal_process_exit_is_intentional_driver_stop=True,normal_graceful_exit_tested=False,normal_pixels_tested=False,focused_native_image_visually_inspected=True,referenced_native_processes=2,new_native_processes_launched_by_review=0,
        all_other_probe_gameplay_rerun=False,physical_input_tested=False,packaged_runtime=False,cpp_compile_executed=False,cook_package_executed=False,full_regression_executed=False,full_version_acceptance=False,full_migration_acceptance_proven=False)

def verify_documentation(document,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original normal-startup/explicit-probe criterion required')
    expected=inspect(repo);require(document['review']==expected,'Startup review differs from current pinned runtime/source evidence')
    return {k:expected[k] for k in ('status','criterion','referenced_native_processes','new_native_processes_launched_by_review','normal_process_exit_is_intentional_driver_stop','full_migration_acceptance_proven')}
