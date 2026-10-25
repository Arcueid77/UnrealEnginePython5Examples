"""Verify current per-candidate implementation/retention coverage, not gameplay.

Reuses a hash-bound native census only while its assets, SDK and declaration
sources remain valid. Unknown source changes fail;the reviewed Spawn Cue fix
must match its exact AST transformation and its separate accepted native input.
"""
import argparse,ast,copy,hashlib,io,json,re,subprocess,tarfile
from collections import Counter,defaultdict
from pathlib import Path
from audit_runtime_entrypoint_coverage import audit as entry_audit
from audit_static_scope_dispositions import verify_documentation as verify_static,relative_asset
from review_runtime_mixin_coverage import review as review_routes,MACROS

REQUIREMENT='Every audited candidate is migrated, explicitly retained, unreachable with checked references, or a named blocker; no silent coverage gaps remain.'
SPAWNING='uep_lyra_weapons.spawning_cue_mixin'
HELPER="""def mesh_target(actor):
    target=actor.get_property('TargetActor')
    return target if valid(target) else None
"""

def require(value,message):
    if not value:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def shape(tree):return ast.dump(tree,include_attributes=False)

def null_spawn_guard_only(old,new):
    expected=copy.deepcopy(old)
    functions=[n for n in expected.body if isinstance(n,ast.FunctionDef) and n.name=='spawn']
    if len(functions)!=1:return False
    loops=[n for n in functions[0].body if isinstance(n,ast.For)]
    if len(loops)!=1:return False
    loop=loops[0];setters=loop.body[-2:]
    if len(setters)!=2:return False
    for node,name in zip(setters,('SetVariableFloat','SetVariableVec3')):
        if not(isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)):return False
        call=node.value
        if not(isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name) and call.func.value.id=='effect' and call.func.attr=='call_function' and call.args and isinstance(call.args[0],ast.Constant) and call.args[0].value==name):return False
    condition=ast.parse('valid(effect)',mode='eval').body
    loop.body[-2:]=[ast.If(test=condition,body=setters,orelse=[])]
    return shape(expected)==shape(new)

def check_source_change(module,before,after):
    old,new=ast.parse(before),ast.parse(after)
    if shape(old)==shape(new):return 'unchanged-python-ast'
    require(module==SPAWNING,'Unreviewed declaration/dependency source change: '+module)
    if null_spawn_guard_only(old,new):return 'reviewed-private-native-null-effect-result-guard-declarations-unchanged'
    expected=copy.deepcopy(old);changed=[]
    class Target(ast.NodeTransformer):
        def visit_Call(self,node):
            if (isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='actor'
                    and node.func.attr=='get_property' and len(node.args)==1 and isinstance(node.args[0],ast.Constant) and node.args[0].value=='TargetActor'):
                changed.append(True);return ast.Call(func=ast.Name(id='mesh_target',ctx=ast.Load()),args=[ast.Name(id='actor',ctx=ast.Load())],keywords=[])
            return self.generic_visit(node)
    names={'spawn','colors','update','removal'}
    require(names<=set(n.name for n in expected.body if isinstance(n,ast.FunctionDef)),'Original Spawn Cue helpers missing')
    for node in expected.body:
        if isinstance(node,ast.FunctionDef) and node.name in names:Target().visit(node)
    index=next(i for i,n in enumerate(expected.body) if isinstance(n,ast.FunctionDef) and n.name=='mark')
    expected.body.insert(index+1,ast.parse(HELPER).body[0])
    require(len(changed)==4 and shape(expected)==shape(new),'Spawn Cue change exceeds the reviewed cached-target conversion fix')
    return 'reviewed-private-cached-target-fix-public-declarations-unchanged'

def source_modules(coverage):
    result=set()
    for asset in coverage['assets']:
        for profiles in [asset.get('profiles',{})]+[b.get('profiles',{}) for b in asset.get('typed_dispatch_bridges',[])]:
            for profile in profiles.values():
                if isinstance(profile,dict) and profile.get('python_class'):result.add(profile['python_class'].rsplit('.',1)[0])
    return result

def local_dependencies(roots,files):
    pending=list(roots);seen=set()
    while pending:
        module=pending.pop()
        if module in seen:continue
        require(module in files,'Current native-profile source module missing: '+module);seen.add(module)
        filename,text=files[module];package=module.split('.') if filename.endswith('/__init__.py') else module.split('.')[:-1]
        imports=[]
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,ast.Import):imports.extend(n.name for n in node.names)
            elif isinstance(node,ast.ImportFrom):
                prefix=package[:len(package)-node.level+1] if node.level else []
                base='.'.join(prefix+([node.module] if node.module else []))
                imports.extend([base]+[base+'.'+n.name if base else n.name for n in node.names if n.name!='*'])
        for name in [module.rsplit('.',1)[0] if '.' in module else '',*imports]:
            if name in files and name not in seen:pending.append(name)
    return seen

def archive_sources(repository,commit,prefix):
    require(re.fullmatch('[0-9a-f]{40}',commit) is not None,'Exact native input Git parent required')
    data=subprocess.check_output(['git','-C',str(repository),'archive',commit,'--',prefix])
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
        return {m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}

def verify_spawn_fix(repo,path):
    ledger=read(repo/'Demos/UEPLyraIntegration/Migration/Acceptance/233-spawning-cached-target-cleanup-and-current-melee-diagnosis.json')
    require(ledger['production_fix_class']=='/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C' and not ledger['original_race_fixed'],'Wrong or overstated Spawn Cue followup')
    require(any((repo/r['path']).resolve()==path.resolve() and r['sha256']==sha(path) for r in ledger['input_hashes']),'Current Spawn Cue bytes lack accepted followup provenance')
    accepted=ledger['accepted_run'];summary_path=repo/accepted['directory']/'summary.json'
    require(sha(summary_path)==accepted['summary_sha256'],'Spawn Cue followup run changed')
    summary=read(summary_path)
    require(summary['status']=='passed' and summary['external_gate']['exit_code']==0 and set(summary['processes'])=={'server','A','B0'} and all(p['exit_code']==0 for p in summary['processes'].values()),'Spawn Cue followup native gate failed')
    require(any(Path(r['path']).resolve()==path.resolve() and r['sha256'].upper()==sha(path) for r in summary['hashes']),'Spawn Cue source not frozen in accepted native followup')
    return dict(ledger='233-spawning-cached-target-cleanup-and-current-melee-diagnosis.json',sha256=sha(path),native_summary_sha256=sha(summary_path),original_race_fixed=False)

def verify_captured_script(repo,record,baseline_source,current_source,stage_path):
    frozen=repo/record['frozen_input']
    require(sha(frozen)==record['sha256'],'Captured native policy script changed')
    require(shape(ast.parse(frozen.read_text(encoding='utf-8-sig')))==shape(ast.parse(baseline_source)),
        'Captured native policy script differs from its input Git baseline')
    require(shape(ast.parse(Path(stage_path).read_text(encoding='utf-8-sig')))==shape(ast.parse(current_source)),
        'Current staged policy script differs from reviewed source')

def inspect(repo,current,initial,paths):
    repo=Path(repo);base=repo/'Demos/UEPLyraIntegration';manifest=base/'Migration/batches.json'
    coverage_ledger=read(repo/paths['native_ledger']);require(len(coverage_ledger['runs'])==1,'One exact native coverage census required')
    run=coverage_ledger['runs'][0];folder=repo/run['directory'];summary_path=folder/'summary.json';coverage_path=folder/'audit.json'
    require(sha(summary_path)==run['summary_sha256'],'Native census summary changed')
    record,=[r for r in run['report_hashes'] if r['file']=='audit.json'];require(sha(coverage_path)==record['sha256'],'Native census report changed')
    summary,coverage=read(summary_path),read(coverage_path)
    require(summary['status']=='passed' and summary['process']['exit_code']==0 and not summary['cpp_compile_executed'] and not summary['cook_package_executed'],'Native census did not pass its read-only gate')
    log_path=folder/'audit.log';log=log_path.read_text(encoding='utf-8-sig')
    require('LogPython: Error' not in log and log.index('UEP_RUNTIME_COVERAGE_AUDIT_PASSED')<log.index('Goodbye Python')<log.index('Log file closed'),'Native census ordered clean shutdown evidence missing')
    snapshot=coverage_ledger['native_manifest_input_snapshot'];require(sha(repo/snapshot['path'])==snapshot['sha256'],'Native input manifest snapshot changed')
    frozen_manifest=read(repo/snapshot['path']);require([(r['path'],r['version']) for r in frozen_manifest['assets']]==[(r['path'],r['version']) for r in current['assets']],'Native census scope differs from current candidates')
    for row in summary['hashes']:
        if Path(row['path']).resolve()==manifest.resolve():require(row['sha256'].upper()==snapshot['sha256'],'Native manifest provenance mismatch')
        else:require(sha(row['path'])==row['sha256'].upper(),'Frozen native census input changed: '+row['path'])
    routes=review_routes(coverage,current)
    static_doc=read(repo/paths['static_scope']);static=verify_static(static_doc,current,initial)
    original_path=Path(static_doc['input_hashes'][0]['path']);original=read(original_path)
    source_reviews=read(repo/paths['entrypoint_reviews']);entries=entry_audit(original,coverage,source_reviews['entries'])
    require(len(entries['entrypoints'])==963 and not entries['counts'].get('unrouted-business-review') and not entries['counts'].get('staged-disconnected-original-body-review'),'Original entry coverage contains a silent gap')
    retained_ledger=read(repo/paths['entrypoint_ledger'])
    proven={(r['asset'],r['graph'],r['entry']):r for r in retained_ledger['retained_native_asset_provenance']}
    for entry in entries['entrypoints']:
        if entry['disposition']!='retained-native-source-review':continue
        key=(entry['asset'],entry['graph'],entry['entry']);require(key in proven,'Retained entry lacks individual native source provenance')
        record=proven[key];require(sha(repo/record['ledger'])==record['ledger_sha256'],'Retained entry historical ledger changed')
        require(sha(record['current_native_asset']['path'])==record['current_native_asset']['sha256'].upper(),'Retained entry current asset changed')
        require(record['byte_matched_historical_inputs'],'Retained entry needs byte-matched native input')
        for accepted in record['byte_matched_historical_inputs']:
            historical=repo/accepted['directory']/'summary.json';require(sha(historical)==accepted['summary_sha256'] and read(historical)['status']=='passed','Retained entry historical run changed')
    prefix='UEPLyraIntegration/Overlay/Content/Scripts';baseline=coverage_ledger['examples_parent_commit'];old=archive_sources(repo/'Demos',baseline,prefix)
    files={}
    for p in (base/'Overlay/Content/Scripts').rglob('*.py'):
        relative=p.relative_to(base/'Overlay/Content/Scripts');parts=relative.with_suffix('').parts
        name='.'.join(parts[:-1] if parts[-1]=='__init__' else parts)
        require(name not in files,'Ambiguous current Python module: '+name)
        files[name]=(p.relative_to(repo/'Demos').as_posix(),p.read_text(encoding='utf-8-sig'))
    declared=source_modules(coverage);dependencies=local_dependencies(declared,files);sources=[];fix=None
    captured=None
    if coverage_ledger.get('native_profile_script_snapshot'):
        snapshot=coverage_ledger['native_profile_script_snapshot']
        require(sha(repo/snapshot['path'])==snapshot['sha256'],'Native profile script snapshot changed')
        records=read(repo/snapshot['path'])['scripts'];captured={row['module']:row for row in records}
        require(len(captured)==len(records) and set(captured)==dependencies,'Native profile script snapshot scope differs')
    native_stage=Path(static_doc['source_copy_roots']['stage'])
    for module in sorted(dependencies):
        relative,text=files[module];require(relative in old,'Native declaration dependency not present in native Git input: '+module)
        previous=old[relative].decode('utf-8-sig');state=check_source_change(module,previous,text)
        if captured is not None:
            require(captured[module]['path']=='Demos/'+relative,'Native profile script snapshot path differs')
            verify_captured_script(repo,captured[module],previous,text,native_stage/Path(relative).relative_to('UEPLyraIntegration/Overlay'))
        if state=='reviewed-private-native-null-effect-result-guard-declarations-unchanged':
            from audit_spawning_spawn_result_fix import verify as verify_null_spawn_fix
            fix=verify_null_spawn_fix(repo,repo/'Demos'/relative)
        elif state.startswith('reviewed-private'):fix=verify_spawn_fix(repo,repo/'Demos'/relative)
        sources.append(dict(module=module,path='Demos/'+relative,sha256=sha(repo/'Demos'/relative),native_baseline_sha256=hashlib.sha256(old[relative]).hexdigest().upper(),state=state))
    changed=subprocess.check_output(['git','-C',str(repo/'Demos'),'diff',baseline,'--name-only','--','UEPLyraIntegration/Overlay'],encoding='utf-8').splitlines()
    require(not any(p.endswith(('.uasset','.umap','.ini')) for p in changed),'Binding/asset/config changed since native census;new native/source review required')
    shared=subprocess.check_output(['git','-C',str(repo),'diff',coverage_ledger['core_parent_commit'],'--name-only','--','Content/Scripts'],encoding='utf-8').strip()
    require(not shared,'Shared Python runtime changed since native census')
    stage=Path(static_doc['source_copy_roots']['stage']);reference=Path(static_doc['source_copy_roots']['reference']);binding_assets=[]
    for asset in sorted({a['mixin_set'] for a in coverage['assets'] if a.get('mixin_set')}):
        relative=relative_asset(asset,reference);overlay=base/'Overlay'/relative;require(sha(overlay)==sha(stage/relative),'Current Mixin Set bytes differ from stage')
        binding_assets.append(dict(asset=asset,sha256=sha(overlay)))
    by_asset=defaultdict(Counter)
    for entry in entries['entrypoints']:by_asset[entry['asset']][entry['disposition']]+=1
    issue=current['melee_two_owner_damage_pilot']['replica_readiness_issue'];require(issue['status']=='open_not_fixed','Readiness blocker must be reviewed before changing its disposition')
    rows=[];native_rows={row['asset']:row for row in coverage['assets']}
    for row in routes['candidates']:
        asset=row['asset'];kind=row['disposition'];reasons=[];blockers=[]
        if kind.startswith('retained-'):reasons.append(kind)
        if asset in MACROS:
            p=base/'Migration/Acceptance'/MACROS[asset];require(p.is_file() and read(p)['status']=='evidence_snapshot','Macro consumer closure ledger missing');reasons.append(MACROS[asset])
        if asset=='/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin':blockers.append(dict(name='initial-join-canonical-pawn-empty-asc',manifest_field='melee_two_owner_damage_pilot.replica_readiness_issue',status='open_not_fixed'))
        if asset=='/ShooterCore/Weapons/NetShooter_PROTO/B_NetShooter.B_NetShooter':reasons.append('Known original multicast/replicated component discrepancy:97-netshooter-native-impact-multicast-component-parity.json;game-project C++ remains separate')
        native_row=native_rows[asset]
        rows.append(dict(asset=asset,version=row['version'],disposition=kind,effective_profile=row['effective_profile'],
            effective_python_class=native_row.get('profiles',{}).get(row['effective_profile'],{}).get('python_class'),
            reviewed_inactive_family_stubs=sorted(native_row.get('unimplemented_union_methods',[])),
            original_entry_dispositions=dict(sorted(by_asset[asset].items())),explicit_retention_reasons=reasons,named_open_issues=blockers))
    return dict(schema_version=1,status='passed',criterion=REQUIREMENT,original_scope=[246,182,63,11],original_assets=491,runtime_candidates=246,excluded_assets_with_source_reasons=static['documented_assets'],
        original_entrypoints=963,unclassified_original_entries=0,source_profile_modules=len(declared),source_dependency_modules=len(dependencies),source_baseline_examples_commit=baseline,
        current_source_reviews=sources,current_binding_assets=binding_assets,reviewed_spawning_fix=fix,native_census_log_sha256=sha(log_path),entrypoint_counts=entries['counts'],candidate_disposition_counts=routes['disposition_counts'],candidates=rows,
        candidate_dispositions_proven=True,gameplay_semantics_all_proven=False,runtime_acceptance=False,full_migration_acceptance_proven=False,native_processes_launched=0,cpp_compile_executed=False,cook_package_executed=False,
        limitations=['Inventory implementation/retention disposition only;gameplay,presentation,lifecycle,network/package and original version requirements are separate.',
          'Reuses a hash-bound native census;does not replay historical runtime or accept every branch.',
          'Named Pawn/ASC issue stays open;known original NetShooter discrepancy stays explicit.'],evidence_paths=paths)

def verify_documentation(document,current,initial,repo):
    require(document.get('schema_version')==1 and document.get('evidence_paths') and document.get('candidate_dispositions_proven') is True,'Frozen native/source evidence paths required;flags alone do not prove candidate disposition')
    expected=inspect(repo,current,initial,document['evidence_paths'])
    require(document==expected,'Candidate dispositions differ from current verified source/assets')
    return dict(status='passed',runtime_candidates=246,original_assets=491,original_entrypoints=963,excluded_assets=245,source_profile_modules=expected['source_profile_modules'],source_dependency_modules=expected['source_dependency_modules'],runtime_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);parser.add_argument('--initial-inventory',required=True);parser.add_argument('--result',required=True)
    parser.add_argument('--native-ledger',help='Repository-relative current native census ledger;otherwise reuse the existing disposition artifact anchor')
    args=parser.parse_args()
    manifest=Path(args.manifest).resolve();repo=manifest.parents[3]
    if not args.native_ledger:
        existing=manifest.parent/'candidate_dispositions.json'
        args.native_ledger=(read(existing).get('evidence_paths',{}).get('native_ledger') if existing.is_file() else None) or 'Demos/UEPLyraIntegration/Migration/Acceptance/222-all-original-candidate-native-routing-and-inheritance-review.json'
    paths=dict(native_ledger=args.native_ledger,entrypoint_ledger='Demos/UEPLyraIntegration/Migration/Acceptance/223-original-entrypoint-transitive-routes-and-retained-native-source-review.json',entrypoint_reviews='Demos/UEPLyraIntegration/Migration/entrypoint_source_reviews.json',static_scope='Demos/UEPLyraIntegration/Migration/static_scope_dispositions.json')
    report=inspect(repo,read(manifest),read(args.initial_inventory),paths)
    Path(args.result).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ('current_source_reviews','current_binding_assets','candidates','limitations','evidence_paths')}))
