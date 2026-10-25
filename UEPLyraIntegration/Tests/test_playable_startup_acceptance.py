import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'Tools'),str(BASE/'Overlay/Content/Scripts')]
import audit_playable_startup_acceptance as audit
from audit_migration_acceptance import attach_playable_startup_review

def fixture():
    normal=dict(status='passed',no_validation_flags=True,native_experience_loaded=True,intentional_owned_process_stop=True,graceful_exit_tested=False,alive_observation_seconds=20,process=dict(arguments=['Lyra.uproject','-game','-NullRHI'],pid=2,exit_code=-1,duration_seconds=40.))
    child=dict(status='passed',error=None,process=dict(exit_code=0,pid=1,arguments=['Lyra.uproject','-game','-RenderOffscreen']),playable_startup=normal)
    final=dict(active_count=0,active_scopes=0,ticker_active=False,subscribed=1,unsubscribed=1,errors=[])
    report=dict(status='passed',cases=[{}]*42,declarations=[{}]*4,restored_classes=4,class_identity_preserved=True,full_acceptance=False,network_acceptance=False,shutdown=dict(phase='python_atexit',owned_resources_closed_before_exit=True),reload_cycles=[dict(status='passed',native_gc_collected=True,python_housekeeper_gc_executed=True,after=dict(final)) for _ in range(3)])
    normal_log='UEP_LYRA_SCRIPT_LOADED\nUEP_LYRA_PLAYABLE_BOOTSTRAP_READY\nUEP_LYRA_WEAPON_HUD_REGISTERED 4\nOnExperienceLoadComplete'
    focused_log='UEP_WEAPON_HUD_DIFFERENTIAL_PASSED\nGoodbye Python\nUEP_WEAPON_HUD_SHUTDOWN_PASSED\nLog file closed'
    return child,report,normal_log,focused_log

class PlayableStartupAcceptanceTests(unittest.TestCase):
    def test_all_real_selector_returns_are_explicit_without_running_any_probe(self):
        source=(BASE/'Overlay/Content/Scripts/uep_lyra_hud/startup.py').read_text(encoding='utf-8-sig');catalogue,select=audit.selector_catalogue(source)
        self.assertGreater(len(catalogue['explicit_flag_literals']),100);self.assertIsNone(select(['-game']))
        self.assertEqual(select(['-UEPLyraWeaponHUDResult=result.json']),'uep_lyra_hud.weapon_validation')
    def test_default_probe_or_a_non_test_or_branch_cannot_be_accepted(self):
        for source in ("def validation_module(arguments):return 'uep_probe'\n","def validation_module(arguments):\n if '-UEPTest' in arguments or '-game' in arguments:return 'uep_probe'\n return None\n","def validation_module(arguments):\n if '-UEPTest' in ('-UEPTest',):return 'uep_probe'\n return None\n","print('side effect')\ndef validation_module(arguments):return None\n"):
            with self.assertRaises(ValueError):audit.selector_catalogue(source)
    def test_conditional_modules_still_need_a_guarded_return_path(self):
        source="def validation_module(arguments):\n if '-UEPTest' in arguments:return 'uep_a' if '-UEPVariant' in arguments else 'uep_b'\n return None\n"
        catalogue,_=audit.selector_catalogue(source);self.assertEqual(catalogue['returned_module_count'],2)
    def test_outer_commandlet_guard_and_import_boundary_stay_exact(self):
        source=(BASE/'Overlay/Content/Scripts/ue_site.py').read_text(encoding='utf-8-sig');audit.site_guard(source)
        for changed in (source.replace('if is_commandlet:','if False:'),source+'ue.request_exit()\n'):
            with self.assertRaises(ValueError):audit.site_guard(changed)
    def test_normal_and_explicit_native_processes_have_distinct_exit_contracts(self):
        args=fixture();self.assertEqual(audit.report_gate(*args)['normal_intentional_owned_stop_exit_code'],-1)
        for field,value in (('intentional_owned_process_stop',False),('graceful_exit_tested',True),('alive_observation_seconds',0)):
            child,report,normal,focused=fixture();child['playable_startup'][field]=value
            with self.assertRaises(ValueError):audit.report_gate(child,report,normal,focused)
    def test_hidden_test_flag_exit_or_runtime_error_in_normal_play_is_rejected(self):
        for suffix in ('\nGoodbye Python','\nUEP_WEAPON_HUD_DIFFERENTIAL_PASSED','\nLogPython: Error: bad'):
            child,report,normal,focused=fixture()
            with self.assertRaises(ValueError):audit.report_gate(child,report,normal+suffix,focused)
        child,report,normal,focused=fixture();child['playable_startup']['process']['arguments'].append('-UEPTest')
        with self.assertRaises(ValueError):audit.report_gate(child,report,normal,focused)
    def test_probe_cleanup_and_ordered_native_exit_cannot_be_replaced_by_a_flag(self):
        child,report,normal,focused=fixture();report['reload_cycles'][-1]['after']['active_scopes']=1
        with self.assertRaises(ValueError):audit.report_gate(child,report,normal,focused)
        child,report,normal,focused=fixture()
        with self.assertRaises(ValueError):audit.report_gate(child,report,normal,focused.replace('Goodbye Python',''))
    def test_attachment_only_accepts_the_exact_original_startup_requirement(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'review.json';path.write_text('{}');rows=[dict(version='0.9.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.9.0',text='Packaged weapon example',completion_proven=False)];result=dict(requirements=rows,inputs=[])
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')):attach_playable_startup_review(result,folder,path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven']);self.assertFalse(rows[0]['full_migration_acceptance_proven'])
            rows[0]['text']='partial substitute'
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')),self.assertRaises(ValueError):attach_playable_startup_review(result,folder,path)
    def test_checked_metadata_alone_does_not_prove_normal_runtime(self):
        for value in (dict(criterion='partial',completion_proven=True),dict(criterion=audit.REQUIREMENT,completion_proven=False)):
            with self.assertRaises(ValueError):audit.verify_documentation(value,'.')
