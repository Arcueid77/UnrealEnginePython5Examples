"""Literal legacy forwarding and raw accepted profile objects."""
import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_team_listener_mixin as listener_models


class CharacterLegacyPlayerInfoPolicyModels(unittest.TestCase):
    def setUp(self):
        setup = listener_models.CharacterTeamListenerPolicyModels(); setup.setUp()
        parent = types.ModuleType("uep_lyra_characters.team_listener_mixin")
        self.parent, self.fallback_parent = setup.python, setup.fallback
        parent.LyraCharacterTeamListenerPythonProfile, parent.LyraCharacterTeamListenerBlueprintFallbackProfile = self.parent, self.fallback_parent
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/legacy_player_info_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._legacy_player_info_policy_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {parent.__name__: parent}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterLegacyPlayerInfoPythonProfile, self.module.LyraCharacterLegacyPlayerInfoBlueprintFallbackProfile
        self.actor, self.calls = setup.actor, setup.calls

    def test_original_zero_and_null_defaults_not_actual_team_query(self):
        self.python.OnRep_PlayerInfo(self.actor); self.assertEqual(self.calls, [("actor", "OnTeamOrCosmeticsChanged", 0, None)])
    def test_each_repeat_forwards_once(self):
        self.python.OnRep_PlayerInfo(self.actor); self.python.OnRep_PlayerInfo(self.actor)
        self.assertEqual(self.module.evidence(self.actor)["team_forwards"], 2); self.assertEqual(len(self.calls), 2)
    def test_no_authority_or_local_control_guard_added(self):
        self.python.OnRep_PlayerInfo(self.actor); self.assertEqual(len(self.calls), 1)
    def test_fallback_calls_exact_original(self):
        self.fallback.OnRep_PlayerInfo(self.actor); self.assertEqual(self.calls, [("original", "OnRep_PlayerInfo")])
    def test_python_does_not_fall_through_to_original(self):
        self.python.OnRep_PlayerInfo(self.actor); self.assertFalse(any(value[0] == "original" for value in self.calls))
    def test_original_no_argument_signature(self):
        for profile in (self.python, self.fallback): self.assertEqual(list(inspect.signature(profile.OnRep_PlayerInfo).parameters), ["self"])
    def test_all_nineteen_accepted_raw_aliases(self):
        for name, value in self.parent.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], value)
    def test_all_fourteen_fallback_aliases(self):
        for name, value in self.fallback_parent.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.fallback.__dict__[name], value)
    def test_counts_store_no_actors_or_callbacks(self):
        self.python.OnRep_PlayerInfo(self.actor); self.assertTrue(all(type(value) is int for value in self.module.evidence(self.actor).values()))
    def test_two_instances_never_share_counters(self):
        other = types.SimpleNamespace(); self.module.evidence(self.actor)["python_calls"] = 7
        self.assertEqual(self.module.evidence(other)["python_calls"], 0)
