"""Extracted fixture barrier model; native proof requires real clients."""
import ast
from pathlib import Path
import types
import unittest
from uep_lyra_abilities.reload_magazine_contract import REFUSED, EARLY


class ReloadReplicaBarrier(unittest.TestCase):
    def test_final_snapshot_waits_for_actual_replication_not_local_end(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/reload_magazine_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Client")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "may_capture_end")
        namespace = dict(REFUSED=REFUSED, EARLY=EARLY)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(file), "exec"), namespace)
        owner = types.SimpleNamespace(name="empty-magazine", row=dict(initial_ammo=(0, 12, 24), expected_ammo=(12, 12, 12)), ammo=lambda: (0, 12, 24))
        self.assertFalse(namespace["may_capture_end"](owner))
        owner.ammo = lambda: (12, 12, 12)
        self.assertTrue(namespace["may_capture_end"](owner))
        owner.name, owner.ammo = "native-cancel", lambda: (0, 12, 24)
        self.assertTrue(namespace["may_capture_end"](owner))
        owner.name = "no-spare-refused"
        self.assertTrue(namespace["may_capture_end"](owner))
