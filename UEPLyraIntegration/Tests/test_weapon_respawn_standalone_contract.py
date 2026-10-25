import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from uep_lyra_weapons.weapon_respawn_standalone_contract import FORBIDDEN,validate,semantic_result,compare_runs
from uep_lyra_hud.startup import validation_module

def fixture(profile='Python'):
    def state(name):return dict(pawn=name,player_state='same-state',native_class='retained-hero',health=100.,attribute_health=100.,death_state=0,
        native_role=3,asc_bound=True,avatar=name,profile=profile)
    def fire(name):return dict(pawn=name,definition_is_pistol=True,ammo_before=12,ammo_after=11,gestures=1,input_released=True,
        events=[dict(kind=k,source=name,profile=profile,authority=True) for k in ('activate','target-data')])
    result=dict(before_death=state('old'),after_respawn=state('new'),after_new_life_fire=state('new'),
        death=dict(observed=True,health=0.,pawn='old'),old_pawn_end_play_observed=True,respawn_seconds=5.,fires=[fire('old'),fire('new')],
        hazard=dict(world_bounds_enabled=True,kill_z=-1000.,kill_z_after=-1000.,world_bounds_enabled_after=True,placement_accepted=True,placed_z=-2000.))
    report=dict(status='passed',error=None,profile=profile,native_mode='Standalone',native_bot_controllers=0,result=result,
        observer_scope_closed=True,profile_classes_restored=True,boot_selectors_restored=True,probe_roots_removed=True,input_released=True)
    report.update(dict.fromkeys(FORBIDDEN,False));return report

class StandaloneRespawnContractTests(unittest.TestCase):
    def comparison_inputs(self,root):
        paths=[]
        for profile in ('Python','BlueprintFallback'):
            case=root/profile;case.mkdir();paths.append(case)
            (case/'respawn.json').write_text(json.dumps(fixture(profile)),encoding='utf-8')
            summary=dict(status='passed',profile=profile,process=dict(exit_code=0),external_gate=dict(exit_code=0),hashes=[],cpp_compile_executed=False,cook_package_executed=False)
            (case/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
        return paths
    def test_both_profiles_retain_equal_native_outcomes(self):
        self.assertEqual(semantic_result(fixture('Python')),semantic_result(fixture('BlueprintFallback')))
    def test_network_mode_is_not_standalone_evidence(self):
        for mode in ('DedicatedServer','Client'):
            r=fixture();r['native_mode']=mode
            with self.assertRaises(Exception):validate(r)
    def test_disabled_moved_or_nonfinite_world_bounds_rejected(self):
        for key,value in [('world_bounds_enabled',False),('world_bounds_enabled_after',False),('kill_z_after',0.),('kill_z',float('nan')),('placed_z',0.),('placement_accepted',False)]:
            r=fixture();r['result']['hazard'][key]=value
            with self.assertRaises(Exception):validate(r)
    def test_old_pawn_reuse_and_mid_fire_replacement_rejected(self):
        for key,value in [('after_respawn','old'),('after_new_life_fire','third')]:
            r=fixture();r['result'][key].update(pawn=value,avatar=value)
            with self.assertRaises(Exception):validate(r)
    def test_class_player_state_health_and_asc_boundaries(self):
        for key,value in [('native_class','other'),('player_state','other'),('health',0.),('attribute_health',0.),('asc_bound',False),('avatar','old'),('profile','BlueprintFallback'),('native_role',1)]:
            r=fixture();r['result']['after_respawn'][key]=value
            with self.assertRaises(Exception):validate(r)
    def test_native_zero_health_and_old_endplay_required(self):
        r=fixture();r['result']['death']['health']=10.
        with self.assertRaises(Exception):validate(r)
        r=fixture();r['result']['old_pawn_end_play_observed']=False
        with self.assertRaises(Exception):validate(r)
    def test_native_bot_isolation_required(self):
        r=fixture();r['native_bot_controllers']=1
        with self.assertRaises(Exception):validate(r)
    def test_each_forbidden_shortcut_rejected(self):
        for key in FORBIDDEN:
            r=fixture();r[key]=True
            with self.assertRaises(Exception):validate(r)
    def test_both_life_input_source_and_cost_required(self):
        for life in (0,1):
            for key,value in [('ammo_after',10),('gestures',0),('input_released',False),('pawn','foreign')]:
                r=fixture();r['result']['fires'][life][key]=value
                with self.assertRaises(Exception):validate(r)
            r=fixture();r['result']['fires'][life]['events'][0]['source']='foreign'
            with self.assertRaises(Exception):validate(r)
    def test_missing_native_target_data_and_missing_life_rejected(self):
        r=fixture();r['result']['fires'][1]['events'].pop()
        with self.assertRaises(Exception):validate(r)
        r=fixture();r['result']['fires'].pop()
        with self.assertRaises(Exception):validate(r)
    def test_cleanup_and_finite_respawn_bound_required(self):
        for key in ('observer_scope_closed','profile_classes_restored','boot_selectors_restored','probe_roots_removed','input_released'):
            r=fixture();r[key]=False
            with self.assertRaises(Exception):validate(r)
        r=fixture();r['result']['respawn_seconds']=float('inf')
        with self.assertRaises(Exception):validate(r)
    def test_explicit_probe_selection_only(self):
        self.assertEqual(validation_module(['-UEPWeaponRespawnStandaloneResult=owned.json']),'uep_lyra_weapons.weapon_respawn_standalone_validation')
        for args in ([],['-game'],['-UEPWeaponRespawnStandaloneResult'],['-run=Py','-UEPWeaponRespawnStandaloneResult=owned.json']):
            self.assertIsNone(validation_module(args))
    def test_two_profile_comparison_and_missing_duplicate_case_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.comparison_inputs(Path(directory))
            self.assertEqual(compare_runs(paths,verify_frozen=False)['standalone_natural_respawns'],2)
            with self.assertRaises(Exception):compare_runs(paths[:1],verify_frozen=False)
            with self.assertRaises(Exception):compare_runs([paths[0],paths[0]],verify_frozen=False)
    def test_failed_process_or_profile_mismatch_cannot_prove_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.comparison_inputs(Path(directory));p=paths[0]/'summary.json';summary=json.loads(p.read_text())
            summary['process']['exit_code']=1;p.write_text(json.dumps(summary),encoding='utf-8')
            with self.assertRaises(Exception):compare_runs(paths,verify_frozen=False)
            summary['process']['exit_code']=0;summary['profile']='BlueprintFallback';p.write_text(json.dumps(summary),encoding='utf-8')
            with self.assertRaises(Exception):compare_runs(paths,verify_frozen=False)
    def test_changed_default_inventory_breaks_native_outcome_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.comparison_inputs(Path(directory));p=paths[0]/'respawn.json';report=json.loads(p.read_text())
            for fire in report['result']['fires']:fire.update(ammo_before=10,ammo_after=9)
            p.write_text(json.dumps(report),encoding='utf-8')
            with self.assertRaises(Exception):compare_runs(paths,verify_frozen=False)
    def test_frozen_inputs_required_and_cli_report_gate_executes(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.comparison_inputs(Path(directory))
            with self.assertRaises(Exception):compare_runs(paths)
            result=subprocess.run([sys.executable,'-B','-X','utf8','-m','uep_lyra_weapons.weapon_respawn_standalone_contract','--report',str(paths[0]/'respawn.json')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['standalone_natural_respawns'],1)

if __name__=='__main__':unittest.main()
