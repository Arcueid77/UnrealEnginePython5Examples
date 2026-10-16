import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class PoolMembershipTests(unittest.TestCase):
    def setUp(self):
        self.calls, self.removed = [], []
        native = types.ModuleType("unreal_engine")
        native.find_class = lambda name: name
        native.add_ticker = lambda callback: self.calls.append("ticker") or 17
        native.remove_ticker = lambda handle: self.calls.append(("remove", handle))
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None and getattr(value, "alive", True)
        source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/pooled_widget_lifetime.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._pool_contract", source)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)
        self.members = []
        self.point = types.SimpleNamespace(is_a=lambda cls: cls == "UIExtensionPointWidget",
                                           call_function=lambda *args: list(self.members))
        tree = types.SimpleNamespace(is_a=lambda cls: cls == "WidgetTree", RootWidget=self.point)
        self.widget = types.SimpleNamespace(get_outer=lambda: tree)

    def watch(self):
        self.module.watch(self.widget, lambda widget: self.removed.append(widget))

    def test_one_shared_sampler_for_multiple_active_widgets(self):
        self.members = [self.widget]
        self.watch()
        self.watch()
        self.module.refresh()
        self.assertEqual(self.calls, ["ticker"])
        self.assertIs(self.widget._uep_pool_owner, self.point)
        self.assertEqual(self.removed, [])
        self.module.unwatch(self.widget)
        self.assertEqual(self.module.snapshot()["registered"], self.module.snapshot()["unregistered"])

    def test_release_disarms_once_without_destruct_and_blocks_rearm(self):
        self.members = [self.widget]
        self.watch()
        self.module.refresh()
        self.members = []
        self.module.refresh()
        self.module.refresh()
        self.assertEqual(self.removed, [self.widget])
        self.assertFalse(self.module.may_activate(self.widget))
        self.assertEqual(self.module.snapshot()["active_count"], 0)
        self.assertFalse(self.module.snapshot()["ticker_active"])

    def test_native_reinsertion_can_resume_without_event_replay(self):
        self.members = [self.widget]
        self.watch()
        self.module.refresh()
        self.members = []
        self.module.refresh()
        self.members = [self.widget]
        self.assertTrue(self.module.may_activate(self.widget))
        self.watch()
        self.module.refresh()
        self.assertEqual(self.module.snapshot()["active_count"], 1)
        self.assertEqual(self.removed, [self.widget])

    def test_pending_native_factory_is_not_prematurely_deactivated(self):
        self.watch()
        self.module.refresh()
        self.assertEqual(self.removed, [])
        self.members = [self.widget]
        self.module.refresh()
        self.assertIs(self.widget._uep_pool_owner, self.point)

    def test_nonpooled_viewport_widget_does_not_start_sampler(self):
        self.widget.get_outer = lambda: types.SimpleNamespace(is_a=lambda cls: False)
        self.watch()
        self.assertEqual(self.calls, [])

    def test_invalid_pool_is_disarmed_and_cleanup_is_idempotent(self):
        self.members = [self.widget]
        self.watch()
        self.module.refresh()
        self.point.alive = False
        self.module.refresh()
        self.module.unwatch(self.widget)
        self.assertFalse(self.module.may_activate(self.widget))
        self.assertEqual(self.calls.count(("remove", 17)), 1)

    def test_collapsed_consumer_can_rearm_on_native_reinsertion_without_tick(self):
        activated = []
        self.members = [self.widget]
        self.module.watch(self.widget, lambda widget: self.removed.append(widget), lambda widget: activated.append(widget))
        self.module.refresh()
        self.members = []
        self.module.refresh()
        self.module.refresh()
        self.assertEqual(self.removed, [self.widget])
        self.assertEqual(self.module.snapshot()["active_count"], 1)
        self.members = [self.widget]
        self.module.refresh()
        self.module.refresh()
        self.assertEqual(activated, [self.widget])
        self.assertEqual(self.module.snapshot()["reactivations"], 1)
        self.module.unwatch(self.widget)
        self.assertFalse(self.module.snapshot()["ticker_active"])

    def test_reentrant_activation_refresh_does_not_replay_callback(self):
        activated = []
        self.members = [self.widget]
        def activate(widget):
            activated.append(widget)
            self.module.refresh()
        self.module.watch(self.widget, lambda widget: None, activate)
        self.module.refresh()
        self.members = []
        self.module.refresh()
        self.members = [self.widget]
        self.module.refresh()
        self.assertEqual(activated, [self.widget])


if __name__ == "__main__":
    unittest.main()
