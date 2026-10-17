"""Native evidence counterexamples; model data are not runtime acceptance."""
import copy
from pathlib import Path
import unittest
from uep_lyra_abilities.grenade_widget_contract import validate


def model():
    report=dict(status="passed",error=None,native_mode="Standalone",owning_player_state="state",observation_errors=[],
        full_acceptance=False,network_acceptance=False,packaged_runtime=False,physical_input_tested=False,
        grenade_throw_projectile_damage_migrated=False,callback_replay=False,health_properties_written=False,
        ability_spec_properties_written=False,inventory_properties_written=False,native_ui_pool_written=False,
        native_give_clear_called_by_fixture=True,observers_restored=True,test_owned_specs_removed=True,
        reset_request_entry="SendGameplayEventToActor(GameplayEvent.RequestReset)",cases=[])
    for profile in ("BlueprintFallback","Python"):
        python=profile=="Python"
        counts=dict(avatar_python=2 if python else 0,removed_python=1 if python else 0,avatar_fallback=0 if python else 2,
            removed_fallback=0 if python else 1,existing_noops=int(python),nonlocal_noops=0,missing_subsystem_noops=0,
            registrations=int(python),unregistrations=int(python),opaque_default_noops=int(python))
        cls="/ShooterCore/Input/Abilities/GA_Grenade.GA_Grenade_C"
        row=dict(profile=profile,native_class=cls,initial_ui_invalid=True,reset_requests=2,new_pawns=["new1","new2"],quiet_ticks=20,
            original_handle_preserved=True,original_widget_restored=True,specs_restored=True,registered_widgets=["original","fixture"],native_callbacks=[])
        for method,before,after in zip(("K2_OnPawnAvatarSet","K2_OnPawnAvatarSet","K2_OnAbilityRemoved"),(False,True,True),(True,True,True)):
            row["native_callbacks"].append(dict(method=method,profile=profile,native_callback=True,cls=cls,owner="state",
                before=dict(valid=before,arity=2),after=dict(valid=after,arity=2),counts=copy.deepcopy(counts)))
        report["cases"].append(row)
    return report


class TestGrenadeWidgetContract(unittest.TestCase):
    def setUp(self): self.report=model()
    def reject(self):
        with self.assertRaises(RuntimeError): validate(self.report)
    def test_complete_model(self): self.assertEqual(validate(self.report)["native_avatar_callbacks"],4)
    def test_failed_native_status(self): self.report["status"]="failed";self.reject()
    def test_not_network_acceptance(self): self.report["network_acceptance"]=True;self.reject()
    def test_no_callback_replay(self): self.report["callback_replay"]=True;self.reject()
    def test_no_ui_pool_writes(self): self.report["native_ui_pool_written"]=True;self.reject()
    def test_both_profiles_required(self): self.report["cases"].pop();self.reject()
    def test_actual_class_required(self): self.report["cases"][0]["native_class"]="PythonDerived";self.reject()
    def test_two_real_pawns_required(self): self.report["cases"][1]["new_pawns"]=["same","same"];self.reject()
    def test_quiet_interval_required(self): self.report["cases"][0]["quiet_ticks"]=19;self.reject()
    def test_original_spec_required(self): self.report["cases"][0]["original_handle_preserved"]=False;self.reject()
    def test_duplicate_widget_rejected(self): self.report["cases"][1]["registered_widgets"].append("extra");self.reject()
    def test_exact_native_event_count(self): self.report["cases"][1]["native_callbacks"].pop();self.reject()
    def test_actual_native_callback(self): self.report["cases"][0]["native_callbacks"][0]["native_callback"]=False;self.reject()
    def test_correct_owning_actor(self): self.report["cases"][1]["native_callbacks"][0]["owner"]="pawn";self.reject()
    def test_native_ref_return_shape(self): self.report["cases"][0]["native_callbacks"][0]["after"]["arity"]=1;self.reject()
    def test_native_opaque_handle_behavior_matches_original(self): self.report["cases"][1]["native_callbacks"][-1]["after"]["valid"]=False;self.reject()
    def test_existing_handle_is_noop(self): self.report["cases"][1]["native_callbacks"][-1]["counts"]["registrations"]=2;self.reject()
    def test_observer_restored(self): self.report["observers_restored"]=False;self.reject()
    def test_clone_spec_removed(self): self.report["test_owned_specs_removed"]=False;self.reject()
    def test_fixture_uses_native_inputs_not_callback_replay(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_widget_validation.py").read_text(encoding="utf-8")
        for value in ('"K2_GiveAbility"','"ClearAbility"','"SendGameplayEventToActor"','"GetAllEntries"'): self.assertIn(value,text)
        for value in ('call_function("K2_OnPawnAvatarSet"','call_function("K2_OnAbilityRemoved"','set_property("Health"','set_property("Extension"'): self.assertNotIn(value,text)
    def test_removed_target_remains_observable_without_rooting_dead_ability(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_widget_observation.py").read_text(encoding="utf-8")
        self.assertIn('instance.get_path_name()==observer.target_path',text);self.assertNotIn('instance==observer.clone',text)
