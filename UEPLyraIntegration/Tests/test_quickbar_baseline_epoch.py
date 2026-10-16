"""Execute the actual reconciliation method with small native-widget fakes."""
import ast
from pathlib import Path
import types
import unittest


class Widget:
    def __init__(self, index=0, numeric=999.0):
        self.SlotIndex, self.SlotInputAction, self.numeric = index, "action", numeric
        self.calls, self.mounted = [], True

    def get_class(self):
        return "retained-class"

    def add_to_root(self):
        self.calls.append(("root",))

    def AddToViewport(self, order):
        self.calls.append(("AddToViewport", order))
        self.mounted = True

    def call_function(self, name, *args):
        self.calls.append((name,)+args)
        return self.mounted if name == "IsInViewport" else None


class QuickBarBaselineEpochTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_quickbar_probe.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "QuickBarSlotsProbe")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "reconcile")
        module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
        namespace = {"valid": lambda widget: widget is not None,
                     "slots": types.SimpleNamespace(RESUME="resume"),
                     "ue": types.SimpleNamespace(set_mixin_profile=lambda widget, profile: widget.calls.append(("profile", profile)))}
        exec(compile(module, str(source), "exec"), namespace)
        self.owned = [Widget(index) for index in range(3)]
        self.baselines = [Widget(index, 84.0 if index == 1 else 60.0) for index in range(3)]
        self.created, self.closes = [], 0
        self.probe = types.SimpleNamespace(pairs=list(zip(self.owned, self.baselines)), world_token="old", reused_baseline_epochs=0)
        def close():
            self.closes += 1
            self.probe.pairs = []
        def create(cls):
            result = Widget()
            self.created.append(result)
            return result
        self.probe.close = close
        self.controller = types.SimpleNamespace(create_widget=create)
        self.reconcile = types.MethodType(namespace["reconcile"], self.probe)

    def test_same_widgets_new_world_preserve_original_numeric_state(self):
        self.reconcile(self.controller, self.owned, "new")
        self.assertEqual(self.created, [])
        self.assertEqual(self.closes, 0)
        self.assertEqual(self.baselines[1].numeric, 84.0)
        self.assertEqual(self.probe.reused_baseline_epochs, 1)
        for widget in self.baselines:
            self.assertIn(("SetOwningPlayer", self.controller), widget.calls)
            self.assertIn(("resume",), widget.calls)
            self.assertFalse(any(call[0] in ("OnInitialized", "Construct", "SetCurrentValue") for call in widget.calls))

    def test_detached_original_baseline_uses_native_remount(self):
        self.baselines[1].mounted = False
        self.reconcile(self.controller, self.owned, "new")
        self.assertIn(("AddToViewport", 450), self.baselines[1].calls)
        self.assertNotIn(("AddToViewport", 450), self.baselines[0].calls)

    def test_same_world_has_no_replay_or_new_widget(self):
        self.reconcile(self.controller, self.owned, "old")
        self.assertEqual(self.created, [])
        self.assertTrue(all(not widget.calls for widget in self.baselines))

    def test_new_production_identity_gets_fresh_original_baseline(self):
        owned = [Widget(index) for index in range(3)]
        self.reconcile(self.controller, owned, "new")
        self.assertEqual(self.closes, 1)
        self.assertEqual(len(self.created), 3)
        self.assertEqual(self.created[1].numeric, 999.0)
        self.assertEqual([pair[0] for pair in self.probe.pairs], owned)


if __name__ == "__main__":
    unittest.main()
