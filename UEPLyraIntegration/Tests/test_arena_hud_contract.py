import copy,unittest
from uep_lyra_hud.arena_hud_contract import CASES,validate
def report(mode='Python'):
    counts={p+k:0 for p in ('python_','fallback_') for k in ('select','configure','construct','ready','tick')}
    if mode!='Baseline':
        for k in ('select','configure','construct','ready','tick'):counts[('python_' if mode=='Python' else 'fallback_')+k]=1
    return dict(status='passed',error=None,mode=mode,full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,timer_tick_or_ready_replayed=False,native_delegates_broadcast_by_fixture=False,production_round_properties_changed=False,python_clock_added=False,cleanup_complete=True,pause_restored=True,natural_list=True,natural_timer=dict(ready_calls=1,tick_calls=2,mode_is_actual_component=True),list_ingress=dict(native_begin_end_component=True,entries_added=1,entries_restored=True,native_select_delta=1,native_configure_delta=1),selector_results=[True]*3,invalid_widget_no_tile_configures=True,owned_experience=dict(ready_next_frame=True,mode_is_actual_component=True),clock_cases=[dict(name=n,input=s,playing=p,text=t,native_tick_delta=2,native_frame_delta=2,world_time_frozen=True) for n,s,p,t in CASES],invalid_mode=dict(text_unchanged=True,native_tick_delta=2),remount=dict(construct_delta=1,ready_delta=1,native_ready_next_frame=True,actual_component_restored=True),natural_list_counts=counts,natural_timer_counts=copy.deepcopy(counts),actual_round_properties_preserved=True,original_list_empty_events_stay_native=True)
class ArenaHUDContractTests(unittest.TestCase):
    def test_original_and_both_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertEqual(validate(report(mode))['native_clock_cases'],9)
    def test_missing_native_ingress_or_wrong_selector_rejected(self):
        r=report();r['list_ingress']['native_configure_delta']=0
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['selector_results'][1]=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_minute_boundary_or_fractional_format_rejected(self):
        r=report();r['clock_cases'][3]['text']='0:60'
        with self.assertRaises(RuntimeError):validate(r)
    def test_replayed_tick_or_production_round_change_rejected(self):
        for key in ('timer_tick_or_ready_replayed','production_round_properties_changed'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_missing_remount_ready_or_invalid_mode_mutation_rejected(self):
        r=report();r['remount']['ready_delta']=0
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['invalid_mode']['text_unchanged']=False
        with self.assertRaises(RuntimeError):validate(r)
