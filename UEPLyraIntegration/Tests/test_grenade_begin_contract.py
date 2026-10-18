"""BeginPlay Actor-timer evidence counterexamples,not native runtime proof."""
import copy
import importlib.util
from pathlib import Path
import unittest
from uep_lyra_weapons.grenade_begin_contract import validate,PLAN

spec=importlib.util.spec_from_file_location("_begin_cleanup_contract_fixture",Path(__file__).with_name("test_grenade_cleanup_contract.py"))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def model():
    report=fixture.model();report.update(begin_cases=[],begin_play_replayed=False,python_timer_entry="KismetSystemLibrary.K2_SetTimer",native_named_actor_timer_binding=True,
        native_destroyed_actor_timers_naturally_expired=True,native_detonate_callback_observed=False,timer_drain_elapsed=1.516,timer_drain_expected_remaining=1.5,timer_drain_max_frame=1./60.)
    for cleanup,(name,profile) in zip(report["cases"],PLAN):
        py=profile=="Python";char=name=="character";actor=cleanup["actor"];instigator=cleanup["instigator"]
        before=dict(fuse_handle_exists=False,fuse_named_exists=False,cleanup_named_exists=False,capsule_ignores=["old"] if char else None,mesh_ignores=[])
        after=dict(fuse_handle_exists=True,fuse_handle_active=True,fuse_named_exists=True,cleanup_named_exists=True,fuse_property=2.,fuse_handle_remaining=2.,fuse_named_remaining=2.,cleanup_named_remaining=.16,
            vfx_helper_calls=1,trail_valid=True,capsule_ignores=[actor,"old"] if char else None,mesh_ignores=[instigator] if char else [])
        stats=dict(python_calls=int(py),fallback_calls=int(not py),material_requests=int(py),invalid_material_noops=0,character_capsule_ignores=int(py and char),character_mesh_ignores=int(py and char),
            non_character_skips=int(py and not char),invalid_capsule_noops=0,invalid_mesh_noops=0,vfx_calls=int(py),detonate_timers=int(py),timer_handle_writes=int(py),cleanup_timers=int(py))
        report["begin_cases"].append(dict(name=name,profile=profile,actor=actor,instigator=instigator,native_begin_count=1,event=dict(before=before,after=after,stats=stats),
            cleanup_timer_gone_after_callback=True,fuse_handle_exists_before_destroy=True,fuse_handle_gone_after_destroy=False,fuse_remaining_before_destroy=1.5))
    return report


class TestGrenadeBeginContract(unittest.TestCase):
    def setUp(self): self.report=model()
    def reject(self):
        with self.assertRaises(RuntimeError): validate(self.report)
    def test_complete_model_only(self): self.assertEqual(validate(self.report)["actual_actor_owned_fuse_timers"],6)
    def test_actual_begin_once(self): self.report["begin_cases"][0]["native_begin_count"]=2;self.reject()
    def test_no_begin_replay(self): self.report["begin_play_replayed"]=True;self.reject()
    def test_no_alternate_timer_owner(self): self.report["native_named_actor_timer_binding"]=False;self.reject()
    def test_actual_opaque_timer_handle(self): self.report["begin_cases"][0]["event"]["after"]["fuse_handle_exists"]=False;self.reject()
    def test_name_and_handle_match(self): self.report["begin_cases"][0]["event"]["after"]["fuse_named_remaining"]=1.;self.reject()
    def test_original_native_fuse_duration(self): self.report["begin_cases"][0]["event"]["after"]["fuse_property"]=.5;self.reject()
    def test_original_cleanup_duration(self): self.report["begin_cases"][0]["event"]["after"]["cleanup_named_remaining"]=.2;self.reject()
    def test_cleanup_is_one_shot(self): self.report["begin_cases"][0]["cleanup_timer_gone_after_callback"]=False;self.reject()
    def test_fuse_survives_cleanup(self): self.report["begin_cases"][0]["fuse_handle_exists_before_destroy"]=False;self.reject()
    def test_preserve_original_deferred_handle_after_actor_destroy(self): self.report["begin_cases"][0]["fuse_handle_gone_after_destroy"]=True;self.reject()
    def test_all_native_handles_naturally_expire(self): self.report["native_destroyed_actor_timers_naturally_expired"]=False;self.reject()
    def test_no_unverified_rpc_observation_claim(self): self.report["native_detonate_callback_observed"]=True;self.reject()
    def test_native_expiry_not_arbitrarily_delayed(self): self.report["timer_drain_elapsed"]=3.;self.reject()
    def test_native_vfx_called_once(self): self.report["begin_cases"][0]["event"]["after"]["vfx_helper_calls"]=2;self.reject()
    def test_noncharacter_does_not_install_ignores(self): self.report["begin_cases"][2]["event"]["after"]["mesh_ignores"]=["source"];self.reject()
    def test_fixture_uses_only_timer_queries(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_begin_validation.py").read_text(encoding="utf-8")
        for value in ('"K2_TimerExistsHandle"','"K2_TimerExists"','"K2_GetTimerRemainingTime"','"K2_GetTimerRemainingTimeHandle"'): self.assertIn(value,text)
        for value in ('call_function("K2_SetTimer"','call_function("ReceiveBeginPlay"','call_function("PostLaunchCleanup"','call_function("Detonate"','set_property("Timer"'): self.assertNotIn(value,text)
    def test_action_regression_keeps_current_complete_family(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_actions_validation.py").read_text(encoding="utf-8")
        self.assertIn('self.original_profile_classes',text);self.assertIn('for name,base in self.original_profile_classes.items()',text)
