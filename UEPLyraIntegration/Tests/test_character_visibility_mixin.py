"""Native queue policy models; actual InitState/latent delivery is separate."""
import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_possessed_mixin as possessed_models
from uep_lyra_characters.latent_keys import allocate


class CharacterVisibilityPolicyModels(unittest.TestCase):
    def setUp(self):
        setup = possessed_models.CharacterPossessedPolicyModels(); setup.setUp(); self.parent = setup.module
        self.tasks, self.frame, self.hidden, self.originals, self.setters = {}, 0, True, [], []
        self.actor = types.SimpleNamespace(get_path_name=lambda: "actor", get_property=lambda name: self.hidden,
            call_function=self.actor_call, call_mixin_original=lambda *args: self.originals.append(args))
        self.params = types.SimpleNamespace(OwningActor=self.actor, FeatureName="PawnExtension", FeatureState=types.SimpleNamespace(TagName="InitState.GameplayReady"),
            Implementer=types.SimpleNamespace(get_path_name=lambda: "component"))
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        engine = types.ModuleType("unreal_engine"); engine.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=self.native))
        structs = types.ModuleType("unreal_engine.structs"); structs.LatentActionInfo = lambda **kwargs: types.SimpleNamespace(**kwargs)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/visibility_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._visibility_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"uep_lyra_characters.possessed_mixin": self.parent, "unreal_engine": engine, structs.__name__: structs, native.__name__: native}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterVisibilityPythonProfile, self.module.LyraCharacterVisibilityBlueprintFallbackProfile

    def actor_call(self, name, hidden): self.setters.append((name, hidden)); self.hidden = hidden
    def native(self, name, *args):
        if name == "GetFrameCount": return self.frame
        self.assertEqual(name, "DelayUntilNextTick"); actor, info = args; self.tasks.setdefault((id(actor), info.UUID), info)
    def start(self): self.python.ShowPawnAgainNextFrame(self.actor, self.params)
    def tick(self):
        tasks, self.tasks = list(self.tasks.values()), {}; self.frame += 1
        for info in tasks:
            if not getattr(info.CallbackTarget, "invalid", False): self.module.resume(info.CallbackTarget, info.Linkage)
    def stats(self): return self.module.evidence(self.actor)
    def test_never_show_synchronously_in_callback(self): self.start(); self.assertTrue(self.hidden); self.assertFalse(self.setters)
    def test_native_named_int_linkage_target(self):
        self.start(); info, = self.tasks.values(); self.assertIs(info.CallbackTarget, self.actor); self.assertEqual((info.Linkage, info.ExecutionFunction), (0, self.module.RESUME))
    def test_native_resume_shows_once(self): self.start(); self.tick(); self.assertEqual(self.setters, [("SetActorHiddenInGame", False)]); self.assertFalse(self.stats()["pending"])
    def test_repeated_callback_coalesces_same_native_key(self): self.start(); self.start(); self.assertEqual(len(self.tasks), 1); self.tick(); self.assertEqual(self.stats()["delay_requests"], 2); self.assertEqual(self.stats()["resumes"], 1)
    def test_inventory_and_visibility_keys_are_disjoint_in_both_orders(self):
        self.start(); self.assertNotIn(self.stats()["uuid"], allocate(self.actor, "inventory-readiness", 3))
        other = types.SimpleNamespace(); keys = allocate(other, "inventory-readiness", 3); self.assertNotIn(allocate(other, "gameplay-ready-visibility", 1)[0], keys)
    def test_native_backend_drops_destroyed_owner(self): self.start(); self.actor.invalid = True; self.tick(); self.assertTrue(self.hidden); self.assertEqual(self.stats()["resumes"], 0)
    def test_fallback_uses_exact_original_struct_parameter(self): self.fallback.ShowPawnAgainNextFrame(self.actor, self.params); self.assertEqual(self.originals, [(self.module.SHOW, self.params)]); self.assertFalse(self.tasks)
    def test_payload_observed_not_used_as_extra_gate(self): self.params.OwningActor = self.params.Implementer = None; self.params.FeatureState.TagName = "Other"; self.start(); self.tick(); self.assertFalse(self.hidden)
    def test_python_never_falls_through_to_original(self): self.start(); self.tick(); self.assertFalse(self.originals)
    def test_pending_python_action_can_resume_in_fallback_profile(self): self.start(); self.fallback.PythonVisibilityResume(self.actor, 0); self.assertFalse(self.hidden); self.assertFalse(self.originals)
    def test_bad_linkage_rejected(self):
        with self.assertRaises(ValueError): self.module.resume(self.actor, 1)
        self.assertFalse(self.setters)
    def test_exact_native_parameter_names(self):
        for cls in (self.python, self.fallback):
            self.assertEqual(list(inspect.signature(cls.ShowPawnAgainNextFrame).parameters), ["self", "Params"])
            self.assertEqual(cls.PythonVisibilityResume.override, self.module.RESUME)
    def test_previous_twenty_three_methods_raw_aliases(self):
        for name, method in self.parent.LyraCharacterPossessedPythonProfile.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], method)
    def test_evidence_only_copies_payload_paths(self): self.start(); self.assertEqual(self.stats()["last_payload"], dict(actor="actor", feature="PawnExtension", state="InitState.GameplayReady", implementer="component"))
    def test_no_python_ticker_closure_root_or_global_cancel(self):
        source = inspect.getsource(self.module)
        for value in ("add_ticker", "add_to_root", "bind_event", "lambda", "CancelLatentActions"): self.assertNotIn(value, source)


class CharacterLatentKeyModels(unittest.TestCase):
    def test_keys_stable_and_return_is_a_copy(self):
        actor = types.SimpleNamespace(); keys = allocate(actor, "one", 3); again = list(keys); keys.clear(); self.assertEqual(allocate(actor, "one", 3), again)
    def test_sites_cannot_collide_even_when_random_repeats(self):
        actor = types.SimpleNamespace()
        with patch("uep_lyra_characters.latent_keys.uuid.uuid4", side_effect=[types.SimpleNamespace(int=value) for value in (1, 1, 2, 1, 3, 4)]):
            self.assertEqual(allocate(actor, "visibility", 1), [1]); self.assertEqual(allocate(actor, "inventory", 3), [2, 3, 4])
    def test_site_shape_cannot_change(self):
        actor = types.SimpleNamespace(); allocate(actor, "one", 1)
        with self.assertRaises(ValueError): allocate(actor, "one", 3)
    def test_keys_are_pod_positive_int32(self): self.assertTrue(all(type(value) is int and 0 < value < 2**31 for value in allocate(types.SimpleNamespace(), "site", 3)))
    def test_actor_namespaces_independent(self):
        first, second = types.SimpleNamespace(), types.SimpleNamespace(); allocate(first, "one", 1); self.assertFalse(hasattr(second, "_uep_character_latent_keys"))
