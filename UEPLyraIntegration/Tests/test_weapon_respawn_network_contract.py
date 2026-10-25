import ast,copy,importlib.util,json,tempfile,types,unittest
from pathlib import Path
from uep_lyra_weapons.weapon_respawn_network_contract import validate,validate_all,FORBIDDEN
from uep_lyra_hud.startup import validation_module
spec=importlib.util.spec_from_file_location('respawn_comparison',Path(__file__).resolve().parents[1]/'Tools/compare_weapon_respawn_runs.py')
comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)

def fixture(peer='server',profile='Python',attacker='A'):
    victim='B0' if attacker=='A' else 'A'
    roster={p:dict(player_id=i,state_wire='s'+p,pawn_wire='p'+p,name=p,team=i) for i,p in enumerate(('A','B0'))}
    states={p:dict(state_wire='s'+p,pawn_wire='p'+p+('new' if p==victim else ''),native_class='native-hero',health=100.,attribute_health=100.,death_state=0,asc_bound=True,profile=profile) for p in ('A','B0')}
    for row in states.values():row['avatar_wire']=row['pawn_wire']
    events=[dict(kind=k,source_wire='p'+victim+'new',profile=profile,authority=peer=='server') for k in ('activate','target-data')]
    row=dict(roster=roster,after_respawn=copy.deepcopy(states),after_new_life_fire=copy.deepcopy(states),authored_target_score=50,target_score_at_arm=50,
        death=dict(observed=True,health=0.,zero_health_observed=True,pawn_wire='p'+victim),old_pawn_end_play_observed=True,old_victim_class='native-hero',postgame_active=False,playing_active=True,phase_state_authoritative=peer=='server',
        score_delta=dict(kills=1,deaths=1,team=1,other=0),respawn_seconds=5.,foreign_inventory_sampled=False,
        new_life_fire=dict(definition_is_pistol=True,ammo_before=18,ammo_after=17,activation_entries=1,target_data_entries=1,events=events,gestures=1,input_released=True),
        first_kill_fire=dict(ammo_before=18,ammo_after=13,gestures=5,activation_events=[dict(source_wire='p'+attacker,profile=profile,authority=peer=='server')],target_data_events=[dict(source_wire='p'+attacker,profile=profile,authority=peer=='server',target_hits=5)]))
    report=dict(status='passed',error=None,peer=peer,run_id='one',requested_profile=profile,attacker_peer=attacker,victim_peer=victim,result=row,native_weapon_damage_observed=True,server_waited_for_client_process_exit=True,
        observer_scopes_closed=True,profile_classes_restored=True,probe_roots_removed=True,boot_selectors_restored=True,weapon_input_released=True,weapon_profile_classes_restored=True,respawn_scope_closed=True)
    report.update(dict.fromkeys(FORBIDDEN,False));return report

class NaturalRespawnContractTests(unittest.TestCase):
    def comparison_inputs(self,root):
        paths=[]
        for profile in ('Python','BlueprintFallback'):
            for owner in ('A','B0'):
                path=root/(profile+owner);path.mkdir();paths.append(path);run=profile+owner
                summary=dict(status='passed',external_gate=dict(exit_code=0),processes={p:dict(exit_code=0) for p in ('server','A','B0')},profile=profile,attacker_peer=owner,run_id=run,hashes=[])
                (path/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
                for peer in ('server','A','B0'):
                    r=fixture(peer,profile,owner);r['run_id']=run;(path/(peer+'.json')).write_text(json.dumps(r),encoding='utf-8')
        return paths
    def test_both_profiles_all_actual_peers(self):
        for profile in ('Python','BlueprintFallback'):
            for attacker in ('A','B0'):
                for peer in ('server','A','B0'):self.assertEqual(validate(fixture(peer,profile,attacker))['status'],'passed')
    def test_three_peer_identity_and_ammo_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for peer in ('server','A','B0'):(root/(peer+'.json')).write_text(json.dumps(fixture(peer)),encoding='utf-8')
            self.assertEqual(validate_all(root)['natural_human_respawns'],1)
    def test_old_pawn_cannot_be_reused_as_respawn(self):
        r=fixture();r['result']['after_respawn']['B0'].update(pawn_wire='pB0',avatar_wire='pB0')
        with self.assertRaises(Exception):validate(r)
    def test_native_class_identity_change_rejected(self):
        r=fixture();r['result']['after_respawn']['B0']['native_class']='replacement-class'
        with self.assertRaises(Exception):validate(r)
    def test_missing_health_or_asc_binding_rejected(self):
        for key,value in [('health',0.),('attribute_health',0.),('asc_bound',False),('avatar_wire','old'),('death_state',1)]:
            r=fixture();r['result']['after_respawn']['B0'][key]=value
            with self.assertRaises(Exception):validate(r)
    def test_foreign_state_or_survivor_replacement_rejected(self):
        for owner,key,value in [('B0','state_wire','sA'),('A','pawn_wire','another')]:
            r=fixture();r['result']['after_respawn'][owner][key]=value
            with self.assertRaises(Exception):validate(r)
    def test_every_forbidden_shortcut_rejected(self):
        for key in FORBIDDEN:
            r=fixture();r[key]=True
            with self.assertRaises(Exception):validate(r)
    def test_profile_mismatch_and_missing_old_endplay_rejected(self):
        r=fixture();r['result']['after_respawn']['B0']['profile']='BlueprintFallback'
        with self.assertRaises(Exception):validate(r)
        r=fixture();r['result']['old_pawn_end_play_observed']=False
        with self.assertRaises(Exception):validate(r)
    def test_winning_postgame_fixture_is_not_natural_respawn(self):
        for key,value in [('target_score_at_arm',1),('postgame_active',True),('playing_active',False)]:
            r=fixture();r['result'][key]=value
            with self.assertRaises(Exception):validate(r)
    def test_synthetic_counts_or_wrong_new_life_input_rejected(self):
        for key,value in [('ammo_after',16),('activation_entries',5),('target_data_entries',0)]:
            r=fixture();r['result']['new_life_fire'][key]=value
            with self.assertRaises(Exception):validate(r)
        r=fixture();r['result']['new_life_fire']['events'][0]['source_wire']='pB0'
        with self.assertRaises(Exception):validate(r)
    def test_first_life_damage_and_input_provenance_required(self):
        r=fixture();r['result']['first_kill_fire']['target_data_events'][0]['target_hits']=0
        with self.assertRaises(Exception):validate(r)
    def test_server_must_wait_for_actual_client_exits(self):
        r=fixture();r['server_waited_for_client_process_exit']=False
        with self.assertRaises(Exception):validate(r)
    def test_client_death_notification_can_precede_zero_health_replication(self):
        r=fixture('A');r['result']['death']['health']=10.;r['result']['playing_active']=False
        self.assertEqual(validate(r)['status'],'passed')
        r['result']['death']['zero_health_observed']=False
        with self.assertRaises(Exception):validate(r)
    def test_authority_death_requires_actual_zero_health_at_callback(self):
        r=fixture();r['result']['death']['health']=10.
        with self.assertRaises(Exception):validate(r)
    def test_authority_cleanup_waits_for_every_peer_result_snapshot(self):
        path=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/weapon_respawn_network_validation.py'
        tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        method=next(node for cls in tree.body if isinstance(cls,ast.ClassDef) and cls.name=='Network'
            for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='snapshot_tick')
        writes=[];namespace={'atomic_write':lambda path,data:writes.append((path,data))}
        exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
        tokens={'captured-server.json','captured-A.json'};cleanup=[]
        probe=types.SimpleNamespace(token=lambda name:name in tokens,cleanup=lambda:cleanup.append(True),
            report={'status':'running'},root=Path('owned'),peer='server',run='same-run',stage='snapshot-barrier')
        namespace['snapshot_tick'](probe)
        self.assertEqual((cleanup,writes,probe.stage),([],[],'snapshot-barrier'))
        tokens.add('captured-B0.json');namespace['snapshot_tick'](probe)
        self.assertEqual(cleanup,[True]);self.assertEqual(probe.report['status'],'awaiting_release')
        self.assertEqual(writes,[(Path('owned/ready-server.json'),{'run_id':'same-run'})])
        self.assertEqual(probe.stage,'release')
    def test_only_explicit_natural_respawn_flag_selects_probe(self):
        self.assertEqual(validation_module(['-UEPWeaponRespawnNetworkResult=owned.json']),'uep_lyra_weapons.weapon_respawn_network_validation')
        for arguments in ([],['-game'],['-UEPWeaponRespawnNetworkResult'],['-run=Py','-UEPWeaponRespawnNetworkResult=owned.json']):
            self.assertIsNone(validation_module(arguments))
    def test_both_owner_original_python_semantic_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.comparison_inputs(Path(directory));self.assertEqual(comparison.compare(paths,verify_frozen=False)['natural_human_respawns'],4)
    def test_missing_owner_or_duplicate_capture_cannot_prove_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.comparison_inputs(Path(directory))
            with self.assertRaises(ValueError):comparison.compare(paths[:3],verify_frozen=False)
            with self.assertRaises(ValueError):comparison.compare(paths[:3]+[paths[0]],verify_frozen=False)
    def test_changed_new_inventory_default_breaks_original_python_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.comparison_inputs(Path(directory));target=paths[0]
            for peer in ('server','A','B0'):
                p=target/(peer+'.json');r=json.loads(p.read_text());r['result']['new_life_fire'].update(ammo_before=10,ammo_after=9);p.write_text(json.dumps(r),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'outcome differs'):comparison.compare(paths,verify_frozen=False)
    def test_driver_profile_mismatch_or_failed_process_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.comparison_inputs(Path(directory));p=paths[0]/'summary.json';s=json.loads(p.read_text());s['profile']='wrong';p.write_text(json.dumps(s),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'driver/report'):comparison.compare(paths,verify_frozen=False)

if __name__=='__main__':unittest.main()
