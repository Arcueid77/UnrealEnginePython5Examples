"""Fixture entry/lifetime checks only, not native collision acceptance."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"Overlay/Content/Scripts"))
from uep_lyra_hud.startup import validation_module


class InventoryFixture(unittest.TestCase):
    def test_only_explicit_runtime_flag_selects_lane(self):
        self.assertEqual(validation_module(["-UEPInventoryPadResult=report.json"]), "uep_lyra_world.inventory_pad_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPInventoryPadResult=report.json"]))
        self.assertEqual(validation_module(["-UEPInventoryPadPlayerResult=player.json"]), "uep_lyra_world.inventory_pad_player_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPInventoryPadPlayerResult=player.json"]))

    def test_native_spawn_collision_and_ticker_entries(self):
        source = (ROOT/"Overlay/Content/Scripts/uep_lyra_world/inventory_pad_validation.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for entry in ('"BeginDeferredActorSpawnFromClass"', '"FinishSpawningActor"', '.set_actor_location(', '.actor_destroy('):
            self.assertIn(entry, source)
        for event in ('"ReceiveTick"', '"ReceiveBeginPlay"', '"ReceiveEndPlay"', '"ReceiveActorBeginOverlap"'):
            self.assertNotIn(event, source)
        owned = [node for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and
                 isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "add_ticker"]
        self.assertEqual(len(owned), 1)

    def test_asset_generator_retains_original_branch_and_rejects_unsafe_shape(self):
        source = (ROOT/"Tools/generate_inventory_pad_mixin_assets.py").read_text(encoding="utf-8")
        self.assertIn('branch.node_find_pin("then").make_link_to(original_input)', source)
        self.assertIn('branch.node_find_pin("else").get_linked_to()', source)
        self.assertIn('original_semantics(graph, old_names, ignored)', source)
        self.assertIn('blueprint_configure_mixin(parent,', source)
        self.assertNotIn('blueprint_configure_mixin(child,', source)
