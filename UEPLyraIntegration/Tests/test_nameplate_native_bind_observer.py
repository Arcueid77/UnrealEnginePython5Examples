"""Observation must not fabricate a production bind or registry mutation."""
import ast
from pathlib import Path
import unittest
import test_nameplate_mixin as fixtures


class BindObservation(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.NameplatePolicy()
        self.fixture.setUp()

    def test_normal_play_has_no_observer(self):
        self.assertEqual(self.fixture.module._validation_bind_observers, [])
        self.assertEqual(self.fixture.module._validation_release_observers, [])

    def test_native_release_epochs_notify_without_polling(self):
        seen = []
        self.fixture.module._validation_release_observers.append(seen.append)
        self.fixture.bind()
        self.fixture.widget.UnbindIndicator(self.fixture.indicator)
        self.fixture.widget.Destruct()
        self.fixture.widget.__uep_mixin_teardown__()
        self.assertEqual(seen, [self.fixture.widget]*3)

    def test_bp_comparator_preserves_native_construct_and_hidden_rendering(self):
        source = (Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_nameplate_probe.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
                             node.func.attr == "AddToViewport" for node in ast.walk(tree)))
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
                            node.func.attr == "call_function" and isinstance(node.args[0], ast.Constant) and
                            node.args[0].value == "SetRenderOpacity" and node.args[1].value == 0.0 for node in ast.walk(tree)))

    def test_observer_sees_native_data_before_immediate_init_registration(self):
        seen = []
        def observe(widget, indicator):
            self.assertIs(widget.Pawn, self.fixture.pawn)
            self.assertIs(indicator, self.fixture.indicator)
            self.assertEqual(widget._uep_np_init_callbacks, 0)
            self.assertIsNone(widget._uep_np_extension)
            seen.append(widget)
        self.fixture.module._validation_bind_observers.append(observe)
        self.fixture.bind()
        self.assertEqual(seen, [self.fixture.widget])
        self.assertEqual(self.fixture.widget._uep_np_init_callbacks, 1)

    def test_comparator_selector_does_not_mutate_registry_in_native_callback(self):
        source = (Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_nameplate_probe.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "capture_native_bind")
        calls = [node for node in ast.walk(method) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
        self.assertFalse(any(node.func.attr in ("set_mixin_profile", "register_mixin", "register_mixin_profile") for node in calls))
        self.assertTrue(any(node.func.attr == "set_property" and isinstance(node.args[0], ast.Constant) and node.args[0].value == "PythonMixinProfile" for node in calls))

    def test_shutdown_uses_pre_exit_native_placement_snapshot_only(self):
        scripts = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"
        tree = ast.parse((scripts/"uep_lyra_hud/shutdown_validation.py").read_text(encoding="utf-8"))
        finalize = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_finalize")
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                             node.func.id == "read_placement" for node in ast.walk(finalize)))
        tree = ast.parse((scripts/"uep_lyra_weapon_network.py").read_text(encoding="utf-8"))
        finish = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_finish")
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                            node.func.id == "read_placement" for node in ast.walk(finish)))
