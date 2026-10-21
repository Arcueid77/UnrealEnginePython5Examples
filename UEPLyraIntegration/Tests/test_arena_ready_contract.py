import copy,unittest
from uep_lyra_hud.arena_ready_contract import FALSE_FIELDS,validate

def report(mode='Python'):
    count=dict(python_constructs=int(mode=='Python'),fallback_constructs=int(mode=='BlueprintFallback'),plays=int(mode=='Python'));sample=dict(position=0.,playing=True,forward=True,in_viewport=True,animation_end=4.125);natural=dict(first=copy.deepcopy(sample),samples=[dict(sample,position=.5),dict(sample,position=2.9),dict(sample,position=3.,in_viewport=False)],counts_after=count,removed_at_playing=True);owned=dict(first=copy.deepcopy(sample),samples=[dict(sample,position=.5),dict(sample,position=4.11),dict(sample,position=4.125,playing=False)],counts_after=count,native_animation_finished=True);r=dict(status='passed',error=None,mode=mode,owned_widgets_removed_and_roots_selectors_restored=True,natural_cues=[dict(not_rooted=True,parent_policy_after=dict(python_start=1,creates=1,adds=1,python_remove=1,removals=1))],natural_widgets=[natural],owned_widgets=[owned],phase_samples=[dict(Warmup=True,Playing=False),dict(Warmup=False,Playing=True)]);r.update(dict.fromkeys(FALSE_FIELDS,False));return r

class ArenaReadyContractTests(unittest.TestCase):
    def test_actual_baseline_and_both_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertEqual(validate(report(mode))['natural_widgets'],1)
    def test_manual_callback_or_clock_replay_rejected(self):
        for key in ('phase_or_cue_callbacks_replayed','python_animation_clock_added'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_missing_phase_transition_or_cue_parent_removal_rejected(self):
        r=report();r['phase_samples'].pop()
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['natural_cues'][0]['parent_policy_after']['removals']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_no_animation_progress_or_early_stop_rejected(self):
        r=report();r['owned_widgets'][0]['samples']=[dict(v,position=0.) for v in r['owned_widgets'][0]['samples']]
        with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_construct_profile_or_unrestored_context_rejected(self):
        r=report('BlueprintFallback');r['natural_widgets'][0]['counts_after']=dict(python_constructs=1,fallback_constructs=0,plays=1)
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['owned_widgets_removed_and_roots_selectors_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
