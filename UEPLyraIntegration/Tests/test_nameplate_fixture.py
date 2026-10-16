"""Prevent unsupported fixture entry points; not native nameplate acceptance."""
import ast
from pathlib import Path
import unittest


class NameplateFixtureEntryPoints(unittest.TestCase):
    def setUp(self):
        self.source = (Path(__file__).resolve().parents[1] /
                       "Overlay/Content/Scripts/uep_lyra_hud/nameplate_validation.py").read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_native_ticker_handle_is_owned_at_module_scope(self):
        owners = [node for node in self.tree.body if isinstance(node, ast.Assign) and
                  isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and
                  node.value.func.attr == "add_ticker"]
        self.assertEqual(len(owners), 1)
        self.assertTrue(any(isinstance(target, ast.Name) for target in owners[0].targets))

    def test_world_and_widget_queries_use_exposed_apis(self):
        self.assertIn('world.get_world_type()', self.source)
        self.assertIn('"GetAllWidgetsOfClass"', self.source)
        self.assertIn('"GetPlayerController", world, 0', self.source)
        self.assertNotIn('ue.get_objects(', self.source)
        self.assertNotIn('world.get_player_controller()', self.source)
        self.assertNotIn('get_property("WorldType")', self.source)
        self.assertNotIn('.broadcast_event(', self.source)
        self.assertIn('.broadcast("OnHealthChanged"', self.source)


if __name__ == "__main__":
    unittest.main()
