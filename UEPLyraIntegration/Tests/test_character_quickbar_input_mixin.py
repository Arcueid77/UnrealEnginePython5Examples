"""Character input-policy models; no native event/RPC acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterQuickbarModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.slots, self.controller, self.quickbar = [], [object(), object(), None], object(), object()
        actor = types.SimpleNamespace(call_function=self.actor_call)
        self.actor = actor
        engine = types.ModuleType("unreal_engine"); structs = types.ModuleType("unreal_engine.structs")
        structs.GameplayEventData = lambda **fields: types.SimpleNamespace(**fields)
        lib = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        engine.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: lib) if name == "AbilitySystemBlueprintLibrary" else name
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        audio = types.ModuleType("uep_lyra_characters.emote_audio_mixin")
        class Parent:
            def ClearInventory(self): pass
            def GetEmoteAudioComponent(self): pass
            def SetEmoteAudioComponent(self, AudioComponent): pass
        audio.LyraCharacterAudioPythonProfile = audio.LyraCharacterAudioBlueprintFallbackProfile = Parent
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/quickbar_input_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._slot_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": engine, structs.__name__: structs, native.__name__: native, audio.__name__: audio}):
            spec.loader.exec_module(self.module)
        self.parent = Parent; self.python = self.module.LyraCharacterQuickbarPythonProfile
        self.actor.call_mixin_original = lambda *args: self.calls.append(("original", *args))
        self.quickbar = types.SimpleNamespace(call_function=lambda name: self.slots)
        self.controller = types.SimpleNamespace(call_function=lambda *args: self.quickbar)

    def actor_call(self, name):
        self.assertEqual(name, "GetController"); return self.controller

    def invoke(self, index, tag=None):
        tag = object() if tag is None else tag
        self.python.ChangeQuickbarSlot(self.actor, index, tag); return tag

    def test_occupied_slot_sends_original_actor_tag_and_double_magnitude(self):
        tag = self.invoke(1); call, = self.calls
        self.assertEqual(call[:3], ("SendGameplayEventToActor", self.actor, tag))
        self.assertEqual(vars(call[3]), {"EventMagnitude": 1.0})
        self.assertIs(type(call[3].EventMagnitude), float)

    def test_payload_does_not_invent_actor_target_instigator_or_event_tag_fields(self):
        self.invoke(0); self.assertEqual(set(vars(self.calls[0][3])), {"EventMagnitude"})

    def test_empty_valid_index_does_not_send_any_event(self):
        self.invoke(2); self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["empty_slot_noops"], 1)

    def test_negative_does_not_use_python_negative_array_index(self):
        self.invoke(-1); self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["invalid_index_noops"], 1)

    def test_past_end_is_a_safe_explicit_noop(self):
        self.invoke(99); self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["invalid_index_noops"], 1)

    def test_missing_controller_is_safe(self):
        self.controller = None; self.invoke(0)
        self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["missing_controller_noops"], 1)

    def test_missing_quickbar_is_safe(self):
        self.quickbar = None; self.invoke(0)
        self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["missing_quickbar_noops"], 1)

    def test_repeated_selection_is_not_suppressed(self):
        self.invoke(1); self.invoke(1); self.assertEqual(len(self.calls), 2)

    def test_arbitrary_slot_action_tag_is_forwarded_unchanged(self):
        tag = object(); self.invoke(1, tag); self.assertIs(self.calls[0][2], tag)

    def test_fallback_replays_only_original_function_once(self):
        tag = object(); self.module.LyraCharacterQuickbarBlueprintFallbackProfile.ChangeQuickbarSlot(self.actor, 1, tag)
        self.assertEqual(self.calls, [("original", "ChangeQuickbarSlot", 1, tag)])

    def test_all_three_accepted_methods_are_explicit_local_aliases(self):
        for profile in (self.python, self.module.LyraCharacterQuickbarBlueprintFallbackProfile):
            for name in ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent"):
                self.assertIs(profile.__dict__[name], getattr(self.parent, name))

    def test_evidence_is_per_actor_pod_without_global_actor_registry(self):
        value = self.module.evidence(self.actor); self.invoke(0)
        self.assertIs(value, self.module.evidence(self.actor)); self.assertEqual(value["events_sent"], 1)
        self.assertEqual(self.module.evidence(types.SimpleNamespace())["events_sent"], 0)
