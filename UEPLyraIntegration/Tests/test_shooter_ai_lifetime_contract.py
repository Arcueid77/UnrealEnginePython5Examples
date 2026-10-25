import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_world.shooter_ai_lifetime_contract import FORBIDDEN,validate
from uep_lyra_hud.startup import validation_module
TRUE=('pawn_endplay_observed','native_unpossess_stopped_brain','native_unpossess_cleared_enemy','pawn_destroy_callbacks_quiet','native_world_replaced','world_owner_endplay_observed','world_callbacks_quiet','owned_endplay_scopes_closed','python_object_references_released','old_world_and_ai_objects_collected','profiles_and_class_roots_restored','player_health_unchanged_before_travel')
def report():
    r=dict(status='passed',error=None,profile='Python',mode='tdm',native_mode='Standalone',gc_requested=True,quiet_seconds_after_destroy=.9,quiet_seconds_after_world_endplay=.9,
        running_cases=[dict(purpose=p,native_brain_running=True,task_class='BTTask_Wait',wait_seconds=5.,elapsed=1.1,native_ammo_ticks=3,intervals=[.5,.5]) for p in ('pawn-destroy','world-travel')])
    r.update(dict.fromkeys(FORBIDDEN,False));r.update(dict.fromkeys(TRUE,True))
    r.update(retained_old_objects=[],pawn_destroy_callbacks_before={'ammo':3},pawn_destroy_callbacks_after={'ammo':3},player_health_before={'health':100.,'death':0},player_health_before_travel={'health':100.,'death':0});return r
class ShooterAILifetimeContractTests(unittest.TestCase):
    def test_complete_native_lifetime_case(self):self.assertEqual(validate(report())['native_lifetime_boundaries'],2)
    def test_both_native_profile_and_map_modes_supported(self):
        for profile in ('BlueprintFallback','Python'):
            for mode in ('tdm','cp'):
                r=report();r.update(profile=profile,mode=mode);validate(r)
    def test_completed_or_non_native_wait_does_not_prove_cancel(self):
        for field,value in (('elapsed',5.),('native_brain_running',False),('task_class','SyntheticTask')):
            r=report();r['running_cases'][0][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_original_service_intervals_are_not_widened(self):
        for intervals in ([.5],[.5,.9],[.1,.5]):
            r=report();r['running_cases'][1]['intervals']=intervals
            with self.assertRaises(RuntimeError):validate(r)
    def test_every_native_cleanup_observation_required(self):
        for field in TRUE:
            r=report();r[field]=False
            with self.assertRaises(RuntimeError):validate(r)
    def test_manual_stop_callback_or_wait_time_changes_rejected(self):
        for field in FORBIDDEN:
            r=report();r[field]=True
            with self.assertRaises(RuntimeError):validate(r)
    def test_missing_or_repeated_lifetime_boundary_rejected(self):
        for rows in (report()['running_cases'][:1],[report()['running_cases'][0]]*2):
            r=report();r['running_cases']=rows
            with self.assertRaises(RuntimeError):validate(r)
    def test_gc_and_quiet_period_cannot_be_omitted(self):
        for field,value in (('gc_requested',False),('quiet_seconds_after_destroy',.1),('quiet_seconds_after_world_endplay',.2)):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_startup_is_explicit_and_never_runs_as_commandlet(self):
        self.assertEqual(validation_module(['-UEPShooterAILifetimeResult=r']),'uep_lyra_world.shooter_ai_lifetime_validation')
        self.assertIsNone(validation_module([]));self.assertIsNone(validation_module(['-run=Py','-UEPShooterAILifetimeResult=r']))
    def test_cleanup_flags_must_match_observations(self):
        for field,value in (('retained_old_objects',['old-world']),('pawn_destroy_callbacks_after',{'ammo':4}),('player_health_before_travel',{'health':50.,'death':0})):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
