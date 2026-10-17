"""Local native Actor lifetime is distinct from owner ragdoll replication."""
import unittest
import ast
from pathlib import Path
import test_character_equipment_hide_network_contract as hide_models
from test_character_ragdoll_contract import upgrade, body, counts, CLASS
from uep_lyra_characters.ragdoll_network_contract import validate


def reports():
    values = hide_models.reports()
    for peer, value in values.items():
        upgrade(value); value.update(ragdoll_physics_replication_tested=False, network_owner_death_ragdoll_ingress_tested=False, local_ragdoll_cases=[])
        for profile in ("BlueprintFallback", "Python"):
            value["local_ragdoll_cases"].append(dict(profile=profile, actual_character_class=CLASS, native_role=3, owned_team_proxies_created=1,
                bp_reference_call=True, test_owned_nonreplicated_local_actor=True, actor_was_not_rooted=True, owned_actor_destroyed=True,
                owned_team_proxies_collected=True, original_active_proxies_preserved=True, ragdoll_quiet_after_destroy=True,
                latent_script_quiet_after_destroy=True, counters=counts(profile), native_after=body()))
    return values


class CharacterRagdollNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.reports)
    def test_complete_shape_is_only_model(self): self.assertEqual(validate(self.reports)["native_local_network_ragdoll_calls"], 6)
    def test_no_physics_replication_claim(self): self.reports["A"]["ragdoll_physics_replication_tested"] = True; self.reject()
    def test_no_network_owner_death_claim(self): self.reports["server"]["network_owner_death_ragdoll_ingress_tested"] = True; self.reject()
    def test_not_actual_player_pawn_physics_mutation(self): self.reports["B0"]["local_ragdoll_cases"][1]["test_owned_nonreplicated_local_actor"] = False; self.reject()
    def test_exact_owned_observer_cleanup(self): self.reports["A"]["local_ragdoll_cases"][0]["owned_team_proxies_collected"] = False; self.reject()
    def test_native_physics_state_required(self): self.reports["A"]["local_ragdoll_cases"][0]["native_after"]["simulating"] = False; self.reject()
    def test_destroyed_actor_latent_work_quiet(self): self.reports["A"]["local_ragdoll_cases"][0]["latent_script_quiet_after_destroy"] = False; self.reject()
    def test_clients_wait_for_server_global_inventory_barrier(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/ragdoll_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); client = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Client")
        tick = next(node for node in client.body if isinstance(node, ast.FunctionDef) and node.name == "tick")
        tokens = [node for node in ast.walk(tick) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "token"]
        self.assertTrue(any(any(isinstance(arg, ast.Constant) and arg.value == "ragdoll-start.json" for arg in node.args) for node in tokens))
    def test_server_publishes_global_barrier_before_running_local_trials(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/ragdoll_network_validation.py"
        source = file.read_text(encoding="utf-8"); self.assertIn('peer+"-equipment-hide.json"', source)
        self.assertLess(source.index('atomic_write(self.root/"ragdoll-start.json"'), source.index('if not self.advance_ragdoll(self.trials["A"]'))
