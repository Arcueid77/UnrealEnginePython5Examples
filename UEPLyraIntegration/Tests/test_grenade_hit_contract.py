"""Native blocking-event report counterexamples; not physical runtime proof."""
from pathlib import Path
import unittest
from uep_lyra_weapons.grenade_hit_contract import PLAN,CLASS,validate


def model():
    report=dict(status="passed",error=None,native_mode="Standalone",cases=[],observation_errors=[],quiet_ticks=20)
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","hit_callback_replayed","health_properties_written","raw_velocity_written","enemy_hit_detonation_tested","native_rpc_detonate_body_migrated","audio_playback_tested","quantitative_flight_physics_tested"): report[key]=False
    for key in ("native_blocking_sweep_used","all_pawn_health_unchanged","test_actors_destroyed","bot_pose_restored","production_classes_restored"): report[key]=True
    for name,profile in PLAN:
        py=profile=="Python";stats=dict(python_hits=int(py),fallback_hits=int(not py),team_queries=int(py),invalid_team_subsystem_defaults=0,
            different_team_hits=0,other_team_hits=int(py),native_timer_clears=0,handle_writes=0,native_detonate_requests=0,native_sound_requests=int(py))
        report["cases"].append(dict(name=name,profile=profile,**{"class":CLASS},native_hits=1,actor_destroyed=True,expected_other="target",mesh="mesh",
            event=dict(profile=profile,other="target",comparison=2 if name=="invalid-wall" else 0,native_generated_callback=True,my_component="mesh",other_component="other-mesh",
                location=[1.,2.,3.],fuse_exists_before=True,fuse_exists_after=True,stats=stats)))
    return report


class TestGrenadeHitContract(unittest.TestCase):
    def setUp(self): self.report=model()
    def reject(self):
        with self.assertRaises(RuntimeError): validate(self.report)
    def test_full_model_only(self): self.assertEqual(validate(self.report)["actual_native_blocking_hit_trials"],4)
    def test_no_enemy_detonation_overclaim(self): self.report["enemy_hit_detonation_tested"]=True;self.reject()
    def test_no_sound_playback_claim(self): self.report["audio_playback_tested"]=True;self.reject()
    def test_no_callback_replay(self): self.report["hit_callback_replayed"]=True;self.reject()
    def test_actual_callback_not_fake_sweep_exit(self): self.report["cases"][0]["native_hits"]=0;self.reject()
    def test_no_duplicate_native_hit(self): self.report["cases"][0]["native_hits"]=2;self.reject()
    def test_actual_other_actor(self): self.report["cases"][0]["event"]["other"]="wrong";self.reject()
    def test_actual_my_component(self): self.report["cases"][0]["event"]["my_component"]="wrong";self.reject()
    def test_native_same_team_not_hostile(self): self.report["cases"][-1]["event"]["comparison"]=1;self.reject()
    def test_non_enemy_fuse_not_cancelled(self): self.report["cases"][0]["event"]["fuse_exists_after"]=False;self.reject()
    def test_native_hit_position_not_nan(self): self.report["cases"][0]["event"]["location"][0]=float("nan");self.reject()
    def test_no_extra_detonate(self): self.report["cases"][-1]["event"]["stats"]["native_detonate_requests"]=1;self.reject()
    def test_source_restore(self): self.report["bot_pose_restored"]=False;self.reject()
    def test_fixture_real_move_no_event_replay(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_hit_validation.py").read_text(encoding="utf-8")
        for value in ('bSweep=True','"SetNotifyRigidBodyCollision"','handler(actor,MyComp,Other,OtherComp','"CompareTeams"'): self.assertIn(value,text)
        for value in ('call_function("ReceiveHit"','set_property("Health"','set_property("Velocity"'): self.assertNotIn(value,text)
