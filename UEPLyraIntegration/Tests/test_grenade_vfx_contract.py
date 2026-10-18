"""Independent native evidence counterexamples,not Niagara runtime passes."""
import copy
from pathlib import Path
import unittest
from uep_lyra_weapons.grenade_vfx_contract import PLAN,CLASS,TRAIL,validate


def model():
    report=dict(status="passed",error=None,native_mode="Standalone",cases=[],observation_errors=[],remaining_test_actors=0,quiet_ticks=20,warmup_actual_active_ticks=3)
    for field in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","actor_collision_fuse_explosion_damage_migrated","projectile_physics_tested","projectile_replication_tested","particle_rendering_tested","health_properties_written","team_properties_written","begin_play_replayed"): report[field]=False
    for field in ("native_deferred_spawn_finish","original_blueprint_begin_calls_helper","repeat_ordinary_helper_call_by_fixture","grenade_actors_destroyed_before_world_tick","profile_classes_restored","all_pawn_health_unchanged","native_warmup_ready","warmup_actor_destroyed"): report[field]=True
    for name,profile in PLAN:
        py=profile=="Python";team={"other-team":2,"team1":1,"no-instigator":-1}[name];red=team==1;color=[1.,.05,.01,1.] if red else [.01,.15,1.,1.]
        row=dict(name=name,profile=profile,**{"class":CLASS},team_id=team,actor_destroyed=True,mesh="mesh")
        for index,field in enumerate(("initial","repeated"),1):
            stats=dict(python_calls=index if py else 0,fallback_calls=0 if py else index,native_spawns=index if py else 0,invalid_spawn_noops=0,trail_writes=index if py else 0,
                team_queries=index if py else 0,missing_team_subsystem_defaults=0,red_choices=index if py and red else 0,blue_choices=index if py and not red else 0,
                color_writes=index if py else 0,parameter_writes=index if py else 0,invalid_trail_noops=0)
            row[field]=dict(component="trail"+str(index),asset=TRAIL,parent="mesh",relative_location=[0.,0.,0.],relative_rotation=[0.,0.,0.],relative_scale=[1.,1.,1.],
                active=True,auto_activate=False,auto_destroy=False,actor_team_color=list(color),parameter_store_color=list(color),helper_calls=index,matching_components=index,
                parameter_name="User.Team_Color",parameter_offset=16,parameter_data_bytes=32,stats=stats,last_team_id=team)
        report["cases"].append(row)
    return report


class TestGrenadeVFXContract(unittest.TestCase):
    def setUp(self): self.report=model()
    def reject(self):
        with self.assertRaises(RuntimeError): validate(self.report)
    def test_full_model_only(self): self.assertEqual(validate(self.report)["actual_parameter_store_reads"],12)
    def test_no_physics_claim(self): self.report["projectile_physics_tested"]=True;self.reject()
    def test_no_explosion_claim(self): self.report["actor_collision_fuse_explosion_damage_migrated"]=True;self.reject()
    def test_real_begin_not_replayed(self): self.report["begin_play_replayed"]=True;self.reject()
    def test_no_raw_team_assignment(self): self.report["team_properties_written"]=True;self.reject()
    def test_helper_called_from_actual_begin(self): self.report["cases"][0]["initial"]["helper_calls"]=0;self.reject()
    def test_actual_original_actor_class(self): self.report["cases"][0]["class"]="PythonActor";self.reject()
    def test_actual_team_id(self): self.report["cases"][0]["team_id"]=1;self.reject()
    def test_parameter_value_read_not_only_field(self): self.report["cases"][0]["initial"]["parameter_store_color"]=[1.,1.,1.,1.];self.reject()
    def test_two_wrong_matching_sources_rejected(self):
        for row in self.report["cases"]: row["initial"]["actor_team_color"]=[0.,0.,0.,0.];row["initial"]["parameter_store_color"]=[0.,0.,0.,0.]
        self.reject()
    def test_native_parameter_offset_bounds(self): self.report["cases"][0]["initial"]["parameter_offset"]=20;self.reject()
    def test_native_parameter_name(self): self.report["cases"][0]["initial"]["parameter_name"]="AnotherColor";self.reject()
    def test_repeat_spawns_not_reuses(self): self.report["cases"][0]["repeated"]["component"]="trail1";self.reject()
    def test_original_previous_component_retained_until_actor_destroy(self): self.report["cases"][0]["repeated"]["matching_components"]=1;self.reject()
    def test_mesh_attachment(self): self.report["cases"][0]["initial"]["parent"]="root";self.reject()
    def test_auto_destroy_original_false(self): self.report["cases"][0]["initial"]["auto_destroy"]=True;self.reject()
    def test_request_not_confused_with_native_auto_activate_field(self): self.report["cases"][0]["initial"]["auto_activate"]=True;self.reject()
    def test_native_common_warmup_required(self): self.report["warmup_actual_active_ticks"]=2;self.reject()
    def test_actual_unit_scale(self): self.report["cases"][0]["initial"]["relative_scale"]=[0.,0.,0.];self.reject()
    def test_no_nan(self): self.report["cases"][0]["initial"]["parameter_store_color"][0]=float("nan");self.reject()
    def test_scope_restored(self): self.report["profile_classes_restored"]=False;self.reject()
    def test_quiet_interval(self): self.report["quiet_ticks"]=19;self.reject()
    def test_fixture_has_native_color_storage_and_no_event_replay(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_vfx_validation.py").read_text(encoding="utf-8")
        for value in ('"BeginDeferredActorSpawnFromClass"','"FinishSpawningActor"','"K2_GetComponentsByClass"','"OverrideParameters"','SortedParameterOffsets','store.ParameterData','struct.unpack_from'): self.assertIn(value,text)
        for value in ('call_function("ReceiveBeginPlay"','set_property("Team Color"','set_property("ParameterData"','set_property("Health"'): self.assertNotIn(value,text)
