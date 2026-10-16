import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class ReticleHostContracts(unittest.TestCase):
    def setUp(self):
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        native = types.ModuleType("unreal_engine")
        native.find_class = lambda name: name
        runtime = types.ModuleType("uep_runtime")
        runtime.SubscriptionScope = lambda: None
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/reticle_host_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._reticle_host_contract", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime, "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)
        self.widget = self.module.LyraReticleHostPythonProfile()
        self.calls = []
        self.widget.call_function = lambda *args: self.calls.append(args)

    def test_invalid_weapon_clears_then_stops(self):
        self.widget.OnWeaponChanged(None, None)
        self.assertEqual(self.calls, [("ClearExistingWidgets",)])
        self.assertEqual(self.module.snapshot()["weapon_changes"], 1)
        self.assertEqual(self.module.snapshot()["reticles_created"], 0)

    def test_clear_assigns_back_reflected_array(self):
        self.widget.SpawnedWidgets = ["one", "two"]
        self.widget.WidgetStack = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.widget.ClearExistingWidgets()
        self.assertEqual(self.calls, [("RemoveChild", "one"), ("RemoveChild", "two")])
        self.assertEqual(self.widget.SpawnedWidgets, [])

    def test_visibility_uses_native_death_state(self):
        self.widget.VisWrapper = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        for health, expected in ((None, 1), (types.SimpleNamespace(call_function=lambda name: False), 0),
                                 (types.SimpleNamespace(call_function=lambda name: True), 1)):
            self.widget.CurrentHealthComponent = health
            self.widget.UpdateVisibility()
            self.assertEqual(self.calls[-1], ("SetVisibility", expected))

    def test_profile_teardown_closes_but_keeps_reticles(self):
        closed = []
        self.widget._uep_reticle_host_scope = types.SimpleNamespace(close=lambda: closed.append(True))
        self.widget.SpawnedWidgets = ["native-reticle"]
        self.widget.__uep_mixin_teardown__()
        self.widget.__uep_mixin_teardown__()
        self.assertEqual(closed, [True])
        self.assertEqual(self.widget.SpawnedWidgets, ["native-reticle"])
        self.assertEqual(self.calls, [])

    def test_fallback_teardown_only_removes_its_native_delegate(self):
        widget = self.module.LyraReticleHostBlueprintFallbackProfile()
        widget.CurrentHealthComponent = "health"
        widget.call_function = lambda *args: self.calls.append(args)
        widget.__uep_mixin_teardown__()
        self.assertEqual(self.calls, [(self.module.CLEANUP_HELPER, "health")])

    def test_wrong_instigator_and_missing_fragment_do_not_create_reticles(self):
        for item in (types.SimpleNamespace(is_a=lambda cls: False),
                     types.SimpleNamespace(is_a=lambda cls: True, call_function=lambda *args: None)):
            self.widget.OnWeaponChanged(None, types.SimpleNamespace(call_function=lambda name: item))
        self.assertEqual(self.calls, [("ClearExistingWidgets",), ("ClearExistingWidgets",)])
        self.assertEqual(self.module.snapshot()["reticles_created"], 0)

    def test_native_creation_initializes_before_attaching_and_keeps_fill_alignment(self):
        created = []
        slot = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("slot",) + args))
        stack = types.SimpleNamespace(call_function=lambda name, child: self.calls.append((name, child)) or slot)
        self.widget.WidgetStack, self.widget.SpawnedWidgets = stack, []
        controller, weapon = object(), object()
        fragment = types.SimpleNamespace(ReticleWidgets=["reticle-a", "counter-a"])
        item = types.SimpleNamespace(is_a=lambda cls: True, call_function=lambda *args: fragment)

        def create(name, context, cls, owner):
            self.assertEqual((name, context, owner), ("Create", self.widget, controller))
            child = types.SimpleNamespace(call_function=lambda *args: self.calls.append((cls,) + args))
            created.append(child)
            return child

        library = types.SimpleNamespace(call_function=create)
        self.module.ue.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: library)

        def dispatch(name):
            if name == "ClearExistingWidgets":
                self.widget.ClearExistingWidgets()
            else:
                return controller

        self.widget.call_function = dispatch
        native_weapon = types.SimpleNamespace(call_function=lambda name: item)
        self.widget.OnWeaponChanged(weapon, native_weapon)
        self.assertEqual(self.widget.SpawnedWidgets, created)
        self.assertEqual(self.calls, [
            ("reticle-a", "InitializeFromWeapon", native_weapon), ("AddChildToOverlay", created[0]),
            ("slot", "SetHorizontalAlignment", 0), ("slot", "SetVerticalAlignment", 0),
            ("counter-a", "InitializeFromWeapon", native_weapon), ("AddChildToOverlay", created[1]),
            ("slot", "SetHorizontalAlignment", 0), ("slot", "SetVerticalAlignment", 0)])

    def test_death_closes_once_and_tick_does_not_rebind_same_health(self):
        bound, closed = [], []
        self.module.SubscriptionScope = lambda: types.SimpleNamespace(
            bind_event=lambda *args: bound.append(args), close=lambda: closed.append(True))
        health = object()
        pawn = types.SimpleNamespace(call_function=lambda *args: health)
        controller = types.SimpleNamespace(call_function=lambda name: pawn)
        self.widget.call_function = lambda name, *args: controller if name == "GetOwningPlayer" else self.calls.append((name,) + args)
        self.widget.get_path_name = lambda: "test-host"
        self.widget.CurrentHealthComponent = None
        self.widget.OnCheckForDeath()
        self.widget.OnDeathStarted(None)
        self.widget.OnCheckForDeath()
        self.assertEqual(len(bound), 1)
        self.assertEqual(closed, [True])
        self.assertIsNone(self.widget._uep_reticle_host_scope)

    def test_invalid_pawn_preserves_authored_current_health_branch(self):
        old_health = object()
        self.widget.CurrentHealthComponent = old_health
        self.widget.call_function = lambda name: None
        self.widget.OnCheckForDeath()
        self.assertIsNone(self.widget.NewHealthComponent)
        self.assertIs(self.widget.CurrentHealthComponent, old_health)
        self.assertIsNone(self.widget._uep_reticle_host_scope)


if __name__ == "__main__":
    unittest.main()
