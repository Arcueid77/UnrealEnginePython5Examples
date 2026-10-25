import copy,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from uep_lyra_hud.settings_cancel_action_contract import FORBIDDEN,validate,compare
from uep_lyra_hud.startup import validation_module
def fixture(profile='Python'):
    baseline=dict(label='Cancel Changes',native_entry='CommonBoundActionButton.HandleButtonClicked',profile_matches=True,selected_clicks=1,other_clicks=0,value_before=1.,value_after=1.,files_unchanged=True,clean=True,screen_active=True)
    cancel=dict(baseline,value_before=.5,ui_after=1.,material_after=1.,files_before={'owned.ini':'same'},files_after={'owned.ini':'same'},cancel_action_removed=True)
    pointer=dict(entry='SSlider.OnMouseButtonDown',handled=True,selected_callbacks=2,other_callbacks=0,target=.5,after=.5,ui_value=.5,material_progress=.5)
    row=dict(initial=1.,target=.5,initially_dirty=True,baseline_cancel=baseline,pointer=pointer,cancel=cancel,menu_options_native_focus=True,settings_native_focus=True,
        native_back_after_cancel_closed=True,volume_still_original=True,world_unchanged=True,health_unchanged=True)
    report=dict(status='passed',error=None,profile=profile,native_mode='Standalone',saved_path_owned=True,cases=[dict(copy.deepcopy(row),profile=profile,cycle=i) for i in (0,1)],
        owned_widgets_unmounted_and_unrooted=True,class_selectors_restored=True,class_roots_restored=True,health_unchanged=True,scalar_fixture_unmounted_and_unrooted=True)
    report.update(dict.fromkeys(FORBIDDEN,False));return report
class SettingsCancelActionTests(unittest.TestCase):
    def test_actual_native_cancel_contract(self):self.assertEqual(validate(fixture())['native_dirty_cancel_actions'],2)
    def test_new_lane_is_opt_in(self):
        flag='-UEPSettingsCancelResult=owned.json';self.assertEqual(validation_module([flag]),'uep_lyra_hud.settings_cancel_action_validation')
        for args in ([],['-game'],['-UEPSettingsCancelResult'],['-run=Py',flag]):self.assertIsNone(validation_module(args))
    def test_direct_cancel_save_or_setting_setter_is_not_native_action(self):
        for key in FORBIDDEN:
            r=fixture();r[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_cancel_must_restore_native_value_ui_and_material_without_pop(self):
        for key,value in [('value_after',.5),('ui_after',.5),('material_after',.5),('screen_active',False),('clean',False),('cancel_action_removed',False),('selected_clicks',0),('other_clicks',1),('label','Apply Changes')]:
            r=fixture();r['cases'][0]['cancel'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_cancel_cannot_write_files_or_change_loaded_initial_value(self):
        r=fixture();r['cases'][0]['cancel']['files_after']['owned.ini']='changed'
        with self.assertRaises(ValueError):validate(r)
        r=fixture();r['cases'][0]['baseline_cancel']['value_after']=.5
        with self.assertRaises(ValueError):validate(r)
    def test_two_cycles_and_teardown_required(self):
        r=fixture();r['cases'].pop()
        with self.assertRaises(ValueError):validate(r)
        for key in ('scalar_fixture_unmounted_and_unrooted','class_selectors_restored','health_unchanged'):
            r=fixture();r[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_distinct_clean_native_profiles_and_matching_callbacks_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);frozen=root/'source.py';frozen.write_text('same');paths=[]
            for profile in ('BlueprintFallback','Python'):
                path=root/profile;path.mkdir();paths.append(path);(path/'failure.json').write_text(json.dumps(fixture(profile)),encoding='utf-8')
                summary=dict(status='passed',profile=profile,process=dict(exit_code=0),external_gate=dict(exit_code=0),cpp_compile_executed=False,cook_package_executed=False,hashes=[dict(path=str(frozen),sha256=hashlib.sha256(frozen.read_bytes()).hexdigest())])
                (path/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
            self.assertEqual(compare(paths)['native_dirty_cancel_actions'],4)
            with self.assertRaises(ValueError):compare([paths[0],paths[0]])
            p=paths[1]/'failure.json';r=json.loads(p.read_text());r['cases'][0]['pointer']['selected_callbacks']=3;p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):compare(paths)
    def test_report_cli_executes_semantic_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'report.json';p.write_text(json.dumps(fixture()),encoding='utf-8')
            result=subprocess.run([sys.executable,'-B','-X','utf8','-m','uep_lyra_hud.settings_cancel_action_contract','--report',str(p)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
