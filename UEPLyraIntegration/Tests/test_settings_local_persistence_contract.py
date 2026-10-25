import copy,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from uep_lyra_hud.settings_local_persistence_contract import FORBIDDEN,validate,validate_pair,compare
from uep_lyra_hud.startup import validation_module
class LocalSettingsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def fixture(self,profile='Python',mode='write'):
        initial,saved=(1.,.5) if mode=='write' else (.5,1.);snapshot=self.root/(profile+'-'+mode+'.txt')
        data=('[/Script/LyraGame.LyraSettingsLocal]\nOverallVolume='+str(saved)+'\n').encode();snapshot.write_bytes(data)
        user=self.root/(profile+'-user');path=user/'Saved/Config/WindowsEditor/GameUserSettings.ini'
        events=[dict(entry='SSlider.OnMouseButtonDown',handled=True,synthetic_pointer_up_sent=True,target=target,before=before,after=target,ui_value=target,material_progress=target,selected_callbacks=2,other_callbacks=0,native_geometry=[200.,40.]) for before,target in [(initial,saved),(initial,saved)]+([(saved,initial)] if mode=='write' else [])]
        report=dict(status='passed',error=None,profile=profile,mode=mode,setting='OverallVolume',native_mode='Standalone',native_store='LyraSettingsLocal/GameUserSettings.ini',
            owned_user_root=str(user),saved_path_owned=True,cancel_restores_initial=True,cancel_does_not_write_files=True,dirty_state_cleared=True,native_ini_saved=True,native_companion_save_complete=True,
            selectors_roots_widgets_restored=True,health_unchanged=True,initial=initial,saved=saved,native_pointer_events=events,
            native_screen_baselines=[dict(initially_dirty=True,original_cancel_used=True,value_before=value,value_after=value,config_files_unchanged=True,clean_after_cancel=True) for value in ([initial,saved] if mode=='write' else [initial])],
            ini_files=[dict(path=str(path),value=saved,snapshot=str(snapshot),sha256=hashlib.sha256(data).hexdigest().upper())],
            same_process_reopen_keeps_saved=True,cancel_after_reopen_keeps_saved=True,fresh_process_loaded_saved=True,original_owned_value_restored=True)
        report.update(dict.fromkeys(FORBIDDEN,False));return report
    def directories(self):
        paths=[];frozen=self.root/'frozen.py';frozen.write_text('unchanged',encoding='utf-8')
        for profile in ('BlueprintFallback','Python'):
            for mode in ('write','read_restore'):
                path=self.root/(profile+'-'+mode);path.mkdir();paths.append(path)
                (path/'result.json').write_text(json.dumps(self.fixture(profile,mode)),encoding='utf-8')
                summary=dict(status='passed',profile=profile,mode=mode,process=dict(exit_code=0),external_gate=dict(exit_code=0),cpp_compile_executed=False,cook_package_executed=False,
                    hashes=[dict(path=str(frozen),sha256=hashlib.sha256(frozen.read_bytes()).hexdigest().upper())])
                (path/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
        return paths
    def test_native_write_read_restore_pair(self):validate_pair(self.fixture(mode='write'),self.fixture(mode='read_restore'))
    def test_opt_in_entry_excludes_normal_play_and_commandlets(self):
        flag='-UEPSettingsLocalResult=owned.json';self.assertEqual(validation_module([flag]),'uep_lyra_hud.settings_local_persistence_validation')
        for args in ([],['-game'],['-UEPSettingsLocalResult'],['-run=Py',flag]):self.assertIsNone(validation_module(args))
    def test_model_or_file_setter_and_replayed_callbacks_rejected(self):
        for key in FORBIDDEN:
            r=self.fixture();r[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_slider_native_data_source_and_material_must_agree(self):
        for key,value in [('handled',False),('after',.8),('ui_value',1.),('material_progress',0.),('selected_callbacks',0),('other_callbacks',1)]:
            r=self.fixture();r['native_pointer_events'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_cancel_save_and_cleanup_boundaries(self):
        for key in ('cancel_restores_initial','cancel_does_not_write_files','dirty_state_cleared','native_ini_saved','native_companion_save_complete','selectors_roots_widgets_restored','health_unchanged'):
            r=self.fixture();r[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_initial_cancel_cannot_change_loaded_value_or_config(self):
        for key,value in [('value_after',.5),('config_files_unchanged',False),('clean_after_cancel',False),('original_cancel_used',False)]:
            r=self.fixture();r['native_screen_baselines'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_snapshot_hash_and_native_ini_value_verified(self):
        r=self.fixture();p=Path(r['ini_files'][0]['snapshot']);p.write_text('changed')
        with self.assertRaises(ValueError):validate(r)
        r=self.fixture();data=b'[/Script/LyraGame.LyraSettingsLocal]\nOverallVolume=0.2\n';p.write_bytes(data);r['ini_files'][0]['sha256']=hashlib.sha256(data).hexdigest().upper()
        with self.assertRaises(ValueError):validate(r)
    def test_unowned_native_store_and_nonfinite_value_rejected(self):
        r=self.fixture();r['ini_files'][0]['path']=str(self.root/'other/GameUserSettings.ini')
        with self.assertRaises(ValueError):validate(r)
        r=self.fixture();r['saved']=float('nan')
        with self.assertRaises(ValueError):validate(r)
    def test_fresh_read_requires_saved_value_same_profile_and_store(self):
        for key,value in [('initial',1.),('profile','BlueprintFallback'),('owned_user_root',str(self.root/'other'))]:
            a=self.fixture();b=self.fixture(mode='read_restore');b[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_pair(a,b)
    def test_complete_four_process_comparison(self):self.assertEqual(compare(self.directories())['native_pointer_changes'],10)
    def test_native_callback_multiplicity_must_match_between_profiles(self):
        paths=self.directories();p=paths[2]/'result.json';r=json.loads(p.read_text());r['native_pointer_events'][0]['selected_callbacks']+=1;p.write_text(json.dumps(r))
        with self.assertRaises(ValueError):compare(paths)
    def test_missing_duplicate_failed_or_changed_native_input_rejected(self):
        paths=self.directories()
        for cases in (paths[:3],[paths[0],paths[0],paths[2],paths[3]]):
            with self.assertRaises(ValueError):compare(cases)
        p=paths[0]/'summary.json';r=json.loads(p.read_text());r['process']['exit_code']=1;p.write_text(json.dumps(r))
        with self.assertRaises(ValueError):compare(paths)
        r['process']['exit_code']=0;p.write_text(json.dumps(r));(self.root/'frozen.py').write_text('changed')
        with self.assertRaises(ValueError):compare(paths)
    def test_independent_report_cli(self):
        path=self.root/'report.json';path.write_text(json.dumps(self.fixture()),encoding='utf-8')
        result=subprocess.run([sys.executable,'-B','-X','utf8','-m','uep_lyra_hud.settings_local_persistence_contract','--report',str(path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
