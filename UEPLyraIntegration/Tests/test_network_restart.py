import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class RestartLifetime(unittest.TestCase):
    def load(self, pawn):
        native = types.ModuleType("unreal_engine")
        native.find_object = lambda path: pawn
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None and value.live
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_network_restart.py"
        spec = importlib.util.spec_from_file_location("_restart_lifetime", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(module)
        return module

    def pawn(self, authority=True, destroys=True):
        pawn = types.SimpleNamespace(live=True, calls=[])
        def call(name):
            pawn.calls.append(name)
            if name == "HasAuthority":
                return authority
            if name == "K2_DestroyActor" and destroys:
                pawn.live = False
        pawn.call_function = call
        return pawn

    def test_server_uses_native_destruction_not_lifecycle_replay(self):
        pawn = self.pawn()
        result = self.load(pawn).retire_old_pawn("old")
        self.assertEqual(pawn.calls, ["HasAuthority", "K2_DestroyActor"])
        self.assertTrue(result["native_destroy_complete"])
        self.assertFalse(result["manual_lifecycle_event"])
        self.assertFalse(result["death_ability_tested"])

    def test_remote_or_failed_destroy_is_rejected(self):
        for pawn in (self.pawn(authority=False), self.pawn(destroys=False)):
            with self.assertRaises(RuntimeError):
                self.load(pawn).retire_old_pawn("old")

    def test_already_destroyed_is_not_relabelled_as_an_executed_call(self):
        result = self.load(None).retire_old_pawn("old")
        self.assertTrue(result["native_destroy_complete"])
        self.assertFalse(result["fixture_native_destroy_called"])

    def test_client_source_endplay_uses_native_component_destruction(self):
        source = self.pawn()
        def destroy(name, caller):
            self.assertEqual(name, "K2_DestroyComponent")
            self.assertIs(caller, source)
            source.live = False
        source.call_function = destroy
        pawn = self.pawn()
        pawn.call_function = lambda *args: [source]
        result = self.load(pawn).retire_client_sources("replicated-old", "SourceClass")
        self.assertEqual(result["native_source_destroy_calls"], 1)
        self.assertTrue(result["all_sources_destroyed"])
        self.assertFalse(result["manual_lifecycle_event"])
