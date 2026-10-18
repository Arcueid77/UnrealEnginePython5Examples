"""Counterexamples for native evidence; fabricated models are not UE passes."""
import copy
from pathlib import Path
import unittest
from uep_lyra_abilities.grenade_activation_contract import CLASS,PROJECTILE,PLAN,validate,expected


def model():
    report=dict(status="passed",error=None,native_mode="Standalone",native_class=CLASS,cases=[],observation_errors=[],
        request_entry="ASC.TryActivateAbilityByClass",remaining_test_projectiles=0,remaining_fixture_actors=0)
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","activation_event_replayed","task_callbacks_replayed","ability_granted_by_fixture","health_properties_written","inventory_properties_written","ability_spec_properties_written","projectile_actor_business_migrated","explosion_damage_tested","denied_body_native_tested"): report[key]=False
    for key in ("observers_restored","listener_closed","profile_restored","specs_preserved","config_preserved","native_pose_restored","native_control_restored","actual_granted_primary_instance"): report[key]=True
    for index,(name,profile) in enumerate(PLAN):
        python=profile=="Python";hit=name!="miss";distance={"miss":0.,"near":30.,"far":180.}[name]
        row=dict(name=name,profile=profile,pawn="pawn"+str(index),quiet_ticks=20,native_callback_count=1,native_role=3,active_after=False,tasks_after=0,cooldown=5.,native_cooldown=5.,
            before=dict(actor_location=[0.,0.,10.],forward=[1.,0.,0.],up=[0.,0.,1.],control=[0.,0.,0.],
                trace=dict(hit=hit,distance=distance,location=[200.,10.,60.],start=[20.,10.,60.],end=[2000.,10.,60.])))
        for key in ("native_request_accepted","native_repeat_rejected","native_cost_ready","native_cooldown_ready","all_pawn_health_unchanged","persistent_handle_preserved","specs_preserved","config_preserved","projectile_destroyed_by_fixture","montage_continues_after_end","native_montage_completed"): row[key]=True
        row["location"],row["direction"]=expected(row)
        row["messages"]=[dict(channel="Ability.Grenade.Duration.Message",instigator=row["pawn"],duration=5.,native_active=True,native_montage_task_count=1)]
        row["projectiles"]=[dict(path="projectile"+str(index),**{"class":PROJECTILE},instigator=row["pawn"],owner=None,location=list(row["location"]),rotation=list(row["direction"]),scale=[1.,1.,1.])]
        row["stats"]=dict(python_calls=int(python),fallback_calls=int(not python),cost_checks=int(python),cooldown_checks=int(python),commits=int(python),denied=0,aim_queries=int(python),
            near_control_rotation=int(python and distance<45.),hit_aim=int(python and distance>=45. and hit),miss_aim=0,projectiles=int(python),cooldown_writes=int(python),
            montage_tasks=int(python),duration_messages=int(python),native_ends=int(python),invalid_receiver_defaults=0)
        report["cases"].append(row)
    return report


class TestGrenadeActivationContract(unittest.TestCase):
    def setUp(self): self.report=model()
    def reject(self):
        with self.assertRaises(RuntimeError): validate(self.report)
    def test_complete_model_not_runtime(self): self.assertEqual(validate(self.report)["native_profile_trials"],6)
    def test_failure_is_not_accepted(self): self.report["status"]="failed";self.reject()
    def test_six_cases_required(self): self.report["cases"].pop();self.reject()
    def test_native_only_standalone_scope(self): self.report["network_acceptance"]=True;self.reject()
    def test_no_explosion_claim(self): self.report["explosion_damage_tested"]=True;self.reject()
    def test_no_fake_denied_native_body(self): self.report["denied_body_native_tested"]=True;self.reject()
    def test_no_callback_replay(self): self.report["activation_event_replayed"]=True;self.reject()
    def test_no_health_repair(self): self.report["health_properties_written"]=True;self.reject()
    def test_native_input_not_grant(self): self.report["ability_granted_by_fixture"]=True;self.reject()
    def test_class_preserved(self): self.report["native_class"]="PythonDerived";self.reject()
    def test_selected_handler_once(self): self.report["cases"][0]["native_callback_count"]=2;self.reject()
    def test_actual_authority(self): self.report["cases"][0]["native_role"]=2;self.reject()
    def test_immediate_end(self): self.report["cases"][0]["active_after"]=True;self.reject()
    def test_native_task_cleanup(self): self.report["cases"][0]["tasks_after"]=1;self.reject()
    def test_native_montage_continues(self): self.report["cases"][1]["montage_continues_after_end"]=False;self.reject()
    def test_natural_montage_completion(self): self.report["cases"][1]["native_montage_completed"]=False;self.reject()
    def test_missing_projectile(self): self.report["cases"][0]["projectiles"]=[];self.reject()
    def test_instigator_is_pawn(self): self.report["cases"][0]["projectiles"][0]["instigator"]="PS";self.reject()
    def test_no_owner_pin(self): self.report["cases"][0]["projectiles"][0]["owner"]="Controller";self.reject()
    def test_collision_placement_not_wrong_matching_outputs(self):
        for row in self.report["cases"][:2]: row["location"][0]+=1.;row["projectiles"][0]["location"][0]+=1.
        self.reject()
    def test_far_aim_not_near_branch(self): self.report["cases"][-1]["direction"]=[0.,0.,0.];self.reject()
    def test_no_trace_nan(self): self.report["cases"][0]["before"]["trace"]["distance"]=float("nan");self.reject()
    def test_no_native_nan(self): self.report["cases"][0]["location"][0]=float("nan");self.reject()
    def test_cooldown_real_native_value(self): self.report["cases"][0]["native_cooldown"]+=.1;self.reject()
    def test_message_duration_not_literal(self): self.report["cases"][0]["messages"][0]["duration"]+=1.;self.reject()
    def test_message_instigator_is_pawn(self): self.report["cases"][0]["messages"][0]["instigator"]="Controller";self.reject()
    def test_message_before_end(self): self.report["cases"][0]["messages"][0]["native_active"]=False;self.reject()
    def test_message_after_native_montage_start(self): self.report["cases"][0]["messages"][0]["native_montage_task_count"]=0;self.reject()
    def test_quiet_ticks_required(self): self.report["cases"][0]["quiet_ticks"]=19;self.reject()
    def test_no_late_actors(self): self.report["remaining_test_projectiles"]=1;self.reject()
    def test_observer_class_restored(self): self.report["observers_restored"]=False;self.reject()
    def test_listener_closed(self): self.report["listener_closed"]=False;self.reject()
    def test_fixture_is_native_input_and_observation(self):
        source=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_activation_validation.py").read_text(encoding="utf-8")
        for text in ('"TryActivateAbilityByClass"','"SendGameplayEventToActor"','"GetAllActorsOfClass"','"ReadDuration"','handler(ability)','"K2_DestroyActor"'): self.assertIn(text,source)
        for text in ('call_function("K2_ActivateAbility"','call_function("K2_EndAbility"','set_property("Health"','set_property("Location"','set_property("Cooldown Time"','call_function("ReadyForActivation"'): self.assertNotIn(text,source)
    def test_typed_transform_avoids_known_default_import(self):
        source=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_activation_mixin.py").read_text(encoding="utf-8")
        self.assertIn('ue.FTransform(point,direction,ue.FVector(1.,1.,1.))',source)
        self.assertNotIn('call_function("MakeTransform"',source)
