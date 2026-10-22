import unittest
from uep_lyra_hud.settings_persistence_contract import validate,validate_pair
from uep_lyra_hud.startup import validation_module


def report(mode='write'):
    result=dict(status='passed',profile='Python',setting='GamepadVibration',mode=mode,owned_user_root='Owned/User',
        saved_path_owned=True,native_button_handler_calls=3,effective_profiles_match=True,selected_profile_callback_entries=3,cancel_restores_initial=True,cancel_does_not_write_files=True,
        native_async_save_success=True,dirty_state_cleared=True,selectors_roots_widgets_restored=True,health_unchanged=True,
        direct_settings_setter_called=False,configuration_files_written_by_python=False,physical_keyboard_or_pointer_tested=False,
        full_acceptance=False,initial=1,saved=0,save_files=[dict(path='Owned/User/Saved/SaveGames/SharedGameSettings.sav',sha256='test')])
    if mode=='write':result.update(same_process_reopen_keeps_saved=True,cancel_after_reopen_keeps_saved=True)
    else:result.update(initial=0,saved=1,fresh_process_loaded_saved=True,original_owned_value_restored=True)
    return result


class SettingsPersistenceContractTests(unittest.TestCase):
    def test_runtime_entry_is_explicit_and_excludes_commandlets(self):
        flag='-UEPSettingsPersistenceResult=owned/result.json'
        self.assertEqual(validation_module([flag]),'uep_lyra_hud.settings_persistence_validation')
        self.assertIsNone(validation_module(['-run=Py',flag]))
        self.assertIsNone(validation_module([]))

    def test_actual_save_and_restore_pair_contract(self):
        validate_pair(report(),report('read_restore'))

    def test_cancel_that_saves_or_does_not_restore_is_rejected(self):
        for field in ('cancel_restores_initial','cancel_does_not_write_files'):
            value=report();value[field]=False
            with self.subTest(field=field),self.assertRaises(AssertionError):validate(value)

    def test_direct_file_or_model_setter_cannot_prove_ui(self):
        for field in ('direct_settings_setter_called','configuration_files_written_by_python'):
            value=report();value[field]=True
            with self.subTest(field=field),self.assertRaises(AssertionError):validate(value)

    def test_save_outside_owned_directory_is_rejected(self):
        value=report();value['save_files'][0]['path']='Other/User/SharedGameSettings.sav'
        with self.assertRaises(AssertionError):validate(value)

    def test_failed_native_save_or_cleanup_is_rejected(self):
        for field in ('native_async_save_success','selectors_roots_widgets_restored'):
            value=report();value[field]=False
            with self.subTest(field=field),self.assertRaises(AssertionError):validate(value)

    def test_fresh_process_must_read_prior_saved_value(self):
        value=report('read_restore');value.update(initial=1,saved=0)
        with self.assertRaises(AssertionError):validate_pair(report(),value)

    def test_profile_label_without_callback_evidence_is_rejected(self):
        value=report();value['selected_profile_callback_entries']=0
        with self.assertRaises(AssertionError):validate(value)
