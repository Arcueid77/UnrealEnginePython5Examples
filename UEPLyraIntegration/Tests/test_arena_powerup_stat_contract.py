import copy,unittest
from uep_lyra_hud.arena_powerup_stat_contract import FORMAT,validate
def report(mode='Python'):
    counts={p+k:0 for p in ('python_','fallback_') for k in ('configure','listen')}
    if mode!='Baseline':counts[('python_' if mode=='Python' else 'fallback_')+'configure']=1;counts[('python_' if mode=='Python' else 'fallback_')+'listen']=1
    return dict(status='passed',error=None,mode=mode,full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,callbacks_replayed=False,delegate_broadcast_by_fixture=False,python_retry_clock=False,new_production_cleanup_added=False,actor_attributes_written_directly=False,cleanup_complete=True,owned_proxies_cancelled=True,owned_widgets_removed=True,pause_restored=True,natural_stats=[dict(attribute=a,target='PS0',active=True,text='1',expected_text='1',counts=counts) for a in ('BombsRemaining','BombRange','MovementSpeed')],retry=dict(initial_attribute_missing=True,two_configures=True,paused_seconds=.18,game_time_paused=True,native_listen_continues_while_paused=True,no_proxy_after_init_while_paused=True,attribute_initialized_natively=True,resumed_without_manual_listen=True,native_resume_game_seconds=0.,native_resume_real_seconds=.1,native_resume_frame_delta=1,resumed_while_world_paused=True,active=True,initial_text='1'),soft_texture_initially_unloaded=True,soft_texture_resource='/Game/UEPValidation/T_ArenaStatSoftProbe.T_ArenaStatSoftProbe',first_change=dict(callbacks=1,new_value=.5,old_value=1.,text='1',native_animation_started=True),animation=dict(max_position=.24,finished=True,end=.25),pending_reconfigure=dict(immediate_active=True,replacement_distinct=True,earlier_proxy_still_active=True,proxies_not_rooted=True,callbacks=2,new_value=.25,old_value=.5,text='0'),repeat_configure=dict(stored_previous_cancelled=True,older_proxy_still_active=True,callbacks=2,text='1'),format_cases=copy.deepcopy(FORMAT),trace_only_forwarding=True,native_gameplay_effect_used=True,no_manual_animation_completion=True)
class ArenaPowerupStatContractTests(unittest.TestCase):
    def test_zero_monotonic_resolution_requires_later_native_frame(self):
        r=report();r['retry']['native_resume_real_seconds']=0.;self.assertEqual(validate(r)['status'],'passed');r['retry']['native_resume_frame_delta']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_baseline_and_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertEqual(validate(report(mode))['pending_native_duplicate_callbacks'],2)
    def test_invalid_missing_attribute_fixture_or_paused_retry_rejected(self):
        for key in ('initial_attribute_missing','game_time_paused','native_listen_continues_while_paused'):
            r=report();r['retry'][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_deduplicating_original_pending_retry_or_canceling_all_old_proxies_rejected(self):
        r=report();r['pending_reconfigure']['callbacks']=1
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['repeat_configure']['older_proxy_still_active']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_lost_unloaded_soft_reference_or_wrong_rounding_rejected(self):
        r=report();r['soft_texture_resource']=None
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['format_cases'][0][1]='-2'
        with self.assertRaises(RuntimeError):validate(r)
    def test_no_animation_or_replayed_callbacks_rejected(self):
        r=report();r['animation']['max_position']=0.
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['callbacks_replayed']=True
        with self.assertRaises(RuntimeError):validate(r)
