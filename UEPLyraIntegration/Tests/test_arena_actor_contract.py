import unittest
from uep_lyra_world.arena_actor_contract import validate
def report(mode='Python'):
    counts={p+k:0 for p in ('python_','fallback_') for k in ('begin','listen','display','parts','show','death','finish','overlap','change')}
    if mode!='Baseline':
        for k in ('begin','listen','display','parts','show','death','finish','overlap','change'):counts[('python_' if mode=='Python' else 'fallback_')+k]=2 if k=='parts' else 1
    return dict(status='passed',error=None,mode=mode,full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,audio_playback_tested=False,callbacks_replayed=False,death_event_sent_by_fixture=False,health_properties_written=False,replication_verified=False,native_tasks_or_delays_replaced=False,cleanup_complete=True,selectors_restored=True,owned_roots_removed=True,natural_arena_avatar=True,owned_avatar_class_preserved=True,retained_parent_begin_calls=1,visibility=dict(initially_hidden=True,shown=True,created_frame=1,shown_frame=2),team_cases=[dict(team=t,display_asset='Team',visible_parts=1) for t in (1,2,1)],team_visuals_changed=True,team_visuals_restored=True,native_parts_add_remove=True,hero_counts=counts,death=dict(native_lethal_effect=True,ability_class_preserved=True,activated=True,finished=True,duration=2.,dead_or_removed_avatar=True,native_cue_executed=True,counts=counts),pickup=dict(no_asc_overlap_keeps_actor=True,successful_overlap_destroys_actor=True,attribute_before=2.,attribute_after=3.,authority_vfx_matches_ui_data=True,authority_rep_notify_noop=True,null_effect_noop=True,counts=counts))
class ArenaActorContractTests(unittest.TestCase):
    def test_original_and_both_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertTrue(validate(report(mode))['native_pickup_overlap'])
    def test_visibility_must_defer_native_frame(self):
        r=report();r['visibility']['shown_frame']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_death_duration_and_actual_cue_required(self):
        r=report();r['death']['duration']=.1
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['death']['native_cue_executed']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_no_asc_destruction_or_wrong_attribute_delta_rejected(self):
        r=report();r['pickup']['no_asc_overlap_keeps_actor']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['pickup']['attribute_after']=4.
        with self.assertRaises(RuntimeError):validate(r)
    def test_inherited_parent_and_team_visual_evidence_required(self):
        r=report();r['retained_parent_begin_calls']=0
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['team_visuals_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
