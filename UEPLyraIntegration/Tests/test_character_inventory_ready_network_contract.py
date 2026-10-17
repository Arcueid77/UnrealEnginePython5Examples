"""Native grant/replica comparison is required in addition to ready counters."""
import unittest
from test_character_initial_inventory_network_contract import reports as loadout_reports
from test_character_inventory_ready_contract import upgrade
from uep_lyra_characters.inventory_ready_contract import counts
from uep_lyra_characters.inventory_ready_network_contract import validate


def reports():
    values = loadout_reports()
    for peer, value in values.items():
        upgrade(value)
        if peer == "server":
            value.update(native_net_mode="DedicatedServer", owned_experience_proxies_created=24, natural_startup_readiness={name: counts(py=1, immediate=1) for name in ("A", "B0")})
            for item in value["cases"]:
                py = item["owner_observation"]["profile"] == "Python"
                item["owner_observation"]["readiness_counters"] = counts(py=int(py), fallback=int(not py), immediate=int(py))
                item["owner_observation"]["real_experience_factory_signal"] = True
        else: value.update(natural_startup_readiness=counts(), owned_experience_proxies_created=12)
    return values


class CharacterInventoryReadyNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(self.reports)
    def test_complete_shape_only_model(self): self.assertEqual(validate(self.reports)["native_ready_authority_trials"], 24)
    def test_actual_native_replica_not_only_ready_counter(self): self.reports["A"]["cases"][0]["replica_model"]["items"] = []; self.reject()
    def test_no_client_startup_authority_callback_invented(self): self.reports["A"]["natural_startup_readiness"] = counts(py=1, immediate=1); self.reject()
    def test_server_natural_experience_callback_required(self): self.reports["server"]["natural_startup_readiness"]["B0"] = counts(); self.reject()
    def test_deferred_wait_stays_explicitly_original(self): self.reports["B0"]["pending_inventory_wait_migrated"] = True; self.reject()
    def test_typed_caller_root_not_retained_on_server(self): self.reports["server"]["caller_roots"]["released"] = 0; self.reject()
    def test_server_last_original_inventory_restoration(self): self.reports["server"]["restore_frozen_before_release"] = False; self.reject()
    def test_private_network_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterReadyNetworkResult=x"]), "uep_lyra_characters.inventory_ready_network_validation")
    def test_restore_phase_never_recaptures_measured_grant(self):
        import ast
        from pathlib import Path
        from types import SimpleNamespace
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/inventory_ready_network_validation.py"
        cls = next(value for value in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(value, ast.ClassDef) and value.name == "Server")
        calls = []
        class Base:
            def observe(self): calls.append("base")
        namespace = dict(LoadoutServer=Base, Trial=None, server_gate=lambda report: None)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        instance = namespace["Server"].__new__(namespace["Server"])
        instance.current = dict(peer="A"); instance.trials = dict(A=SimpleNamespace(capture=lambda: calls.append("capture") or True))
        instance.phase = "restore"; instance.observe(); self.assertEqual(calls, ["base"])
        calls.clear(); instance.phase = "grant"; instance.observe(); self.assertEqual(calls, ["capture", "base"])
