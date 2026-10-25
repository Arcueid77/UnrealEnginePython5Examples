import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud import menu_travel_contract as travel,ui_travel_lifetime_contract as contract
from uep_lyra_hud.startup import validation_module

def report(profile='Python'):
    t=dict(status='passed',error=None,profile=profile,initial_native_mode='Standalone',confirmation_results=[0],menu_result_handler_calls=1,old_world_path='old',new_world_path=travel.MAP,native_experience_option=travel.EXPERIENCE,native_experience_class=travel.EXPERIENCE_CLASS,native_frontend_widget_class=travel.FRONTEND,native_frontend_profile=profile,native_primary_local_user_state=5)
    t.update(dict.fromkeys(travel.FALSE_FIELDS,False));t.update(dict.fromkeys(travel.TRUE_FIELDS,True))
    r=dict(status='passed',error=None,profile=profile,travel=t,cases=[]);r.update(dict.fromkeys(contract.FORBIDDEN,False))
    for origin in ('game','frontend'):
        for cycle in range(2):r['cases'].append(dict(origin=origin,cycle=cycle,profile=profile,parent_focus=True,settings_focus=True,parent_selected_callbacks=1,back_selected_callbacks=1,parent_other_callbacks=0,back_other_callbacks=0,screen_profile_matches=True,back_profile_matches=True,settings_closed=True,settings_focus_removed=True,settings_object=origin+'settings',controller=origin+'controller',world=t['old_world_path'] if origin=='game' else t['new_world_path']))
    r.update(dict.fromkeys(('old_ui_naturally_deactivated_before_probe_cleanup','old_travel_observers_unbound','old_travel_callbacks_quiet_after_new_ui','new_frontend_reactivated_after_back','owned_ui_unmounted_and_unrooted','selectors_and_class_roots_restored'),True));return r

class UITravelLifetimeContractTests(unittest.TestCase):
    def test_complete_both_profiles(self):
        for profile in travel.PROFILES:self.assertEqual(contract.validate(report(profile))['native_settings_cycles'],4)
    def test_missing_reordered_or_duplicate_cycle_rejected(self):
        for rows in (report()['cases'][:2],report()['cases'][::-1],[report()['cases'][0]]*4):
            r=report();r['cases']=rows
            with self.assertRaises(RuntimeError):contract.validate(r)
    def test_same_world_or_controller_does_not_prove_travel(self):
        for field in ('world','controller'):
            r=report()
            for row in r['cases']:row[field]='same'
            with self.assertRaises(RuntimeError):contract.validate(r)
    def test_duplicate_or_foreign_callbacks_rejected(self):
        for field,value in (('parent_selected_callbacks',2),('back_selected_callbacks',0),('parent_other_callbacks',1),('back_other_callbacks',1)):
            r=report();r['cases'][2][field]=value
            with self.assertRaises(RuntimeError):contract.validate(r)
    def test_focus_native_back_and_cleanup_cannot_be_flags_only(self):
        for field in ('parent_focus','settings_focus','screen_profile_matches','back_profile_matches','settings_closed','settings_focus_removed'):
            r=report();r['cases'][3][field]=False
            with self.assertRaises(RuntimeError):contract.validate(r)
        for field in ('old_ui_naturally_deactivated_before_probe_cleanup','old_travel_observers_unbound','old_travel_callbacks_quiet_after_new_ui','new_frontend_reactivated_after_back','owned_ui_unmounted_and_unrooted','selectors_and_class_roots_restored'):
            r=report();r[field]=False
            with self.assertRaises(RuntimeError):contract.validate(r)
    def test_native_confirmation_and_destination_still_revalidated(self):
        for field,value in (('confirmation_results',[1]),('new_world_path','wrong'),('native_frontend_main_menu_active_in_menu_layer',False)):
            r=report();r['travel'][field]=value
            with self.assertRaises(RuntimeError):contract.validate(r)
    def test_shortcut_and_foreign_profile_rejected(self):
        for field in contract.FORBIDDEN:
            r=report();r[field]=True
            with self.assertRaises(RuntimeError):contract.validate(r)
        r=report();r['cases'][0]['profile']='BlueprintFallback'
        with self.assertRaises(RuntimeError):contract.validate(r)
    def test_opt_in_selector_never_auto_runs_or_runs_in_commandlet(self):
        self.assertEqual(validation_module(['-UEPUITravelLifetimeResult=x']),'uep_lyra_hud.ui_travel_lifetime_validation')
        self.assertIsNone(validation_module([]));self.assertIsNone(validation_module(['-run=Py','-UEPUITravelLifetimeResult=x']))
