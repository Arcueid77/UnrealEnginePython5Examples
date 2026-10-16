"""Decision-only stencil policy; native discovery/setter own recursion/clamping."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterStencilModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.local, self.player = [], False, True
        self.components = [types.SimpleNamespace(call_function=lambda *args: self.calls.append(("component", *args))) for _ in range(3)]
        engine = types.ModuleType("unreal_engine")
        engine.find_class = lambda name: types.SimpleNamespace(name=name, get_cdo=lambda: types.SimpleNamespace(call_function=self.find))
        parent = types.ModuleType("uep_lyra_characters.team_cosmetics_mixin")
        class Team:
            def ClearInventory(self): pass
            def GetEmoteAudioComponent(self): pass
            def SetEmoteAudioComponent(self, AudioComponent): pass
            def ChangeQuickbarSlot(self, NewSlotIndex, SlotActionTag): pass
            def AddInitialInventory(self): pass
            def CreateOrUpdateOutlineIfNeeded(self, TeamID, OutlineColor): pass
            def OnTeamOrCosmeticsChanged(self, TeamID, TeamDisplayAsset): pass
        parent.LyraCharacterTeamPythonProfile = parent.LyraCharacterTeamBlueprintFallbackProfile = Team
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/stencil_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._stencil_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": engine, parent.__name__: parent}): spec.loader.exec_module(self.module)
        self.parent, self.profile = Team, self.module.LyraCharacterStencilPythonProfile
        self.actor = types.SimpleNamespace(call_function=self.actor_call, call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def find(self, name, actor, cls, children):
        self.calls.append(("query", name, actor, cls.name, children)); return self.components

    def actor_call(self, name):
        self.calls.append(("actor", name)); return self.local if name == "IsLocallyControlled" else self.player

    def invoke(self, team=7): self.profile.UpdateCustomStencilFromTeamID(self.actor, team)

    def test_each_native_control_flag_combination_uses_original_and_rule(self):
        for self.local, self.player in ((False, False), (False, True), (True, False), (True, True)):
            self.calls.clear(); self.invoke(); expected = 0 if self.local and self.player else 7
            with self.subTest(local=self.local, player=self.player):
                self.assertEqual(self.calls[:2], [("actor", "IsLocallyControlled"), ("actor", "IsPlayerControlled")])
                self.assertEqual(self.calls[-3:], [("component", "SetCustomDepthStencilValue", expected)]*3)

    def test_native_discovery_requests_primitives_and_actual_child_actor_recursion(self):
        self.invoke(); self.assertEqual(self.calls[2], ("query", "FindComponentsByClass", self.actor, "PrimitiveComponent", True))

    def test_negative_and_overflow_values_are_forwarded_to_native_setter_not_clamped_in_python(self):
        for value in (-1, 256, 65536):
            self.calls.clear(); self.invoke(value)
            with self.subTest(value=value): self.assertEqual(self.calls[-1], ("component", "SetCustomDepthStencilValue", value))

    def test_no_actor_stencil_property_or_render_custom_depth_toggle(self):
        self.invoke(); self.assertEqual(set(vars(self.actor)), {"call_function", "call_mixin_original", "_uep_character_stencil"})
        self.assertFalse(any("RenderCustomDepth" in str(call) for call in self.calls))

    def test_no_components_preserves_noop_without_inventing_writes(self):
        self.components = []; self.invoke(); counts = self.module.evidence(self.actor)
        self.assertEqual((counts["component_queries"], counts["component_writes"]), (1, 0))

    def test_repeats_and_counters_are_per_actor_pod_only(self):
        self.invoke(); self.invoke(); counts = self.module.evidence(self.actor)
        self.assertEqual((counts["python_calls"], counts["component_queries"], counts["component_writes"]), (2, 2, 6))
        self.assertTrue(all(type(value) is int for value in counts.values()))

    def test_seven_accepted_helpers_are_explicit_aliases_not_implicit_python_inheritance(self):
        for name in ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot", "AddInitialInventory", "CreateOrUpdateOutlineIfNeeded", "OnTeamOrCosmeticsChanged"):
            with self.subTest(name=name): self.assertIs(self.profile.__dict__[name], self.parent.__dict__[name])

    def test_fallback_only_calls_original_inherited_bp_with_exact_argument(self):
        self.module.LyraCharacterStencilBlueprintFallbackProfile.UpdateCustomStencilFromTeamID(self.actor, -1)
        self.assertEqual(self.calls, [("original", "UpdateCustomStencilFromTeamID", -1)])
