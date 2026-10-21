import copy,unittest
from uep_lyra_hud.arena_player_ui_contract import validate

def report(mode='Python'):
    count=dict(python_begin=int(mode=='Python'),python_end=0,fallback_begin=int(mode=='BlueprintFallback'),fallback_end=0,registrations=int(mode=='Python'),unregistrations=0)
    row=dict(action=0,data='PlayerState0',tag='TopDownArena.ExtensionPoint.Players',priority=-1,context=None,handle_valid=True)
    ended=dict(count,python_end=int(mode=='Python'),fallback_end=int(mode=='BlueprintFallback'),unregistrations=int(mode=='Python'))
    return dict(status='passed',error=None,mode=mode,cleanup_complete=True,observer_callback_native=True,native_component_destruction=True,full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,lifecycle_callbacks_replayed=False,registry_replaced=False,natural_components=[dict(owner_is_playerstate=True,handle_valid=True,counts=count)],owned_components=[dict(owner='PlayerState0',handle_valid_before=True,handle_valid_after_unregister=True,counts_after=ended) for _ in range(2)],owned_owner='PlayerState0',initial_registry=[row],final_registry=[copy.deepcopy(row)],owned_events=[dict(row,action=a) for a in (0,0,1,1)],remaining_after_first_destroy=2,remaining_after_second_destroy=1)

class ArenaPlayerUIContractTests(unittest.TestCase):
    def test_baseline_and_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertEqual(validate(report(mode))['native_registry_events'],4)
    def test_pointer_validity_without_native_removed_callback_rejected(self):
        r=report();r['owned_events'][-1]['action']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_player_context_priority_or_tag_rejected(self):
        for key,value in (('data','Controller'),('context','PlayerState0'),('priority',0),('tag','HUD.Other')):
            r=report();r['owned_events'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_leaked_extension_or_removed_other_handle_rejected(self):
        r=report();r['final_registry'].append(r['initial_registry'][0])
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['remaining_after_first_destroy']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_profile_replay_or_root_leak_rejected(self):
        for key in ('cleanup_complete','lifecycle_callbacks_replayed'):
            r=report();r[key]=not r[key]
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
        r=report('BlueprintFallback');r['owned_components'][0]['counts_after']['python_begin']=1
        with self.assertRaises(RuntimeError):validate(r)
