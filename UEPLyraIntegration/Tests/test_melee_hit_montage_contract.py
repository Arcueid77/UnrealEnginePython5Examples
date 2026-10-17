"""Helper report counterexamples; no host shape is native execution evidence."""
import copy
from pathlib import Path
import unittest
from uep_lyra_abilities.melee_hit_montage_contract import PLAN, ASSETS, validate, network


def report():
    value = dict(status="passed", error=None, actual_granted_primary_instance=True,
        actual_ability_class="/ShooterCore/Game/Melee/GA_Melee.GA_Melee_C", fixture_activated_ability=False, fixture_granted_ability=False,
        gameplay_state_delivered_by_files=False, full_acceptance=False, network_acceptance=False, packaged_runtime=False, physical_input_tested=False,
        whole_melee_activation_trace_damage_migrated=False, original_profile_restored=True, native_specs_unchanged=True,
        caller_roots=dict(created=1, released=1), control_actor_destroyed=True, quiet_after_helper_calls=True, cases=[])
    for case in PLAN:
        x, y, z = case["normal"]; forward, right = (x, y) if case["target"] == "native-identity-control" else (-x, -y)
        choice = ("front" if forward > 0 else "back") if -.5 <= right <= .5 else ("left" if right > 0 else "right")
        rows = {key: dict(result=ASSETS[choice], counters=dict(python_calls=int(python), fallback_calls=int(not python), invalid_actor_native_fallback=0),
            last=dict(forward_dot=forward, right_dot=right, choice=choice) if python else None) for key, python in (("blueprint", False), ("python", True))}
        value["cases"].append(dict(input=copy.deepcopy(case), native_normal=case["normal"][:], native_forward_dot=forward, native_right_dot=right,
            target_path=case["target"], native_state_before=dict(active=False, health=100.), native_state_after=dict(active=False, health=100.), **rows))
    return value


class MeleeHitContractModels(unittest.TestCase):
    def setUp(self): self.value = report()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError)): validate(self.value)
    def test_complete_synthetic_shape_not_native_execution(self): self.assertEqual(validate(self.value)["actual_native_helper_pairs"], 32)
    def test_named_native_bp_output_cannot_be_wrong_even_if_both_agree(self):
        self.value["cases"][0]["blueprint"]["result"] = self.value["cases"][0]["python"]["result"] = ASSETS["front"]; self.reject()
    def test_exact_boundary_must_not_be_float_narrowed(self):
        row = next(row for row in self.value["cases"] if row["input"]["name"] == "outside-positive")
        row["native_normal"][1] = .5; self.reject()
    def test_no_double_original_after_python(self): self.value["cases"][0]["python"]["counters"]["fallback_calls"] = 1; self.reject()
    def test_valid_actor_matrix_cannot_fall_back_to_original(self): self.value["cases"][0]["python"]["counters"]["invalid_actor_native_fallback"] = 1; self.reject()
    def test_helper_state_invariance_required(self): self.value["cases"][0]["native_state_after"]["health"] = 0.; self.reject()
    def test_granted_instance_not_a_cdo(self): self.value["actual_granted_primary_instance"] = False; self.reject()
    def test_no_trace_damage_acceptance_from_helper(self): self.value["whole_melee_activation_trace_damage_migrated"] = True; self.reject()
    def test_native_basis_control_must_be_used(self): self.value["cases"][0]["python"]["last"]["forward_dot"] = 1.; self.reject()
    def test_caller_roots_are_balanced(self): self.value["caller_roots"]["released"] = 0; self.reject()
    def test_owned_actor_is_destroyed(self): self.value["control_actor_destroyed"] = False; self.reject()
    def test_source_uses_native_makevector_not_narrowing_wrapper(self):
        source = (Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/melee_hit_montage_validation.py").read_text(encoding="utf-8")
        self.assertIn('call_function("MakeVector", *case["normal"])', source)
        self.assertNotIn('call_function("TryActivateAbilityByClass"', source)
    def test_explicit_entry_disarms_commandlet(self):
        from uep_lyra_hud.startup import validation_module
        flag = "-UEPMeleeHitMontageResult=x"
        self.assertEqual(validation_module([flag]), "uep_lyra_abilities.melee_hit_montage_validation")
        self.assertIsNone(validation_module(["-run=Py", flag]))


def reports():
    values = {peer: report() for peer in ("server", "A", "B0")}
    for peer, role, mode, player in (("server", 3, "DedicatedServer", 1), ("A", 2, "Client", 1), ("B0", 2, "Client", 2)):
        values[peer].update(peer=peer, native_role=role, native_net_mode=mode, player_id=player, run_id="same-run",
            helper_two_owner_network_tested=True)
    values["server"].update(server_waited_for_client_process_exit=True, all_helper_owners_restored_before_release=True,
        other_authority_owner_unchanged=True, authority_player_ids=dict(A=1, B0=2))
    return values


class MeleeNetworkHelperModels(unittest.TestCase):
    def setUp(self): self.values = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError)): network(self.values)
    def test_complete_three_world_shape_is_not_native_execution(self): self.assertEqual(network(self.values)["actual_worlds"], 3)
    def test_both_owners_must_be_distinct(self): self.values["B0"]["player_id"] = 1; self.reject()
    def test_native_client_role_required(self): self.values["A"]["native_role"] = 3; self.reject()
    def test_real_native_netmode_required(self): self.values["A"]["native_net_mode"] = "Standalone"; self.reject()
    def test_foreign_authority_unchanged_required(self): self.values["server"]["other_authority_owner_unchanged"] = False; self.reject()
    def test_owner_cleanup_precedes_release(self): self.values["server"]["all_helper_owners_restored_before_release"] = False; self.reject()
    def test_actual_client_process_exit_barrier_required(self): self.values["server"]["server_waited_for_client_process_exit"] = False; self.reject()
    def test_native_runs_not_mixed(self): self.values["A"]["run_id"] = "other-run"; self.reject()
    def test_network_entry_commandlet_disarming(self):
        from uep_lyra_hud.startup import validation_module
        flag = "-UEPMeleeHitMontageNetworkResult=x"
        self.assertEqual(validation_module([flag]), "uep_lyra_abilities.melee_hit_montage_network_validation")
        self.assertIsNone(validation_module(["-run=Py", flag]))
