"""Native transition counterexamples; model data are not runtime evidence."""
import copy
from pathlib import Path
import unittest
from uep_lyra_weapons.grenade_actions_contract import PLAN,CLASS,validate


def model():
    report=dict(status="passed",error=None,native_mode="Standalone",cases=[],remaining_test_actors=0,quiet_ticks=20,warmup_actual_active_ticks=3,native_zero_velocity_entry="ProjectileMovement.SetVelocityInLocalSpace")
    for field in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","begin_play_replayed","native_completion_delegate_replayed","health_properties_written","raw_velocity_written","quantitative_flight_physics_tested","native_trail_completion_tested","fuse_detonate_damage_migrated"): report[field]=False
    for field in ("ordinary_action_entries_called_by_fixture","test_grenade_collision_disabled","all_pawn_health_unchanged","production_classes_unchanged","native_warmup_ready","warmup_actor_destroyed"): report[field]=True
    for name,profile in PLAN:
        py=profile=="Python";invalid=name=="invalid-trail";speed=0. if name=="zero-speed" else 5.;forward=[0.,2. if name=="nonunit-forward" else 1.,0.]
        before=dict(location=[0.,0.,0.],rotation=[1.,2.,3.],velocity=[3.,4.,0.] if speed else [0.,0.,0.],conserved=0.,trail="old" if not invalid else None,trail_valid=not invalid,trail_active=not invalid,movement_active=True,matching_components=0 if invalid else 1)
        after=dict(location=[0.,0.,0.] if invalid else [10.,20.,30.],rotation=[1.,2.,3.],velocity=list(before["velocity"]) if invalid else [value*speed/2. for value in forward],conserved=speed,
            trail=None if invalid else "new",trail_valid=not invalid,movement_active=True,matching_components=0 if invalid else 2)
        stats=dict(teleport_python=int(py),teleport_fallback=int(not py),speed_reads=int(py),conserved_writes=int(py),missing_movement_reads=0,
            invalid_trail_noops=int(py and invalid),trail_deactivations=int(py and not invalid),native_locations=int(py and not invalid),movement_activations=int(py and not invalid),
            velocity_writes=int(py and not invalid),missing_movement_writes=0,vfx_calls=int(py and not invalid),destroy_python=int(py),destroy_fallback=int(not py),native_destroy_calls=int(py))
        report["cases"].append(dict(name=name,profile=profile,**{"class":CLASS},native_destroyed=True,before=before,after=after,destination=[10.,20.,30.],forward=forward,old_trail_active_after=not invalid,stats=stats,vfx_helper_calls=1 if invalid else 2))
    return report


class TestGrenadeActionsContract(unittest.TestCase):
    def setUp(self): self.report=model()
    def reject(self):
        with self.assertRaises(RuntimeError): validate(self.report)
    def test_full_model_only(self): self.assertEqual(validate(self.report)["native_actor_trials"],8)
    def test_no_flight_physics_claim(self): self.report["quantitative_flight_physics_tested"]=True;self.reject()
    def test_no_completion_delegate_replay(self): self.report["native_completion_delegate_replayed"]=True;self.reject()
    def test_native_original_class(self): self.report["cases"][0]["class"]="PythonActor";self.reject()
    def test_real_destroy_required(self): self.report["cases"][0]["native_destroyed"]=False;self.reject()
    def test_conserved_original_speed_not_post_half_speed(self): self.report["cases"][0]["after"]["conserved"]=2.5;self.reject()
    def test_half_speed_not_full_speed(self): self.report["cases"][0]["after"]["velocity"]=[0.,5.,0.];self.reject()
    def test_nonunit_not_normalized(self): self.report["cases"][2]["after"]["velocity"]=[0.,2.5,0.];self.reject()
    def test_native_location_actual(self): self.report["cases"][0]["after"]["location"]=[0.,0.,0.];self.reject()
    def test_no_unrequested_rotation(self): self.report["cases"][0]["after"]["rotation"][0]+=1.;self.reject()
    def test_old_trail_native_state_matches_baseline(self): self.report["cases"][0]["old_trail_active_after"]=False;self.reject()
    def test_no_natural_trail_completion_claim(self): self.report["native_trail_completion_tested"]=True;self.reject()
    def test_common_native_readiness(self): self.report["warmup_actual_active_ticks"]=2;self.reject()
    def test_new_component_not_reuse(self): self.report["cases"][0]["after"]["trail"]="old";self.reject()
    def test_invalid_trail_no_teleport(self): self.report["cases"][-1]["after"]["location"]=[10.,20.,30.];self.reject()
    def test_invalid_trail_no_velocity_change(self): self.report["cases"][-1]["after"]["velocity"]=[0.,2.5,0.];self.reject()
    def test_invalid_trail_still_saves_speed(self): self.report["cases"][-1]["after"]["conserved"]=0.;self.reject()
    def test_zero_speed_native_intent(self): self.report["cases"][4]["before"]["velocity"]=[3.,4.,0.];self.reject()
    def test_native_velocity_intent_api(self): self.report["native_zero_velocity_entry"]="raw property";self.reject()
    def test_no_nan(self): self.report["cases"][0]["after"]["velocity"][1]=float("nan");self.reject()
    def test_no_late_actors(self): self.report["remaining_test_actors"]=1;self.reject()
    def test_fixture_uses_native_entries_without_completion_replay(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_actions_validation.py").read_text(encoding="utf-8")
        for value in ('actor.call_function(policy.TELEPORT','actor.call_function(policy.DESTROY','"SetVelocityInLocalSpace"','"K2_DestroyComponent"'): self.assertIn(value,text)
        for value in ('set_property("Velocity"','call_function("ReceiveBeginPlay"','set_property("Health"','broadcast_event("OnSystemFinished"'): self.assertNotIn(value,text)
    def test_current_cleanup_observer_keeps_all_actor_actions(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_cleanup_validation.py").read_text(encoding="utf-8")
        for value in ('self.original_profile_classes','vars(base).items()','for name,base in self.original_profile_classes.items()'): self.assertIn(value,text)
