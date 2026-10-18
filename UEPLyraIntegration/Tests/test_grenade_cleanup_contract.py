"""Closed native timer evidence counterexamples,not native execution itself."""
import copy
from pathlib import Path
import unittest
from uep_lyra_weapons.grenade_cleanup_contract import PLAN,CLASS,validate


def model():
    report=dict(status="passed",error=None,native_mode="Standalone",cases=[],observation_errors=[],remaining_test_actors=0)
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","cleanup_callback_replayed","timer_state_written","health_properties_written","raw_velocity_written","quantitative_movement_parity_tested","fuse_detonate_damage_business_migrated"): report[key]=False
    for key in ("original_native_timer_used","test_grenade_collision_disabled","production_classes_restored","all_pawn_health_unchanged","source_capsule_ignores_restored"): report[key]=True
    for index,(name,profile) in enumerate(PLAN):
        py=profile=="Python";actor="grenade"+str(index);instigator=None if name=="no-instigator" else "source"
        before=dict(mesh_ignores=[instigator,"unrelated"] if name=="character" else ["unrelated"],capsule_ignores=[actor,"old"] if name=="character" else None,rotation_follows_velocity=False)
        after=dict(mesh_ignores=["unrelated"],capsule_ignores=["old"] if name=="character" else None,rotation_follows_velocity=True)
        stats=dict(python_calls=int(py),fallback_calls=int(not py),capsule_unignores=int(py and name=="character"),non_character_skips=int(py and name!="character"),
            mesh_unignores=int(py),rotation_writes=int(py),invalid_capsule_noops=0,invalid_mesh_noops=0,invalid_movement_noops=0)
        row=dict(name=name,profile=profile,**{"class":CLASS},actor=actor,instigator=instigator,instigator_is_character=name=="character",quiet_ticks=20,
            actual_timer_callback_count=1,actor_destroyed=True,native_grenade_alive_until_cleanup=True,max_observed_frame=1./60.,
            event=dict(profile=profile,native_timer_callback=True,elapsed=.166667,before=before,after=after,stats=stats))
        report["cases"].append(row)
    return report


class TestGrenadeCleanupContract(unittest.TestCase):
    def setUp(self): self.report=model()
    def reject(self):
        with self.assertRaises(RuntimeError): validate(self.report)
    def test_complete_model_not_native_execution(self): self.assertEqual(validate(self.report)["actual_native_timer_callbacks"],6)
    def test_no_callback_replay(self): self.report["cleanup_callback_replayed"]=True;self.reject()
    def test_no_native_timer_state_write(self): self.report["timer_state_written"]=True;self.reject()
    def test_no_fuse_damage_claim(self): self.report["fuse_detonate_damage_business_migrated"]=True;self.reject()
    def test_no_quantitative_motion_claim(self): self.report["quantitative_movement_parity_tested"]=True;self.reject()
    def test_native_timer_not_early(self): self.report["cases"][0]["event"]["elapsed"]=.1;self.reject()
    def test_native_timer_not_arbitrary_late(self): self.report["cases"][0]["event"]["elapsed"]=.5;self.reject()
    def test_native_timer_nan_rejected(self): self.report["cases"][0]["event"]["elapsed"]=float("nan");self.reject()
    def test_duplicate_callback(self): self.report["cases"][0]["actual_timer_callback_count"]=2;self.reject()
    def test_native_actor_class(self): self.report["cases"][0]["class"]="PythonActor";self.reject()
    def test_initial_native_reverse_ignore_required(self): self.report["cases"][0]["event"]["before"]["capsule_ignores"]=[];self.reject()
    def test_only_test_actor_removed_from_capsule(self): self.report["cases"][0]["event"]["after"]["capsule_ignores"]=[];self.reject()
    def test_only_instigator_removed_from_mesh(self): self.report["cases"][0]["event"]["after"]["mesh_ignores"]=[];self.reject()
    def test_rotation_restore(self): self.report["cases"][0]["event"]["after"]["rotation_follows_velocity"]=False;self.reject()
    def test_noncharacter_still_mesh_and_rotation(self): self.report["cases"][3]["event"]["stats"]["rotation_writes"]=0;self.reject()
    def test_noncharacter_original_begin_does_not_install_ignore(self): self.report["cases"][2]["event"]["before"]["mesh_ignores"].append("source");self.reject()
    def test_null_instigator_native_case(self): self.report["cases"][-1]["instigator"]="Pawn";self.reject()
    def test_quiet_interval(self): self.report["cases"][0]["quiet_ticks"]=19;self.reject()
    def test_source_ignore_list_restored(self): self.report["source_capsule_ignores_restored"]=False;self.reject()
    def test_production_classes_restored(self): self.report["production_classes_restored"]=False;self.reject()
    def test_fixture_uses_real_timer_no_callback_or_timer_replay(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_cleanup_validation.py").read_text(encoding="utf-8")
        for value in ('"FinishSpawningActor"','"CopyArrayOfMoveIgnoreActors"','handler(actor)','"SetActorEnableCollision"'): self.assertIn(value,text)
        for value in ('call_function("PostLaunchCleanup"','call_function("ReceiveBeginPlay"','call_function("K2_SetTimer','call_function("IgnoreActorWhenMoving"','set_property("bRotationFollowsVelocity"','set_property("Health"'): self.assertNotIn(value,text)
    def test_current_vfx_regression_preserves_complete_profile_family(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_vfx_validation.py").read_text(encoding="utf-8")
        for value in ('self.original_profile_classes','vars(base).items()','for name,base in self.original_profile_classes.items()'): self.assertIn(value,text)
