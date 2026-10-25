"""Source-bound original AI outcomes/cancellation and destroyed-owner acceptance."""
import ast,hashlib,importlib,importlib.util,json,subprocess
from pathlib import Path
from audit_ui_failure_cancellation_acceptance import source_guard,process_gate,log_gate,report_pin
from audit_ui_navigation_acceptance import read,sha,key,index_hashes,verify_lib_only_change
from audit_candidate_dispositions import verify_documentation as verify_candidates
from audit_static_scope_dispositions import relative_asset

REQUIREMENT='AI task/service outcomes and cancellation are reproducible; long-running tasks do not retain a destroyed Pawn or World.'
BASE='.build/LyraValidation/BlueprintPython/20261026-ai-lifetime'
SHARED='uep_lyra_weapons.hero_burst_cue_mixin'
MACRO='uep_lyra_weapons.macro_policies'
WORLD='uep_lyra_world.'
FRESH=[('TDMOriginal03','BlueprintFallback','tdm'),('TDMPython01','Python','tdm'),('CPOriginal01','BlueprintFallback','cp'),('CPPython01','Python','cp')]

def require(value,message):
    if not value:raise ValueError(message)

def ai_candidates(current):
    rows=[r for r in current['assets'] if '/Bot/' in r['path'] or '/ControlPoint/AI/' in r['path']]
    require(len(rows)==12 and len({r['path'] for r in rows})==12 and all(r['version']=='0.12.0' for r in rows),'Original12 AI/EQS candidates required')
    return {r['path'] for r in rows}

def imported_lib_bridge(before,after,macro):
    try:return dict(equivalence=verify_lib_only_change(before,after))
    except ValueError:pass
    tree=ast.parse(after);imports=[n for n in tree.body if isinstance(n,ast.ImportFrom) and n.level==1 and n.module=='macro_policies']
    require(len(imports)==1 and [(a.name,a.asname) for a in imports[0].names]==[('ignore_tag',None)],'Only the reviewed ignore_tag import may be added')
    tree.body.remove(imports[0]);counts={}
    class RestoreTag(ast.NodeTransformer):
        def visit_Call(self,node):
            if isinstance(node.func,ast.Name) and node.func.id=='ignore_tag':
                require(len(node.args)==1 and not node.keywords,'Changed Cue ignore-tag call shape')
                counts['calls']=counts.get('calls',0)+1
                return ast.Call(func=ast.Attribute(value=node.args[0],attr='call_function',ctx=ast.Load()),args=[ast.Constant('ComponentHasTag'),ast.Constant('ignore')],keywords=[])
            return self.generic_visit(node)
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in ('dash','death'):
            counts['calls']=0;RestoreTag().visit(node);require(counts['calls']==1,'Exactly one source-equivalent ignore-tag macro call required')
    verify_lib_only_change(before,ast.unparse(ast.fix_missing_locations(tree)))
    module=ast.parse(macro);functions=[n for n in module.body if isinstance(n,ast.FunctionDef)]
    for node in functions:
        require(not node.decorator_list and not node.args.defaults and not any(node.args.kw_defaults) and node.returns is None and all(a.annotation is None for a in node.args.posonlyargs+node.args.args+node.args.kwonlyargs),'Macro declarations execute unexpected import-time expressions')
    expected=ast.parse('''"""Python equivalents of the original audio/VFX macros, without native caches."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid
WEAPON='/Game/Weapons/B_Weapon.B_Weapon_C'
INVISIBLE='/Game/Characters/Heroes/Mannequin/Meshes/SKM_Manny_Invis.SKM_Manny_Invis'
MAGAZINE='Lyra.ShooterGame.Weapon.MagazineAmmo'
_calls=dict(weapon=0,ammo=0,tag=0,specific=0)
''')
    actual=ast.Module(body=[n for n in module.body if not isinstance(n,ast.FunctionDef)],type_ignores=[])
    require(ast.dump(actual,include_attributes=False)==ast.dump(expected,include_attributes=False),'Added macro import has unreviewed import-time behavior')
    return dict(equivalence='imported-lib-unchanged;reviewed-append-and-native-ignore-tag-body-fixes',added_macro_import='imports-existing-guarded-modules;literal-strings-and-zero-counters;function-bodies-not-executed')

def closure(overlay,seeds):
    pending=[WORLD+s+'_mixin' for s in seeds];seen={}
    while pending:
        name=pending.pop();path=overlay/Path(*name.split('.')).with_suffix('.py')
        if name in seen or not path.is_file():continue
        seen[name]=path;tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        if name==SHARED:
            # Every import site below must import only lib. The separately
            # checked append body cannot execute through that function.
            tree=ast.Module(body=[n for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.name=='lib'],type_ignores=[])
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                require(all(v.name!=SHARED for v in node.names),'Whole Cue imports need fresh native dependency evidence')
                pending.extend(v.name for v in node.names)
            elif isinstance(node,ast.ImportFrom):
                base=importlib.util.resolve_name('.'*node.level+(node.module or ''),name.rsplit('.',1)[0]) if node.level else node.module
                if base==SHARED:require({v.name for v in node.names}=={'lib'},'AI imports another changed Cue helper')
                if base:pending.extend([base]+[base+'.'+v.name for v in node.names])
    return seen

def source_review(repo,summary,ledger,seeds,coverage,retained=None):
    overlay=repo/'Demos/UEPLyraIntegration/Overlay';index=index_hashes(summary['hashes']);modules=[];macro_bridge=None
    for module,path in sorted(closure(overlay/'Content/Scripts',seeds).items()):
        rows=index.get(key(path),[])
        try:proof=source_guard(path,rows)
        except ValueError:
            if module==MACRO and not rows and macro_bridge is not None:
                modules.append(dict(module=module,current_sha256=sha(path),equivalence=macro_bridge['added_macro_import']));continue
            require(module==SHARED and rows and ledger.get('examples_parent_commit'),'Changed AI dependency needs fresh native evidence: '+module)
            relative=path.relative_to(repo/'Demos').as_posix()
            old=subprocess.check_output(['git','show',ledger['examples_parent_commit']+':'+relative],cwd=repo/'Demos').decode('utf-8-sig')
            text=old.replace('\r\n','\n');variants={hashlib.sha256(bom+t.encode()).hexdigest().upper() for t in (text,text.replace('\n','\r\n')) for bom in (b'',b'\xef\xbb\xbf')}
            require(all(r['sha256'] in variants for r in rows),'Historical lib source differs from frozen native input')
            macro=overlay/'Content/Scripts/uep_lyra_weapons/macro_policies.py';macro_bridge=imported_lib_bridge(old,path.read_text(encoding='utf-8-sig'),macro.read_text(encoding='utf-8-sig'))
            proof=dict(current_sha256=sha(path),native_sha256=rows[0]['sha256'],**macro_bridge)
        modules.append(dict(module=module,**proof))
    assets=[];candidate_paths=[]
    for row in coverage['assets']:
        names={(v.get('python_class') or '').rsplit('.',1)[0] for v in row.get('profiles',{}).values()}
        if not names.intersection({WORLD+s+'_mixin' for s in seeds}):continue
        candidate_paths.append(row['asset'])
        for asset in (row['asset'],row.get('mixin_set')):
            if asset:
                relative=relative_asset(asset,Path('F:/LyraStarterGame'));path=overlay/relative
                if not path.is_file():path=Path('F:/LyraStarterGame')/relative
                rows=index.get(key(path),[]);native_paths=[]
                if not rows:
                    project=Path(summary['process']['arguments'][0]);require(project.name=='LyraStarterGame.uproject' and project.resolve().is_relative_to(repo/'.build'),'Recorded isolated native project required')
                    rows=index.get(key(project.parent/relative),[]);native_paths=[r['path'] for r in rows]
                    rows=[dict(r,path=str(path)) for r in rows]
                if not rows and retained and asset in retained:
                    prior=retained[asset];proof=prior['guard']
                    require(not path.is_relative_to(overlay) and key(path)==key(proof['current_asset_path']) and sha(path)==proof['current_sha256']==proof['native_sha256'] and proof['recorded_stage_asset_paths'],'Only unchanged retained child assets may reuse historical native fingerprints')
                    assets.append(dict(asset=asset,current_asset_path=str(path),current_sha256=sha(path),frozen_by_this_native_run=False,historical_native_fingerprint=prior));continue
                assets.append(dict(asset=asset,current_asset_path=str(path),recorded_stage_asset_paths=native_paths,frozen_by_this_native_run=True,**source_guard(path,rows)))
    require(len(candidate_paths)==sum(8 if s=='shooter_ai' else 4 for s in seeds),'Complete AI controller/service/EQS asset guards required')
    return dict(modules=modules,assets=assets,candidate_paths=sorted(candidate_paths))

def inspect(repo,current,initial,fresh):
    repo=Path(repo).resolve();migration=repo/'Demos/UEPLyraIntegration/Migration';candidate_path=migration/'candidate_dispositions.json';candidate=read(candidate_path)
    census=verify_candidates(candidate,current,initial,repo);expected=ai_candidates(current)
    native_ledger=read(repo/candidate['evidence_paths']['native_ledger']);coverage=read(repo/native_ledger['runs'][0]['directory']/'audit.json')
    require([r['directory'] for r in fresh]==[BASE+'/'+v[0] for v in FRESH],'All four profile/map lifetime runs required')
    results=[];processes=0;covered=set();pairs={};retained={}
    for number,seed,marker in ((139,'shooter_ai','UEP_SHOOTER_AI'),(140,'shooter_eqs','UEP_SHOOTER_EQS')):
        ledger_path=next((migration/'Acceptance').glob(str(number)+'-*.json'));ledger=read(ledger_path);observed=set()
        for record in ledger['runs']:
            directory=record['directory'].replace('\\','/')
            if any(v in Path(directory).name for v in ('Audit','Assets')):continue
            folder=repo/directory;summary_path=folder/'summary.json';require(sha(summary_path)==record['summary_sha256'],'Pinned AI summary changed')
            summary=read(summary_path);processes+=process_gate(summary);path=folder/'jump.json'
            require(sha(path)==report_pin(ledger,record,Path(directory),'jump.json'),'Pinned AI report changed')
            report=read(path);gate=importlib.import_module(WORLD+seed+'_contract').validate(report)
            observed.add((report['profile'],report['mode']));proof=source_review(repo,summary,ledger,[seed],coverage);covered.update(proof['candidate_paths'])
            for row in proof['assets']:
                if row['recorded_stage_asset_paths']:
                    retained.setdefault(row['asset'],dict(ledger=ledger_path.relative_to(repo).as_posix(),directory=directory,guard=row))
            contract=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts'/Path(*(WORLD+seed+'_contract').split('.')).with_suffix('.py')
            contract_proof=source_guard(contract,index_hashes(summary['hashes']).get(key(contract),[]))
            log=folder/'jump.log';log_gate(log.read_text(encoding='utf-8-sig'),marker)
            results.append(dict(directory=directory,ledger=ledger_path.relative_to(repo).as_posix(),ledger_sha256=sha(ledger_path),summary_sha256=sha(summary_path),report_sha256=sha(path),log_sha256=sha(log),semantic_gate=gate,contract_guard=contract_proof,current_policy_and_asset_guards=proof,runtime_version_historical=True))
        require(observed=={(p,m) for p in ('BlueprintFallback','Python') for m in ('tdm','cp')},'Historical AI original/Python and TDM/CP matrix incomplete')
    require(covered==expected,'AI/EQS native proof does not cover the exact original candidate set')
    lifetime=importlib.import_module(WORLD+'shooter_ai_lifetime_contract');observer=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_world/shooter_ai_lifetime_validation.py'
    for record,(_,profile,mode) in zip(fresh,FRESH):
        folder=repo/record['directory'];summary_path=folder/'summary.json';require(sha(summary_path)==record['summary_sha256'],'Pinned lifetime summary changed')
        summary=read(summary_path);processes+=process_gate(summary);path=folder/'failure.json';log=folder/'failure.log'
        require(sha(path)==record['report_sha256'] and sha(log)==record['log_sha256'],'Pinned lifetime report/log changed')
        report=read(path);gate=lifetime.validate(report);require(report['profile']==profile and report['mode']==mode,'Lifetime profile/map mismatch')
        log_gate(log.read_text(encoding='utf-8-sig'),'UEP_SHOOTER_AI_LIFETIME')
        proof=source_review(repo,summary,{},['shooter_ai'],coverage,retained);observer_guard=source_guard(observer,index_hashes(summary['hashes']).get(key(observer),[]))
        pairs[(profile,mode)]=report
        results.append(dict(directory=record['directory'],summary_sha256=sha(summary_path),report_sha256=sha(path),log_sha256=sha(log),semantic_gate=gate,current_policy_and_asset_guards=proof,observer_guard=observer_guard,current_gate_rechecked=True,runtime_version_historical=False))
    require(set(pairs)=={(p,m) for p in ('BlueprintFallback','Python') for m in ('tdm','cp')},'Paired native lifetime proof incomplete')
    return dict(schema_version=1,status='passed',criterion=REQUIREMENT,completion_proven=True,original_ai_candidates=sorted(expected),
        source_candidate_guard=dict(path=candidate_path.relative_to(repo).as_posix(),sha256=sha(candidate_path),**census),native_runs=results,
        referenced_native_processes=processes,accepted_historical_native_processes=8,current_native_refresh_processes=4,native_lifetime_boundaries=8,
        original_native_bt_and_eqs_schedulers_preserved=True,old_runtime_versions_retained=True,new_native_processes_launched_by_review=0,
        retained_child_assets_use_explicit_historical_native_fingerprints=True,
        cpp_compile_executed=False,cook_package_executed=False,full_regression_executed=False,full_migration_acceptance_proven=False)

def verify_documentation(document,current,initial,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original AI criterion required')
    expected=inspect(repo,current,initial,document['current_native_refresh_runs']);require(document['review']==expected,'AI review differs from frozen native evidence/current sources')
    return {k:expected[k] for k in ('status','criterion','referenced_native_processes','current_native_refresh_processes','native_lifetime_boundaries','full_migration_acceptance_proven')}
