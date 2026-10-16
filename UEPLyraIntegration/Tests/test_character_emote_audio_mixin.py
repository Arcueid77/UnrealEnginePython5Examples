"""BP Interface property/nullable/out-reference models; not native audio proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterAudioModels(unittest.TestCase):
    def setUp(self):
        self.value, self.calls = None, []
        parent = types.ModuleType("uep_lyra_characters.inventory_clear_mixin")
        class ClearPython:
            def ClearInventory(self): pass
        class ClearBlueprint:
            def ClearInventory(self): pass
        parent.LyraCharacterInventoryPythonProfile, parent.LyraCharacterInventoryBlueprintFallbackProfile = ClearPython, ClearBlueprint
        self.parent = parent
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/emote_audio_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._audio_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {parent.__name__: parent}): spec.loader.exec_module(self.module)
        self.actor = types.SimpleNamespace(get_property=lambda name: self.value, set_property=self.set,
            call_mixin_original=self.original)
        self.python = self.module.LyraCharacterAudioPythonProfile
        self.blueprint = self.module.LyraCharacterAudioBlueprintFallbackProfile

    def set(self, name, value): self.calls.append(("set", name, value)); self.value = value
    def original(self, method, *args):
        self.calls.append(("original", method, *args))
        if method == "GetEmoteAudioComponent": return (self.value,)
        if method == "SetEmoteAudioComponent": self.value, = args

    def test_null_getter_uses_exact_explicit_named_object_output(self):
        self.assertEqual(self.python.GetEmoteAudioComponent(self.actor), {"AudioComponent": None})
        self.assertIs(self.python.GetEmoteAudioComponent.uep_named_outputs, True)

    def test_getter_preserves_native_component_reference(self):
        self.value = object(); result = self.python.GetEmoteAudioComponent(self.actor)
        self.assertIs(result["AudioComponent"], self.value)

    def test_setter_writes_only_original_instance_field(self):
        value = object(); self.python.SetEmoteAudioComponent(self.actor, value)
        self.assertEqual(self.calls, [("set", "Emote_AudioComponent", value)])

    def test_null_setter_clears_original_field(self):
        self.value = object(); self.python.SetEmoteAudioComponent(self.actor, None)
        self.assertIsNone(self.value)

    def test_fallback_get_unpacks_actual_out_tuple_then_named_output(self):
        self.value = object(); self.assertIs(self.blueprint.GetEmoteAudioComponent(self.actor)["AudioComponent"], self.value)
        self.assertEqual(self.calls, [("original", "GetEmoteAudioComponent")])
        self.assertIs(self.blueprint.GetEmoteAudioComponent.uep_named_outputs, True)

    def test_fallback_set_calls_original_without_duplicate_property_write(self):
        value = object(); self.blueprint.SetEmoteAudioComponent(self.actor, value)
        self.assertEqual(self.calls, [("original", "SetEmoteAudioComponent", value)])

    def test_profile_switch_reads_shared_instance_property_not_profile_cache(self):
        value = object(); self.python.SetEmoteAudioComponent(self.actor, value)
        self.assertIs(self.blueprint.GetEmoteAudioComponent(self.actor)["AudioComponent"], value)
        self.blueprint.SetEmoteAudioComponent(self.actor, None)
        self.assertIsNone(self.python.GetEmoteAudioComponent(self.actor)["AudioComponent"])

    def test_reused_clear_method_is_explicit_in_each_local_class_dictionary(self):
        self.assertIs(self.python.__dict__["ClearInventory"], self.parent.LyraCharacterInventoryPythonProfile.ClearInventory)
        self.assertIs(self.blueprint.__dict__["ClearInventory"], self.parent.LyraCharacterInventoryBlueprintFallbackProfile.ClearInventory)

    def test_per_actor_evidence_is_mutable_pod_and_has_no_global_actor_map(self):
        before = self.module.evidence(self.actor); self.python.GetEmoteAudioComponent(self.actor)
        self.assertIs(before, self.module.evidence(self.actor)); self.assertEqual(before["python_gets"], 1)
        other = types.SimpleNamespace(get_property=lambda name: None)
        self.assertEqual(self.module.evidence(other)["python_gets"], 0)

    def test_no_audio_playback_animation_or_actor_subclass_reimplementation(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/emote_audio_mixin.py"
        source = file.read_text(encoding="utf-8")
        for forbidden in ("PlaySound", "SpawnSound", "Montage_", "add_to_root", "ue.uclass", "_actors ="):
            self.assertNotIn(forbidden, source)

    def test_second_bp_probe_is_stage_only_true_interface_message_transport(self):
        file = Path(__file__).resolve().parents[1]/"Tools/generate_character_audio_probe.py"
        source = file.read_text(encoding="utf-8")
        self.assertIn("graph.graph_add_node(K2Node_Message)", source)
        self.assertIn("message.FunctionReference = references[method]", source)
        self.assertIn("stage_only=True, gameplay_business=False", source)
        self.assertIn("original_animation_notify_unchanged=True", source)
