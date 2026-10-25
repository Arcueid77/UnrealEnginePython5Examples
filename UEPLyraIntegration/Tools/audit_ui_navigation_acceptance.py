"""Source-bound native proof for the original navigation/settings/session/replay item."""
import ast,hashlib,importlib,importlib.util,json,os,subprocess
from pathlib import Path
from audit_ui_failure_cancellation_acceptance import source_guard,process_gate,log_gate,ledger_record,report_pin
from audit_candidate_dispositions import verify_documentation as verify_candidates
from audit_static_scope_dispositions import relative_asset

REQUIREMENT='Navigation, focus/back behavior, settings persistence, session results and replay controls pass original-BP/Python comparisons.'
BASE='.build/LyraValidation/BlueprintPython/20261026-ui-navigation-acceptance'
HUD='uep_lyra_hud.'
SHARED='uep_lyra_weapons.hero_burst_cue_mixin'
LEGACY=[
 (147,'settings_editors_contract','UEP_SETTINGS_EDITORS',['settings_editors']),
 (148,'settings_screens_contract','UEP_SETTINGS_SCREENS',['settings_screens']),
 (156,'experience_list_contract','UEP_EXPERIENCE_LIST',['experience_list','experience_entry']),
 (160,'session_browser_contract','UEP_SESSION_BROWSER',['session_browser']),
 (227,'session_join_failure_contract','UEP_SESSION_JOIN_FAILURE',['session_entry','session_browser']),
 (163,'replay_browser_contract','UEP_REPLAY_BROWSER',['replay_browser','replay_entry']),
 (243,'settings_local_persistence_contract','UEP_SETTINGS_LOCAL',['settings_editors','settings_screens','menu_layers','bound_action']),
 (247,'ui_travel_lifetime_contract','UEP_UI_TRAVEL_LIFETIME',['menu_layers','frontend_menu','settings_screens','bound_action']),
]
FRESH=[
 ('Frontend01','frontend_menu_contract','UEP_FRONTEND_MENU',['frontend_menu']),
 ('ExperienceLife01','experience_screen_contract','UEP_EXPERIENCE_SCREEN',['experience_screen','experience_list','experience_entry']),
 ('ExperienceQuickOriginal01','experience_screen_contract','UEP_EXPERIENCE_SCREEN',['experience_screen','experience_list','experience_entry']),
 ('ExperienceQuickPython01','experience_screen_contract','UEP_EXPERIENCE_SCREEN',['experience_screen','experience_list','experience_entry']),
 ('HostLife01','host_session_contract','UEP_HOST_SESSION',['host_session','experience_list','experience_entry']),
 ('HostOriginal01','host_session_contract','UEP_HOST_SESSION',['host_session','experience_list','experience_entry']),
 ('HostPython01','host_session_contract','UEP_HOST_SESSION',['host_session','experience_list','experience_entry']),
 ('ReplayOriginal01','replay_runtime_contract','UEP_REPLAY_RUNTIME',['replay_runtime','replay_browser','replay_entry']),
 ('ReplayPython01','replay_runtime_contract','UEP_REPLAY_RUNTIME',['replay_runtime','replay_browser','replay_entry']),
 ('SharedOriginalWrite01','settings_persistence_contract','UEP_SETTINGS_PERSISTENCE',['settings_editors','settings_screens']),
 ('SharedOriginalRead02','settings_persistence_contract','UEP_SETTINGS_PERSISTENCE',['settings_editors','settings_screens']),
 ('SharedPythonWrite01','settings_persistence_contract','UEP_SETTINGS_PERSISTENCE',['settings_editors','settings_screens']),
 ('SharedPythonRead01','settings_persistence_contract','UEP_SETTINGS_PERSISTENCE',['settings_editors','settings_screens']),
]
def require(value,message):
    if not value:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def key(path):return os.path.normcase(os.path.abspath(path))
def index_hashes(rows):
    result={}
    for row in rows:result.setdefault(key(row['path']),[]).append(row)
    return result
def shape(node):return ast.dump(node,include_attributes=False)
def verify_lib_only_change(before,after):
    old,new=ast.parse(before),ast.parse(after)
    old_functions={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)};new_functions={n.name:n for n in new.body if isinstance(n,ast.FunctionDef)}
    require(set(old_functions)==set(new_functions) and 'lib' in old_functions,'Shared helper function inventory changed')
    require(shape(old_functions['lib'])==shape(new_functions['lib']),'Imported lib helper changed')
    changed={n for n in old_functions if shape(old_functions[n])!=shape(new_functions[n])}
    require(changed=={'append'},'Shared helper change exceeds the separately reviewed Cue array-slot fix')
    require(shape(ast.Module(body=[n for n in old.body if not isinstance(n,ast.FunctionDef)],type_ignores=[]))==shape(ast.Module(body=[n for n in new.body if not isinstance(n,ast.FunctionDef)],type_ignores=[])),'Shared helper import-time state changed')
    a,b=old_functions['append'],new_functions['append']
    require(shape(a.args)==shape(b.args) and not a.decorator_list and not b.decorator_list and not b.args.defaults,'Cue append import-time behavior changed')
    return 'only-imported-lib-unchanged;unrelated-append-body-fix'
def closure(overlay,seeds):
    pending=[HUD+s+'_mixin' for s in seeds];seen={}
    while pending:
        name=pending.pop();path=overlay/Path(*name.split('.')).with_suffix('.py')
        if name in seen or not path.is_file():continue
        seen[name]=path
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.Import):
                require(all(v.name!=SHARED for v in node.names),'Whole Cue module imports require their own native/source review')
                pending.extend(v.name for v in node.names)
            elif isinstance(node,ast.ImportFrom):
                base=importlib.util.resolve_name('.'*node.level+(node.module or ''),name.rsplit('.',1)[0]) if node.level else node.module
                if base==SHARED:require({v.name for v in node.names}=={'lib'},'UI imports another changed Cue helper')
                if base:pending.extend([base]+[base+'.'+v.name for v in node.names])
    return seen
def source_review(repo,summary,ledger,seeds,coverage):
    overlay=repo/'Demos/UEPLyraIntegration/Overlay';files=closure(overlay/'Content/Scripts',seeds);index=index_hashes(summary['hashes']);result=[]
    for module,path in sorted(files.items()):
        rows=index.get(key(path),[])
        try:proof=source_guard(path,rows)
        except ValueError:
            require(module==SHARED and rows and ledger.get('examples_parent_commit'),'Changed UI dependency needs fresh native evidence: '+module)
            relative=str(path.relative_to(repo/'Demos')).replace('\\','/')
            old=subprocess.check_output(['git','show',ledger['examples_parent_commit']+':'+relative],cwd=repo/'Demos').decode('utf-8-sig')
            values={hashlib.sha256(v).hexdigest().upper() for t in (old.replace('\r\n','\n'),old.replace('\r\n','\n').replace('\n','\r\n')) for v in (t.encode(),b'\xef\xbb\xbf'+t.encode())}
            require(all(r['sha256'] in values for r in rows),'Historical imported helper differs from pinned native input')
            proof=dict(current_sha256=sha(path),native_sha256=rows[0]['sha256'],equivalence=verify_lib_only_change(old,path.read_text(encoding='utf-8-sig')))
        result.append(dict(module=module,**proof))
    assets=[]
    for row in coverage['assets']:
        profiles=row.get('profiles',{});modules={(v.get('python_class') or '').rsplit('.',1)[0] for v in profiles.values()}
        if not modules.intersection({HUD+s+'_mixin' for s in seeds}):continue
        for asset in (row['asset'],row.get('mixin_set')):
            if not asset:continue
            path=overlay/relative_asset(asset,Path('F:/LyraStarterGame'))
            assets.append(dict(asset=asset,**source_guard(path,index.get(key(path),[]))))
    require(assets,'Native UI asset/Mixin Set guards missing')
    return dict(modules=result,assets=assets)
def inspect(repo,current,initial,fresh):
    repo=Path(repo).resolve();migration=repo/'Demos/UEPLyraIntegration/Migration';candidate_path=migration/'candidate_dispositions.json';candidate=read(candidate_path)
    census=verify_candidates(candidate,current,initial,repo)
    require(sum(a['version']=='0.13.0' for a in current['assets'])==57,'Original57 UI candidates required')
    native_ledger=read(repo/candidate['evidence_paths']['native_ledger']);record=native_ledger['runs'][0];coverage=read(repo/record['directory']/'audit.json')
    require([r['directory'] for r in fresh]==[BASE+'/'+s[0] for s in FRESH],'All affected native refresh runs required')
    results=[];reports_by_contract={};processes=0
    jobs=[]
    for number,contract,marker,seeds in LEGACY:
        ledger_path=next((migration/'Acceptance').glob(str(number)+'-*.json'));ledger=read(ledger_path)
        records=ledger.get('native_runs',ledger.get('runs',[]))
        for record in records:
            directory=record['directory'].replace('\\','/')
            if any(v in Path(directory).name for v in ('Audit','Assets')):continue
            jobs.append((ledger,record,directory,contract,marker,seeds,str(ledger_path.relative_to(repo)).replace('\\','/')))
    for record,(_,contract,marker,seeds) in zip(fresh,FRESH):jobs.append(({},record,record['directory'],contract,marker,seeds,None))
    for ledger,record,directory,contract,marker,seeds,ledger_path in jobs:
        folder=repo/directory;summary_path=folder/'summary.json';require(sha(summary_path)==record['summary_sha256'],'Pinned UI runtime summary changed')
        summary=read(summary_path);processes+=process_gate(summary);module=importlib.import_module(HUD+contract)
        names=['host.json','BlueprintFallback.json','Python.json'] if contract=='session_join_failure_contract' else ['failure.json' if contract=='ui_travel_lifetime_contract' else 'result.json' if contract in ('settings_persistence_contract','settings_local_persistence_contract') or ledger_path is None else 'jump.json']
        pins=[]
        for name in names:
            path=folder/name
            if ledger_path is None:expected=record['report_sha256']
            elif contract=='settings_persistence_contract':expected=next(r['sha256'] for r in ledger['supplemental_evidence'] if r['path'].replace('\\','/')==directory+'/'+name)
            else:expected=report_pin(ledger,record,Path(directory),name)
            require(sha(path)==expected,'Pinned UI runtime report changed: '+str(path))
            raw=read(path)
            if contract!='session_join_failure_contract':module.validate(raw)
            reports_by_contract.setdefault(contract,[]).append(raw)
            arguments=(summary.get('process') or {}).get('arguments',[])
            log_args=[v.split('=',1)[1] for v in arguments if v.startswith('-abslog=')]
            log=Path(log_args[0]) if log_args else path.with_suffix('.log')
            require(log.resolve().is_relative_to(folder.resolve()),'Native UI log is outside its recorded run')
            if ledger_path is None:require(sha(log)==record['log_sha256'],'Pinned refreshed UI log changed')
            errors=['FinishJoinSession(Failed with Result: Join failed.)'] if contract=='session_join_failure_contract' and name!='host.json' else []
            log_gate(log.read_text(encoding='utf-8-sig'),marker,errors)
            pins.append(dict(file=name,sha256=sha(path),log_sha256=sha(log)))
        if contract=='session_join_failure_contract':module.validate(folder)
        if contract=='settings_persistence_contract' and ledger_path:
            for saved in ledger['supplemental_evidence']:
                if 'native-saved-bytes/' in saved['path']:require(sha(repo/saved['path'])==saved['sha256'],'Archived native save bytes changed')
        if contract=='settings_local_persistence_contract':
            for saved in record.get('native_ini_evidence',[]):require(sha(repo/saved['snapshot'])==saved['sha256'],'Archived native INI snapshot changed')
        proof=source_review(repo,summary,ledger,seeds,coverage)
        results.append(dict(directory=directory,ledger=ledger_path,ledger_sha256=sha(repo/ledger_path) if ledger_path else None,summary_sha256=sha(summary_path),reports=pins,current_policy_and_asset_guards=proof,runtime_version_historical=ledger_path is not None))
    for contract in ('settings_persistence_contract','settings_local_persistence_contract'):
        module=importlib.import_module(HUD+contract);rows=reports_by_contract[contract]
        for profile in ('BlueprintFallback','Python'):
            write=next(r for r in rows if r['profile']==profile and r['mode']=='write');restore=next(r for r in rows if r['profile']==profile and r['mode']=='read_restore');module.validate_pair(write,restore)
    return dict(schema_version=1,status='passed',criterion=REQUIREMENT,completion_proven=True,source_candidate_guard=dict(path='Demos/UEPLyraIntegration/Migration/candidate_dispositions.json',sha256=sha(candidate_path),**census),
        native_runs=results,referenced_native_processes=processes,current_native_refresh_processes=len(FRESH),new_native_processes_launched_by_review=0,settings_write_read_pairs=4,current_shared_ui_helpers_and_native_assets_verified=True,
        old_runtime_versions_retained=True,all57_widget_behaviors_replayed=False,cpp_compile_executed=False,cook_package_executed=False,full_regression_executed=False,full_migration_acceptance_proven=False)
def verify_documentation(document,current,initial,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original navigation criterion required')
    expected=inspect(repo,current,initial,document['current_native_refresh_runs'])
    require(document['review']==expected,'Navigation review differs from pinned native evidence/current source')
    return {k:expected[k] for k in ('status','criterion','referenced_native_processes','current_native_refresh_processes','settings_write_read_pairs','full_migration_acceptance_proven')}
