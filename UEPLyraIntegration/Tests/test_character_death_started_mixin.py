"""Native random/Delay policy and weak native continuation models only."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_ragdoll_mixin as ragdoll_models


class Info:
    def __init__(self, **fields): self.__dict__.update(fields)


class CharacterDeathStartedPolicyModels(unittest.TestCase):
    def setUp(self):
        setup = ragdoll_models.CharacterRagdollPolicyModels(); setup.setUp(); self.parent = setup.module
        self.calls, self.random_calls, self.tasks = [], [], {}; self.frame, self.now, self.profile = 10, 1., "Python"
        self.index, self.duration = 1, .3
        self.sense = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("sense",)+args))
        self.montages = [types.SimpleNamespace(get_path_name=lambda: "montage-A"), types.SimpleNamespace(get_path_name=lambda: "montage-B")]
        self.fields = {"Death Montages": self.montages, "AIPerceptionStimuliSource": self.sense}
        self.actor = types.SimpleNamespace(get_property=lambda name: self.fields[name], get_path_name=lambda: "owned",
            call_function=lambda *args: self.calls.append(args), call_mixin_original=lambda *args: self.calls.append(("original",)+args))
        def random(name, *args): self.random_calls.append((name,)+args); return self.index if name == "RandomIntegerInRange" else self.duration
        def library(name, *args):
            if name == "GetFrameCount": return self.frame
            self.assertEqual(name, "Delay"); actor, duration, info = args
            self.tasks.setdefault((id(actor), info.UUID), (self.now+duration, info)); return None
        classes = {"KismetMathLibrary": types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=random)),
            "KismetSystemLibrary": types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=library)),
            "GameplayStatics": types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=lambda *args: self.now)), "AISense_Sight": "native-sight"}
        engine = types.ModuleType("unreal_engine"); engine.find_class = classes.__getitem__; engine.get_mixin_profile = lambda actor: self.profile
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        actor_types = types.ModuleType("unreal_engine.classes"); actor_types.Actor = type("Actor", (), {})
        structs = types.ModuleType("unreal_engine.structs"); structs.LatentActionInfo = Info
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/death_started_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._death_started_model", source); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"uep_lyra_characters.ragdoll_mixin": self.parent, "unreal_engine": engine,
            "unreal_engine.classes": actor_types, "unreal_engine.structs": structs, native.__name__: native}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterDeathStartedPythonProfile, self.module.LyraCharacterDeathStartedBlueprintFallbackProfile
    def start(self): self.python.PythonDeathStarted(self.actor, self.actor)
    def tick(self, game_seconds):
        self.now += game_seconds; self.frame += 1
        for key, (due, info) in list(self.tasks.items()):
            if self.now >= due:
                del self.tasks[key]
                if not getattr(info.CallbackTarget, "invalid", False): self.module.resume(info.CallbackTarget, info.Linkage)
    def stats(self): return self.module.evidence(self.actor)
    def test_native_montage_then_sight_then_delay(self): self.start(); self.assertEqual([row["event"] for row in self.stats()["trace"]], ["montage", "sight", "delay"])
    def test_random_index_uses_original_inclusive_bounds(self): self.start(); self.assertEqual(self.random_calls[0], ("RandomIntegerInRange", 0, 1))
    def test_selected_native_montage_rate_and_start_section(self): self.start(); self.assertEqual(self.calls[0], ("PlayAnimMontage", self.montages[1], 1., "None"))
    def test_only_sight_is_unregistered(self): self.start(); self.assertEqual(self.calls[1], ("sense", "UnregisterFromSense", "native-sight"))
    def test_original_native_random_delay_bounds(self): self.start(); self.assertEqual(self.random_calls[1], ("RandomFloatInRange", .1, .6))
    def test_native_actor_callback_target_int32_zero_linkage(self):
        self.start(); _, info = next(iter(self.tasks.values())); self.assertIs(info.CallbackTarget, self.actor)
        self.assertEqual(info.Linkage, 0); self.assertEqual(info.ExecutionFunction, self.module.RESUME)
    def test_no_post_delay_calls_early(self): self.start(); self.tick(.1); self.assertEqual(self.stats()["resumes"], 0); self.assertEqual(len(self.calls), 2)
    def test_native_resume_forwards_virtual_functions_in_original_order(self): self.start(); self.tick(.4); self.assertEqual(self.calls[-3:], [("Ragdoll",), ("HideEquippedWeapons",), ("Death",)])
    def test_game_clock_pause_does_not_consume_delay(self): self.start(); self.tick(0.); self.assertEqual(len(self.tasks), 1); self.assertEqual(self.stats()["resumes"], 0)
    def test_repeated_prefix_preserves_native_delay_coalescing(self): self.start(); self.start(); self.assertEqual(len(self.tasks), 1); self.tick(.4); self.assertEqual(self.stats()["resumes"], 1); self.assertEqual(self.stats()["montage_calls"], 2)
    def test_destroyed_native_owner_never_resumes(self): self.start(); self.actor.invalid = True; self.tick(.4); self.assertEqual(self.stats()["resumes"], 0)
    def test_pending_python_delay_survives_profile_switch_without_replaying_prefix(self):
        self.start(); self.profile = "BlueprintFallback"; self.tick(.4); self.assertEqual(self.stats()["fallback_resumes"], 1); self.assertEqual(self.stats()["montage_calls"], 1)
    def test_fallback_calls_exact_original_bound_receiver(self):
        self.fallback.PythonDeathStarted(self.actor, self.actor); self.assertEqual(self.calls, [("original", self.module.BOUND_EVENT, self.actor)]); self.assertFalse(self.tasks)
    def test_empty_array_uses_null_native_montage_not_python_index_error(self):
        self.fields["Death Montages"] = []; self.index = 0; self.start(); self.assertEqual(self.calls[0], ("PlayAnimMontage", None, 1., "None")); self.assertEqual(self.random_calls[0], ("RandomIntegerInRange", 0, -1))
    def test_missing_native_sense_preserves_null_target_noop_effect(self): self.fields["AIPerceptionStimuliSource"] = None; self.start(); self.assertEqual(self.stats()["missing_sense_noops"], 1)
    def test_bad_native_linkage_rejected(self):
        with self.assertRaises(ValueError): self.module.resume(self.actor, 1)
        self.assertEqual(self.stats()["resumes"], 0)
    def test_resume_is_same_raw_handler_in_fallback(self): self.assertIs(self.fallback.__dict__["PythonAfterDeathDelay"], self.python.__dict__["PythonAfterDeathDelay"])
    def test_received_actor_payload_is_observation_only(self): self.python.PythonDeathStarted(self.actor, None); self.assertEqual(self.stats()["last_start"]["owning_actor"], None); self.assertEqual(len(self.tasks), 1)
    def test_existing_twenty_eight_methods_are_raw_aliases(self):
        for name, method in self.parent.LyraCharacterRagdollPythonProfile.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], method)
    def test_no_production_ticker_rooting_or_global_latent_cancellation(self):
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/death_started_mixin.py"
        code = source.read_text(encoding="utf-8")
        for token in ("add_ticker", "add_to_root", "CancelLatentActions"): self.assertNotIn(token, code)
