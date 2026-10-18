"""Dedicated server no-render branch models,not actual server acceptance."""
import importlib.util
from pathlib import Path
import unittest
from uep_lyra_weapons.grenade_begin_contract import validate

spec=importlib.util.spec_from_file_location("_headless_begin_fixture",Path(__file__).with_name("test_grenade_begin_contract.py"))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def model():
    report=fixture.model();report.update(native_mode="DedicatedServer",headless_runtime_requested=True,native_local_or_remote_player_controllers=0,
        headless_readiness=dict(native_mode="DedicatedServer",experience=True,playing=True,stable_seconds=.6),
        headless_selected_source=dict(actor="bot",player_state_pawn="bot",asc_avatar="bot",role=3,health=100.))
    for row in report["begin_cases"]:
        py=row["profile"]=="Python";before,after=row["event"]["before"],row["event"]["after"]
        before["actor_team_color"]=[0.,0.,0.,0.];after["actor_team_color"]=[0.,0.,0.,0.];after["trail_valid"]=False
        after["vfx_stats"]=dict(python_calls=int(py),fallback_calls=int(not py),native_spawns=int(py),invalid_spawn_noops=int(py),
            trail_writes=0,team_queries=0,red_choices=0,blue_choices=0,color_writes=0,parameter_writes=0)
    return report


class TestGrenadeHeadlessContract(unittest.TestCase):
    def setUp(self): self.report=model()
    def validate(self): return validate(self.report,expected_mode="DedicatedServer",expect_trail=False)
    def reject(self):
        with self.assertRaises(RuntimeError): self.validate()
    def test_complete_model_only(self): self.assertEqual(self.validate()["actual_begin_play_callbacks"],6)
    def test_not_a_standalone_pass(self): self.report["native_mode"]="Standalone";self.reject()
    def test_explicit_no_renderer_lane_required(self): self.report["headless_runtime_requested"]=False;self.reject()
    def test_no_fake_client_network_pass(self): self.report["network_acceptance"]=True;self.reject()
    def test_actual_no_player_controller(self): self.report["native_local_or_remote_player_controllers"]=1;self.reject()
    def test_native_canonical_bot_source(self): self.report["headless_selected_source"]["asc_avatar"]="old";self.reject()
    def test_real_post_phase_stability(self): self.report["headless_readiness"]["stable_seconds"]=.1;self.reject()
    def test_invalid_spawn_preserves_original_color(self): self.report["begin_cases"][1]["event"]["after"]["actor_team_color"]=[1.,.05,.01,1.];self.reject()
    def test_no_niagara_trail_created(self): self.report["begin_cases"][0]["event"]["after"]["trail_valid"]=True;self.reject()
    def test_python_invalid_spawn_branch_really_taken(self): self.report["begin_cases"][1]["event"]["after"]["vfx_stats"]["invalid_spawn_noops"]=0;self.reject()
    def test_no_color_write_in_invalid_spawn_branch(self): self.report["begin_cases"][1]["event"]["after"]["vfx_stats"]["parameter_writes"]=1;self.reject()
    def test_headless_still_native_cleanup(self): self.report["cases"][1]["actual_timer_callback_count"]=0;self.reject()
    def test_headless_still_actual_handle(self): self.report["begin_cases"][1]["event"]["after"]["fuse_handle_active"]=False;self.reject()
    def test_parent_fixture_not_started_twice(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_begin_validation.py").read_text(encoding="utf-8")
        self.assertIn('if result and "-UEPGrenadeHeadless" not in sys.argv:',text)
    def test_no_local_player_or_health_repair(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_begin_headless_validation.py").read_text(encoding="utf-8")
        for value in ('snapshot.bExperienceLoaded','"DedicatedServer"','"LyraCharacter"','IsPhaseActive'): self.assertIn(value,text)
        for value in ('GetPlayerController','set_property("Health"','SetControlRotation','K2_TeleportTo'): self.assertNotIn(value,text)
    def test_waits_for_actual_post_phase_population_and_canonical_binding(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_begin_headless_validation.py").read_text(encoding="utf-8")
        for value in ('self.health_fingerprint','if stable<.5','state.call_function("GetPawn")!=pawn','asc.get_property("AvatarActor")!=pawn'): self.assertIn(value,text)
