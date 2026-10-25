"""Recheck the exact original effects/audio/phase/scoring/notification criterion."""
import ast,copy,hashlib,importlib,importlib.util,json,re,subprocess
from pathlib import Path
from audit_ui_failure_cancellation_acceptance import source_guard,process_gate,log_gate,report_pin
from audit_ui_navigation_acceptance import read,sha,key,index_hashes
from audit_ai_lifetime_acceptance import imported_lib_bridge
from audit_candidate_dispositions import verify_documentation as verify_candidates
from audit_static_scope_dispositions import relative_asset

REQUIREMENT='Effect/audio triggering, warmup/play/postgame, scoring and notifications match the original BP checkpoints under the same inputs.'
SHARED='uep_lyra_weapons.hero_burst_cue_mixin'
MACRO='uep_lyra_weapons.macro_policies'
SPAWNING='uep_lyra_weapons.spawning_cue_mixin'
DISPATCH='uep_lyra_weapons.weapon_audio_dispatch_mixin'
SPECS=[
    (109, 'Differential01', ('uep_lyra_audio.music_family_mixin',)),
    (110, 'Differential01', ('uep_lyra_audio.wind_system_mixin',)),
    (112, 'Differential01', ('uep_lyra_weapons.footstep_mixin',)),
    (90, 'Differential01', ('uep_lyra_weapons.weapon_decals_mixin',)),
    (89, 'Differential02NativeHold', ('uep_lyra_weapons.weapon_fire_fx_mixin',)),
    (92, 'ImpactsRegression01Expired', ('uep_lyra_weapons.weapon_impacts_mixin',)),
    (120, 'Differential01', ('uep_lyra_weapons.physics_field_mixin',)),
    (115, 'Differential04NativeFloat', ('uep_lyra_weapons.character_damage_mixin',)),
    (113, 'Differential04NativeGuard', ('uep_lyra_hud.cue_widget_mixin',)),
    (119, 'Differential04DeferredSpawner', ('uep_lyra_weapons.small_burst_cue_mixin',)),
    (187, 'HeroBurst01Affected', ('uep_lyra_weapons.hero_burst_cue_mixin',)),
    (141, 'ConsumerTraversal01', ('uep_lyra_weapons.traversal_cue_mixin',)),
    (253, 'SpawningRendered01', ('uep_lyra_weapons.spawning_cue_mixin',)),
    (114, 'Differential02SelectedProfiles', ('uep_lyra_hud.match_message_mixin', 'uep_lyra_hud.waiting_message_mixin')),
    (141, 'ConsumerFire01', ('uep_lyra_weapons.weapon_fire_cue_mixin',)),
    (128, 'Differential02Accolade', ('uep_lyra_hud.accolade_relay_mixin',)),
    (127, 'Differential01Elimination', ('uep_lyra_hud.elimination_feed_relay_mixin',)),
    (126, 'Differential12LocalTransform', ('uep_lyra_world.control_point_feedback_mixin',)),
    (123, 'Differential01', ('uep_lyra_weapons.cp_scoring_mixin',)),
    (136, 'Differential02NativeAnimationFrames', ('uep_lyra_hud.control_point_widgets_mixin',)),
    (135, 'Differential06StyleGameFrames', ('uep_lyra_hud.scoreboard_style_mixin',)),
    (133, 'Differential01', ('uep_lyra_hud.scoreboard_rows_mixin',)),
    (122, 'Differential02SourceSemantics', ('uep_lyra_weapons.tdm_scoring_mixin',)),
    (137, 'Differential04SettledTimer', ('uep_lyra_hud.elimination_score_mixin',)),
    (138, 'Differential03PythonSeamless', ('uep_lyra_weapons.game_phases_mixin',)),
    (121, 'Differential04ResetEligibility', ('uep_lyra_weapons.scoring_base_mixin',)),
    (130, 'Differential01', ('uep_lyra_hud.accolade_widgets_mixin',)),
    (131, 'Differential02NativeRefresh', ('uep_lyra_hud.elimination_widgets_mixin',)),
    (134, 'Differential02SafeValidity', ('uep_lyra_hud.scoreboard_list_mixin',)),
    (100, 'Differential01', ('uep_lyra_weapons.weapon_audio_math_mixin',)),
    (101, 'Differential02Precision', ('uep_lyra_weapons.weapon_audio_dispatch_mixin',)),
    (102, 'Differential01Offline', ('uep_lyra_weapons.weapon_audio_whiz_mixin',)),
    (106, 'Pistol02ReuseObserver', ('uep_lyra_weapons.weapon_audio_early_mixin',)),
    (106, 'Rifle02Reuse', ('uep_lyra_weapons.weapon_audio_early_mixin',)),
    (106, 'Shotgun01ReuseObserver', ('uep_lyra_weapons.weapon_audio_early_mixin',)),
    (107, 'Differential01', ('uep_lyra_audio.music_manager_mixin',)),
    (108, 'Differential03ProbeRoot', ('uep_lyra_audio.music_manager_lifecycle_mixin',)),
    (111, 'Differential01', ('uep_lyra_audio.general_audio_mixin',)),
    (124, 'Differential05NativeActivationState', ('uep_lyra_world.control_point_helpers_mixin',)),
    (125, 'Differential07NativeReady', ('uep_lyra_world.control_point_state_mixin',)),
    (135, 'Differential07StyleCP', ('uep_lyra_hud.scoreboard_style_mixin',)),
    (138, 'Differential02FallbackSeamless', ('uep_lyra_weapons.game_phases_mixin',)),
    (141, 'Differential01OriginalMacro', ('uep_lyra_weapons.macro_policies',)),
    (141, 'ConsumerAudioEffect01', ('uep_lyra_weapons.weapon_audio_early_mixin',)),
    (253, 'SpawningDestroyed01', ('uep_lyra_weapons.spawning_cue_mixin',)),
]
_HISTORY={}

def require(value,message):
    if not value:raise ValueError(message)

def shape(node):return ast.dump(node,include_attributes=False)

def closure(scripts,seeds):
    pending=list(seeds);seen={}
    while pending:
        name=pending.pop();path=scripts/Path(*name.split('.')).with_suffix('.py')
        if name in seen or not path.is_file():continue
        seen[name]=path
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.Import):pending.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):
                base=importlib.util.resolve_name('.'*node.level+(node.module or ''),name.rsplit('.',1)[0]) if node.level else node.module
                if base:pending.extend([base]+[base+'.'+a.name for a in node.names])
    require(set(seeds)<=seen.keys(),'Every selected policy module must exist')
    return seen

def historical_source(repo,path,rows):
    expected={r['sha256'] for r in rows};require(len(expected)==1,'One frozen historical Python source required')
    relative=path.relative_to(repo/'Demos').as_posix();token=(str(repo),relative,next(iter(expected)))
    if token in _HISTORY:return _HISTORY[token]
    refs=subprocess.check_output(['git','log','--format=%H','--',relative],cwd=repo/'Demos',text=True).splitlines()
    for revision in refs:
        data=subprocess.check_output(['git','show',revision+':'+relative],cwd=repo/'Demos');text=data.decode('utf-8-sig').replace('\r\n','\n')
        variants={hashlib.sha256(bom+t.encode()).hexdigest().upper() for t in (text,text.replace('\n','\r\n')) for bom in (b'',b'\xef\xbb\xbf')}
        if expected<=variants:
            result=(text,dict(revision=revision,native_sha256=next(iter(expected))));_HISTORY[token]=result;return result
    raise ValueError('Git source does not match the pinned native input: '+relative)

def cue_helper_equivalence(before,after,files):
    names=set()
    for module,path in files.items():
        if module==SHARED:continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.Import):require(all(a.name!=SHARED for a in node.names),'Whole changed Cue imports require fresh native proof')
            elif isinstance(node,ast.ImportFrom):
                base=importlib.util.resolve_name('.'*node.level+(node.module or ''),module.rsplit('.',1)[0]) if node.level else node.module
                if base==SHARED:names.update(a.name for a in node.names)
                require(not(base=='uep_lyra_weapons' and any(a.name=='hero_burst_cue_mixin' for a in node.names)),'Whole changed Cue module alias is unsupported')
    require(names and names<={'lib','components','team'},'Only unchanged imported Cue helpers may bridge older evidence')
    old={n.name:n for n in ast.parse(before).body if isinstance(n,ast.FunctionDef)};new={n.name:n for n in ast.parse(after).body if isinstance(n,ast.FunctionDef)}
    for name in names:require(shape(old[name])==shape(new[name]),'Actually imported Cue helper changed: '+name)
    return sorted(names)

def spawning_equivalence(before,after):
    old,new=ast.parse(before),ast.parse(after);helper=[n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='mesh_target']
    expected=ast.parse("def mesh_target(actor):\n target=actor.get_property('TargetActor')\n return target if valid(target) else None\n").body[0]
    require(len(helper)==1 and shape(helper[0])==shape(expected),'Only the exact cached-target validity guard may be added')
    new.body.remove(helper[0]);counts={}
    class Restore(ast.NodeTransformer):
        def visit_FunctionDef(self,node):
            current=node.name
            for child in ast.walk(node):
                if isinstance(child,ast.Call) and isinstance(child.func,ast.Name) and child.func.id=='mesh_target':counts[current]=counts.get(current,0)+1
            return self.generic_visit(node)
        def visit_Call(self,node):
            if isinstance(node.func,ast.Name) and node.func.id=='mesh_target':
                require(len(node.args)==1 and isinstance(node.args[0],ast.Name) and node.args[0].id=='actor' and not node.keywords,'Unexpected cached-target guard call')
                return ast.parse("actor.get_property('TargetActor')",mode='eval').body
            return self.generic_visit(node)
    Restore().visit(new)
    require(counts==dict(spawn=1,colors=1,update=1,removal=1) and shape(old)==shape(new),'Spawning behavior changed beyond nullable mesh-target normalization')
    return 'valid-target-paths-identical;invalid-target-path-verified-by-native-batch250'

def dispatch_equivalence(before,after,macro):
    old,new=ast.parse(before),ast.parse(after);tree=ast.parse(macro)
    functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)};helper=functions['weapon_ammo']
    require(shape(helper.args)==shape(ast.parse('def weapon_ammo(actor):pass').body[0].args) and not helper.decorator_list and helper.returns is None,'Unexpected ammo helper signature')
    require(isinstance(helper.body[0],ast.Expr) and isinstance(helper.body[0].value,ast.Constant) and shape(helper.body[1])==shape(ast.parse("_calls['ammo']+=1").body[0]),'Only the known diagnostic counter may be ignored')
    require(shape(helper.body[-1])==shape(ast.parse('return True,ammo,False').body[0]),'Ammo completion tuple changed')
    assignments={n.targets[0].id:n.value for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
    require(shape(assignments['MAGAZINE'])==shape(ast.Constant('Lyra.ShooterGame.Weapon.MagazineAmmo')),'Magazine tag changed')
    body=copy.deepcopy(helper.body[2:-1])
    class Inline(ast.NodeTransformer):
        def visit_Name(self,node):return ast.Constant('Lyra.ShooterGame.Weapon.MagazineAmmo') if node.id=='MAGAZINE' else node
        def visit_Return(self,node):
            if shape(node)==shape(ast.parse('return False,0,False').body[0]):return ast.Return(value=None)
            require(shape(node)==shape(ast.parse('return False,0,True').body[0]),'Ammo helper error/exit tuple changed');return ast.Return(value=ast.Constant(True))
    body=[Inline().visit(n) for n in body]
    tag=next(n for n in body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='tag' for t in n.targets))
    require(shape(tag)==shape(ast.parse("tag=GameplayTag(TagName='Lyra.ShooterGame.Weapon.MagazineAmmo')").body[0]),'Only the constant native tag construction may move past the item guard')
    body.remove(tag);guard=ast.parse('if not valid(item):return True').body[0];positions=[i for i,n in enumerate(body) if shape(n)==shape(guard)]
    require(len(positions)==1,'Original invalid-item diagnostic exit changed');body.insert(positions[0],tag)
    imports=[n for n in new.body if isinstance(n,ast.ImportFrom) and n.level==1 and n.module is None and [(a.name,a.asname) for a in n.names]==[('macro_policies',None)]]
    require(len(imports)==1,'One exact macro import required');new.body.remove(imports[0])
    fn=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='sound_params')
    expected=ast.parse('completed,ammo,diagnostic=macro_policies.weapon_ammo(actor)\nif diagnostic:return True\nif not completed:return').body
    positions=[i for i in range(len(fn.body)-2) if [shape(n) for n in fn.body[i:i+3]]==[shape(n) for n in expected]]
    require(len(positions)==1,'Exactly the known ammo extraction block required');i=positions[0];fn.body[i:i+3]=body
    require(shape(old)==shape(new),'Audio dispatch changed beyond the source-equivalent ammo macro extraction')
    return 'native-ammo-macro-extraction-equivalent;diagnostic-counter-and-pure-constant-tag-allocation-only'

def verify_source(repo,summary,seeds,contexts):
    scripts=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts';files=closure(scripts,seeds);index=index_hashes(summary['hashes']);proofs={};changed={};macro_bridge=False
    for module,path in sorted(files.items()):
        rows=index.get(key(path),[])
        try:proofs[module]=dict(module=module,**source_guard(path,rows))
        except ValueError:changed[module]=(path,rows)
    for module,(path,rows) in sorted(changed.items()):
        if module==MACRO:continue
        old,history=historical_source(repo,path,rows);current=path.read_text(encoding='utf-8-sig')
        if module==SHARED:
            require(module not in seeds,'Changed Cue business needs its own native comparison')
            names=cue_helper_equivalence(old,current,files);bridge=imported_lib_bridge(old,current,(scripts/Path(*MACRO.split('.')).with_suffix('.py')).read_text(encoding='utf-8-sig'));macro_bridge='added_macro_import' in bridge
            equivalence=dict(imported_functions=names,**bridge)
        elif module==SPAWNING:
            require(contexts['destroyed_target_native_guard']==sha(path),'Current destroyed-target native proof required')
            fixture=scripts/'uep_lyra_weapons/spawning_cue_validation.py';source_guard(fixture,index.get(key(fixture),[]))
            pair=next(n for c in ast.parse(fixture.read_text(encoding='utf-8-sig')).body if isinstance(c,ast.ClassDef) and c.name=='Validation' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='pair')
            calls=[n for n in ast.walk(pair) if isinstance(n,ast.Call)];destroy=[n.lineno for n in calls if any(isinstance(a,ast.Constant) and a.value=='K2_DestroyActor' for a in n.args)];remove=[n.lineno for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='remove'];end=[n.lineno for n in calls if any(isinstance(a,ast.Constant) and a.value=='K2_EndGameplayCue' for a in n.args)]
            require(len(destroy)==1 and remove and end and max(remove)<min(end)<destroy[0],'Historical normal fixtures must remove/end Cues before destroying their owned targets')
            equivalence=dict(equivalence=spawning_equivalence(old,current),normal_fixture_source_guarded=True,normal_fixture_destroys_targets_after_removal=True)
        elif module==DISPATCH:
            equivalence=dict(equivalence=dispatch_equivalence(old,current,(scripts/Path(*MACRO.split('.')).with_suffix('.py')).read_text(encoding='utf-8-sig')),macro_native_proof=contexts['macro_native_directory']);macro_bridge=True
        else:raise ValueError('Changed effect checkpoint dependency needs native evidence: '+module)
        proofs[module]=dict(module=module,current_sha256=sha(path),**history,**equivalence)
    if MACRO in changed:
        path,rows=changed[MACRO];require(not rows and macro_bridge and contexts['macro_native_guard']==sha(path),'Missing macro inputs require the exact separately tested current macro source')
        proofs[MACRO]=dict(module=MACRO,current_sha256=sha(path),equivalence='added-import-tested-against-native-original-macro-matrix',native_directory=contexts['macro_native_directory'])
    return [proofs[n] for n in sorted(proofs)]

def checkpoint_assets(current):
    rows=[r for r in current['assets'] if r['version']=='0.12.0' and '/Bot/' not in r['path'] and '/ControlPoint/AI/' not in r['path']]
    require(len(rows)==63 and len({r['path'] for r in rows})==63,'Exact63 original non-AI0.12 candidates required')
    return rows

def inspect(repo,current,initial):
    repo=Path(repo).resolve();migration=repo/'Demos/UEPLyraIntegration/Migration';scripts=migration.parent/'Overlay/Content/Scripts';candidate_path=migration/'candidate_dispositions.json';candidate=read(candidate_path)
    census=verify_candidates(candidate,current,initial,repo);scope=checkpoint_assets(current)
    census_ledger=read(repo/candidate['evidence_paths']['native_ledger']);coverage=read(repo/census_ledger['runs'][0]['directory']/'audit.json');by_asset={r['asset']:r for r in coverage['assets']};jobs=[]
    for number,name,seeds in SPECS:
        ledger_path=next((migration/'Acceptance').glob(str(number)+'-*.json'));ledger=read(ledger_path)
        records=[r for r in ledger.get('native_runs',ledger.get('runs',[])) if Path(r['directory']).name==name];require(len(records)==1,'One exact native checkpoint record required')
        record=records[0];folder=repo/record['directory'];summary_path=folder/'summary.json';require(sha(summary_path)==record['summary_sha256'],'Pinned checkpoint summary changed')
        summary=read(summary_path);count=process_gate(summary);args=summary['external_gate']['arguments'];target=next(a for a in args if str(a).endswith(('_contract','_contract.py')))
        if target.endswith('.py'):target='uep_lyra_weapons.'+Path(target).stem
        require(target.startswith(('uep_lyra_weapons.','uep_lyra_audio.','uep_lyra_hud.','uep_lyra_world.')),'Unknown checkpoint contract namespace')
        report_path=Path(args[args.index('--report')+1]);require(report_path.resolve().is_relative_to(folder.resolve()),'Native report escaped its recorded directory')
        require(sha(report_path)==report_pin(ledger,record,Path(record['directory']),report_path.name),'Pinned native report changed')
        log=Path(next(a.split('=',1)[1] for a in summary['process']['arguments'] if a.startswith('-abslog=')));require(log.resolve().is_relative_to(folder.resolve()),'Native log escaped its recorded directory')
        text=log.read_text(encoding='utf-8-sig');raw=read(report_path);contract=importlib.import_module(target)
        gate=contract.validate(raw,text) if target.endswith('game_phases_contract') else contract.validate(raw)
        markers=set(re.findall(r'(UEP_[A-Z0-9_]+)_DIFFERENTIAL_PASSED',text)) & set(re.findall(r'(UEP_[A-Z0-9_]+)_SHUTDOWN_PASSED',text));require(markers,'No completed native checkpoint observer')
        for marker in markers:log_gate(text,marker)
        contract_path=scripts/Path(*target.split('.')).with_suffix('.py');index=index_hashes(summary['hashes']);contract_guard=source_guard(contract_path,index.get(key(contract_path),[]))
        jobs.append(dict(batch=number,directory=record['directory'],policy_modules=list(seeds),ledger=ledger_path.relative_to(repo).as_posix(),ledger_sha256=sha(ledger_path),summary_sha256=sha(summary_path),report_sha256=sha(report_path),log_sha256=sha(log),report_file=report_path.name,contract=target,contract_guard=contract_guard,semantic_gate=gate,markers=sorted(markers),native_processes=count,_summary=summary,_index=index,_raw=raw))
    macro=next(j for j in jobs if j['batch']==141 and j['contract'].endswith('macro_closure_contract'));destroyed=next(j for j in jobs if j['contract'].endswith('spawning_destroyed_target_contract'))
    require(macro['semantic_gate']['ammo_cases']==5 and macro['semantic_gate']['weapon_cases']==7 and macro['semantic_gate']['tag_cases']==4 and macro['semantic_gate']['specific_cases']==3,'Full original macro comparison required')
    require(destroyed['semantic_gate']['native_target_destructions']==4 and destroyed['semantic_gate']['paired_native_cases']==2,'Both destroyed-target native boundary comparisons required')
    macro_path=scripts/Path(*MACRO.split('.')).with_suffix('.py');spawn_path=scripts/Path(*SPAWNING.split('.')).with_suffix('.py')
    source_guard(macro_path,macro['_index'].get(key(macro_path),[]));source_guard(spawn_path,destroyed['_index'].get(key(spawn_path),[]))
    contexts=dict(macro_native_directory=macro['directory'],macro_native_guard=sha(macro_path),destroyed_target_native_guard=sha(spawn_path))
    for job in jobs:job['current_source_guards']=verify_source(repo,job['_summary'],job['policy_modules'],contexts)
    asset_guards=[]
    static={
        '/Game/Audio/Blueprints/GeneralAudioFunctions.GeneralAudioFunctions':{111},
        '/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions':{100,101,102,106,141},
        '/Game/Audio/Blueprints/WeaponAudioMacros.WeaponAudioMacros':{141},
        '/ShooterCore/Blueprint/Macros/BPML_VFXMacros.BPML_VFXMacros':{141},
    }
    for candidate_row in scope:
        asset=candidate_row['path'];row=by_asset[asset];modules={(v.get('python_class') or '').rsplit('.',1)[0] for v in row.get('profiles',{}).values()}
        options=[j for j in jobs if modules.intersection(j['policy_modules']) or j['batch'] in static.get(asset,set())];require(options,'Native family proof missing for candidate: '+asset)
        guards=[]
        for value in (asset,row.get('mixin_set')):
            if not value:continue
            relative=relative_asset(value,Path('F:/LyraStarterGame'));path=repo/'Demos/UEPLyraIntegration/Overlay'/relative
            if not path.is_file():path=Path('F:/LyraStarterGame')/relative
            matches=[]
            for job in options:
                rows=job['_index'].get(key(path),[]);native_paths=[]
                if not rows:
                    project=Path(job['_summary']['process']['arguments'][0]);require(project.name=='LyraStarterGame.uproject' and project.resolve().is_relative_to(repo/'.build'),'Isolated recorded Lyra project required')
                    rows=job['_index'].get(key(project.parent/relative),[]);native_paths=[r['path'] for r in rows];rows=[dict(r,path=str(path)) for r in rows]
                if not rows:continue
                try:proof=source_guard(path,rows)
                except ValueError:continue
                matches.append(dict(directory=job['directory'],recorded_stage_asset_paths=native_paths,**proof))
            require(matches,'Current candidate/transport asset differs from every corresponding native family run: '+value)
            guards.append(dict(asset=value,current_path=str(path),matching_native_fingerprints=matches))
        asset_guards.append(dict(asset=asset,version='0.12.0',effective_policy_modules=sorted(m for m in modules if m),guards=guards,retained_static_definition_or_forwarder=asset in static))
    phases=[j['_raw'] for j in jobs if j['contract'].endswith('game_phases_contract')]
    require({r['profile'] for r in phases}=={'BlueprintFallback','Python'} and all(r['countdown_messages'] and r['actual_server_travel_and_second_natural_round'] for r in phases),'Paired full warmup/playing/postgame and native restart required')
    style=[j['_raw'] for j in jobs if j['contract'].endswith('scoreboard_style_contract')];require({r['mode'] for r in style}=={'tdm','cp'},'Both scoring/presentation mode checkpoints required')
    for j in jobs:
        for k in ('_summary','_index','_raw'):j.pop(k)
    return dict(schema_version=1,status='passed',criterion=REQUIREMENT,completion_proven=True,version='0.12.0',original_version_candidates=75,ai_candidates_separately_reviewed=12,checkpoint_candidates=63,
        source_candidate_guard=dict(path=candidate_path.relative_to(repo).as_posix(),sha256=sha(candidate_path),**census),candidate_asset_guards=asset_guards,native_runs=jobs,
        referenced_native_processes=sum(j['native_processes'] for j in jobs),native_checkpoint_runs=len(jobs),original_macro_cases=19,native_destroyed_target_comparison_pairs=2,source_refactors_explicitly_bounded=True,
        current_sdk_used_for_every_historical_checkpoint=False,new_native_processes_launched_by_review=0,physical_audio_output_tested_by_review=False,all63_candidates_pixels_refreshed=False,
        cpp_compile_executed=False,cook_package_executed=False,full_regression_executed=False,full_version_acceptance=False,full_migration_acceptance_proven=False)

def verify_documentation(document,current,initial,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original effect/audio/phase/scoring/notification criterion required')
    expected=inspect(repo,current,initial);require(document['review']==expected,'Effect checkpoint review differs from current pinned native/source evidence')
    return {k:expected[k] for k in ('status','criterion','checkpoint_candidates','native_checkpoint_runs','referenced_native_processes','new_native_processes_launched_by_review','full_migration_acceptance_proven')}
