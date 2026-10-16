import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class OptionalReference(unittest.TestCase):
    def setUp(self):
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value.live
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/nameplate_refs.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._np_refs_test", source)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)

    def receiver(self, message, live=True):
        class Receiver:
            @property
            def proxy(self):
                raise RuntimeError(message)
        value = Receiver()
        value.live = live
        return value

    def test_only_invalid_optional_target_on_live_receiver_is_ignored(self):
        self.assertIsNone(self.module.optional_ref(self.receiver("uobject is in invalid state"), "proxy"))

    def test_dead_receiver_error_is_not_hidden(self):
        with self.assertRaisesRegex(RuntimeError, "invalid state"):
            self.module.optional_ref(self.receiver("uobject is in invalid state", False), "proxy")

    def test_unrelated_failure_is_not_hidden(self):
        with self.assertRaisesRegex(RuntimeError, "layout mismatch"):
            self.module.optional_ref(self.receiver("layout mismatch"), "proxy")
