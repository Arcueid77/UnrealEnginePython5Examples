import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from uep_lyra_hud.ui_back_navigation_contract import FORBIDDEN,validate,outcome,compare
from uep_lyra_hud.startup import validation_module
def fixture(profile='Python'):
    row=dict(native_push_entry='CommonUIExtensions.PushContentToLayer_ForPlayer',native_back_entry='CommonBoundActionButton.HandleButtonClicked',native_back_text='Back',
        menu_options_native_focus=True,settings_native_focus=True,screen_profile_matches=True,back_profile_matches=True,menu_inactive_after_settings_push=True,
        settings_closed_by_native_back=True,closed_settings_has_no_focus=True,world_unchanged=True,health_unchanged=True,
        menu_settings_selected_callbacks=1,menu_settings_other_callbacks=0,back_selected_click_callbacks=1,back_other_click_callbacks=0)
    result=dict(status='passed',error=None,profile=profile,native_mode='Standalone',owned_widgets_unmounted_and_unrooted=True,class_selectors_restored=True,class_roots_restored=True,health_unchanged=True,
        cases=[dict(row,profile=profile,cycle=i) for i in (0,1)])
    result.update(dict.fromkeys(FORBIDDEN,False));return result
class UIBackNavigationContractTests(unittest.TestCase):
    def test_both_profiles_and_reopen_cycles(self):
        self.assertEqual(validate(fixture())['native_back_actions'],2)
        self.assertEqual(outcome(fixture()),outcome(fixture('BlueprintFallback')))
    def test_opt_in_only_and_commandlets_excluded(self):
        flag='-UEPUIBackResult=owned.json';self.assertEqual(validation_module([flag]),'uep_lyra_hud.ui_back_navigation_validation')
        for args in ([],['-game'],['-UEPUIBackResult'],['-run=Py',flag]):self.assertIsNone(validation_module(args))
    def test_no_callback_focus_or_manual_close_shortcuts(self):
        for key in FORBIDDEN:
            r=fixture();r[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_actual_native_focus_and_back_outcomes_required(self):
        for key in ('menu_options_native_focus','settings_native_focus','screen_profile_matches','back_profile_matches','settings_closed_by_native_back','closed_settings_has_no_focus','world_unchanged','health_unchanged'):
            r=fixture();r['cases'][1][key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_selected_click_and_settings_routing_not_fallthrough(self):
        for key,value in (('menu_settings_selected_callbacks',0),('menu_settings_other_callbacks',1),('back_selected_click_callbacks',0),('back_other_click_callbacks',1)):
            r=fixture();r['cases'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_single_open_or_duplicate_profile_is_not_reopen_evidence(self):
        for rows in (fixture()['cases'][:1],fixture()['cases'][:1]*2):
            r=fixture();r['cases']=rows
            with self.assertRaises(ValueError):validate(r)
    def test_widget_and_class_cleanup_required(self):
        for key in ('owned_widgets_unmounted_and_unrooted','class_selectors_restored','class_roots_restored','health_unchanged'):
            r=fixture();r[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_pair_requires_distinct_clean_profiles_and_identical_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            for profile in ('BlueprintFallback','Python'):
                path=Path(directory)/profile;path.mkdir();paths.append(path)
                (path/'failure.json').write_text(json.dumps(fixture(profile)),encoding='utf-8')
                (path/'summary.json').write_text(json.dumps(dict(status='passed',profile=profile,process=dict(exit_code=0),external_gate=dict(exit_code=0),cpp_compile_executed=False,cook_package_executed=False,hashes=[])),encoding='utf-8')
            self.assertEqual(compare(paths,verify_frozen=False)['native_back_actions'],4)
            for pair in (paths[:1],[paths[0],paths[0]]):
                with self.assertRaises(ValueError):compare(pair,verify_frozen=False)
            p=paths[0]/'summary.json';r=json.loads(p.read_text());r['process']['exit_code']=1;p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):compare(paths,verify_frozen=False)
    def test_independent_report_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'result.json';path.write_text(json.dumps(fixture()),encoding='utf-8')
            result=subprocess.run([sys.executable,'-B','-X','utf8','-m','uep_lyra_hud.ui_back_navigation_contract','--report',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
