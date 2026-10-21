import copy,unittest
from uep_lyra_world.arena_phases_contract import validate,validate_log
def report(mode='Python'):
    rows=[]
    for phase,game,amount in (('warmup',2.,2),('playing',5.,1),('postgame',125.,2),('warmup',135.2,2)):
        for i in range(amount):
            counts={p+k:0 for p in ('python_','fallback_') for k in ('activate','after')}
            if mode!='Baseline':counts[('python_' if mode=='Python' else 'fallback_')+'activate']=1
            for stage in ('before','after'):rows.append(dict(phase=phase,method='K2_ActivateAbility',stage=stage,game_seconds=game,real_seconds=game,frame=int(game*60),authority=True,counts=copy.deepcopy(counts)))
    for phase in ('warmup','playing'):rows.append(dict(phase=phase,method='K2_OnEndAbility',stage='after'))
    if mode!='Baseline':
        for phase in ('warmup','postgame'):rows.append(dict(phase=phase,method='AfterWait',stage='after',counts={('python_' if mode=='Python' else 'fallback_')+'after':1}))
    return dict(status='passed',error=None,mode=mode,full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,audio_playback_tested=False,callbacks_replayed=False,phases_started_by_fixture=False,round_properties_written=False,time_dilation_changed=False,native_delays_replaced=False,manual_travel_requested=False,cleanup_complete=True,selectors_restored=True,all_classes_unrooted=True,events=rows,last_postgame_seconds=134.9,default_durations=dict(warmup=3.,postgame=10.,round=120.),warmup_effect_with_registered_handles_observed=True,playing_warmup_effect_removed=True,natural_ready_widget_seen=True,natural_ready_widget_removed=True)
class ArenaPhaseContractTests(unittest.TestCase):
    def test_default_concurrent_cycle_and_all_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertEqual(validate(report(mode))['parallel_phase_counts'],[2,1,2,2])
    def test_removed_duplicate_original_phase_or_clock_reset_rejected(self):
        r=report();r['events'].pop(2);r['events'].pop(2)
        with self.assertRaises(RuntimeError):validate(r)
        r=report()
        for e in r['events']:
            if e.get('game_seconds')==135.2:e['game_seconds']=.2
        with self.assertRaises(RuntimeError):validate(r)
    def test_shortened_default_round_or_synthetic_transition_rejected(self):
        r=report();r['default_durations']['round']=1.
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['phases_started_by_fixture']=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_effect_cue_or_native_continuation_missing_rejected(self):
        r=report();r['natural_ready_widget_removed']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['events']=[e for e in r['events'] if e['method']!='AfterWait']
        with self.assertRaises(RuntimeError):validate(r)
    def test_real_seamless_travel_log_order_required(self):
        validate_log('UEP_ARENA_PHASES_ENTER postgame\nProcessServerTravel: map\nSeamlessTravel finished\nUEP_ARENA_PHASES_ENTER warmup')
        with self.assertRaises(RuntimeError):validate_log('UEP_ARENA_PHASES_ENTER postgame\nUEP_ARENA_PHASES_ENTER warmup\nProcessServerTravel: map\nSeamlessTravel finished')
