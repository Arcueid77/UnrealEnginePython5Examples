import copy,unittest
from uep_lyra_hud.explorer_screens_contract import FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,primary_player_inventory_and_health_unchanged=True,original_layer_widgets_and_transition_restored=True,owned_widgets_roots_profiles_and_class_selectors_restored=True,cases=[]);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for kind in ('inventory','map'):
        for profile in ('BlueprintFallback','Python'):
            row=dict(kind=kind,profile=profile,counts=dict(python=int(profile=='Python'),fallback=int(profile=='BlueprintFallback')));row.update(dict.fromkeys(('natural_native_activation','native_deactivation_callback_once','removed_from_native_layer','repeat_deactivation_no_extra_callback','unstacked_deactivation_safe','original_stack_widgets_preserved'),True));r['cases'].append(row)
    return r
class ExplorerScreenContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_screen_cases'],4)
    def test_missing_profile_rejected(self):
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_repeat_callback_rejected(self):
        r=report();r['cases'][0]['counts']['fallback']=2
        with self.assertRaises(RuntimeError):validate(r)
    def test_failed_native_layer_observations_rejected(self):
        for field in ('removed_from_native_layer','unstacked_deactivation_safe','original_stack_widgets_preserved'):
            r=report();r['cases'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_cleanup_failure_rejected(self):
        r=report();r['original_layer_widgets_and_transition_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_full_acceptance_overclaim_rejected(self):
        r=report();r['full_acceptance']=True
        with self.assertRaises(RuntimeError):validate(r)
