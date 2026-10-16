"""UE 5.8.1 reflected observation API names and output order, not runtime proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class DeathObservation(unittest.TestCase):
    def setUp(self):
        self.calls = []
        native, observer = types.ModuleType("unreal_engine"), types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        self.outputs = {}
        def call(name, *args):
            self.calls.append((name, args)); return self.outputs.get(name)
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=call))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/death_observation.py"
        spec = importlib.util.spec_from_file_location("death_observation_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)

    def test_exact_reflected_effect_context_getters(self):
        self.assertEqual(self.module.context("native-handle"), dict(instigator=None, causer=None, source=None))
        self.assertEqual(self.calls, [(name, ("native-handle",)) for name in (
            "EffectContextGetInstigatorActor", "EffectContextGetEffectCauser", "EffectContextGetSourceObject")])

    def test_native_server_observer_uses_death_instead_of_inactive_respawn(self):
        death, respawn = object(), object()
        self.assertIs(self.module.source_owner(death, respawn, True), death)

    def test_standalone_observer_keeps_original_active_respawn_owner(self):
        death, respawn = object(), object()
        self.assertIs(self.module.source_owner(death, respawn), respawn)

    def test_gameplay_tag_single_output_tuple(self):
        self.outputs["BreakGameplayTagContainer"] = ([types.SimpleNamespace(TagName="z"), types.SimpleNamespace(TagName="a")],)
        self.assertEqual(self.module.tags("container"), ["a", "z"])

    def test_native_break_cue_output_order(self):
        vector = types.SimpleNamespace(x=0., y=0., z=0.)
        tag = types.SimpleNamespace(TagName="death")
        self.outputs["BreakGameplayCueParameters"] = (100., 100., "context", tag, tag, "source-tags", "target-tags",
            vector, vector, None, None, None, None, 1, 1, None, False)
        self.outputs["BreakGameplayTagContainer"] = ([],)
        row = self.module.cue(None, "cue")
        self.assertEqual((row["raw"], row["normalized"], row["effect_level"], row["ability_level"]), (100., 100., 1, 1))
        self.assertEqual(row["location"], [0., 0., 0.]); self.assertFalse(row["replicate_location"])
