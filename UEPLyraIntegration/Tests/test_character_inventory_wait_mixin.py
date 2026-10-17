"""Native-latent resume decisions; host queue models are not UE acceptance."""
import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_inventory_ready_mixin as ready_models


class CharacterInventoryWaitPolicyModels(unittest.TestCase):
    def setUp(self):
        setup = ready_models.CharacterInventoryReadyPolicyModels(); setup.setUp(); self.ready = setup.module
        self.tasks, self.frame, self.grants, self.originals = {}, 0, 0, []
        self.inventory, self.quickbar = object(), object()
        self.controller = types.SimpleNamespace(call_function=lambda name, cls: self.inventory if cls == "LyraInventoryManagerComponent" else self.quickbar)
        self.actor = types.SimpleNamespace(call_function=self.actor_call, call_mixin_original=lambda name: self.originals.append(name))
        engine = types.ModuleType("unreal_engine")
        engine.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=self.native)) if name == "KismetSystemLibrary" else name
        structs = types.ModuleType("unreal_engine.structs"); structs.LatentActionInfo = lambda **kwargs: types.SimpleNamespace(**kwargs)
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None and not getattr(value, "invalid", False)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/inventory_wait_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._inventory_wait_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"uep_lyra_characters.inventory_ready_mixin": self.ready, "unreal_engine": engine, structs.__name__: structs, native.__name__: native}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterInventoryWaitPythonProfile, self.module.LyraCharacterInventoryWaitBlueprintFallbackProfile

    def actor_call(self, name):
        if name == "GetController": return self.controller
        if name == "AddInitialInventory": self.grants += 1

    def native(self, name, *args):
        if name == "GetFrameCount": return self.frame
        self.assertEqual(name, "DelayUntilNextTick")
        actor, info = args; self.tasks.setdefault((id(actor), info.UUID), info)

    def tick(self):
        values, self.tasks = list(self.tasks.values()), {}; self.frame += 1
        for info in values:
            if not getattr(info.CallbackTarget, "invalid", False): self.module.resume(info.CallbackTarget, info.Linkage)

    def start(self): self.python.PythonExperienceReady(self.actor)
    def stats(self): return self.module.evidence(self.actor)

    def test_all_ready_grants_without_latent_action(self): self.start(); self.assertEqual(self.grants, 1); self.assertFalse(self.tasks)
    def test_missing_controller_queues_native_linkage_zero(self):
        self.controller = None; self.start(); info, = self.tasks.values()
        self.assertEqual(info.Linkage, 0); self.assertIs(info.CallbackTarget, self.actor); self.assertEqual(info.ExecutionFunction, self.module.RESUME)
    def test_missing_inventory_queues_stage_one(self):
        self.inventory = None; self.start(); self.assertEqual(next(iter(self.tasks.values())).Linkage, 1)
    def test_missing_quickbar_queues_stage_two(self):
        self.quickbar = None; self.start(); self.assertEqual(next(iter(self.tasks.values())).Linkage, 2)
    def test_repeated_same_checkpoint_uses_same_native_key(self):
        self.inventory = None; self.start(); self.start(); self.assertEqual(len(self.tasks), 1); self.assertEqual(self.stats()["stage_requests"], [0, 2, 0])
    def test_three_distinct_keys_stable_for_actor(self):
        self.controller = None; self.start(); ids = list(self.stats()["uuids"]); self.tick()
        self.assertEqual(ids, self.stats()["uuids"]); self.assertEqual(len(set(ids)), 3); self.assertTrue(all(0 < value < 2**31 for value in ids))
    def test_controller_becomes_ready_then_native_resume_grants(self):
        controller = self.controller; self.controller = None; self.start(); self.tick(); self.assertEqual(self.grants, 0)
        self.controller = controller; self.tick(); self.assertEqual(self.grants, 1); self.assertFalse(self.tasks)
    def test_inventory_becomes_ready_then_resume_advances(self):
        self.inventory = None; self.start(); self.tick(); self.inventory = object(); self.tick()
        self.assertEqual(self.grants, 1); self.assertEqual(self.stats()["stage_resumes"], [0, 2, 0])
    def test_quickbar_becomes_ready_then_resume_grants(self):
        self.quickbar = None; self.start(); self.tick(); self.quickbar = object(); self.tick(); self.assertEqual(self.grants, 1)
    def test_controller_wait_can_advance_to_inventory_wait(self):
        controller = self.controller; self.controller = None; self.inventory = None; self.start()
        self.controller = controller; self.tick(); self.assertEqual(next(iter(self.tasks.values())).Linkage, 1); self.assertEqual(self.grants, 0)
    def test_resumed_later_checkpoint_does_not_restart_prior_checkpoint(self):
        self.module.resume(self.actor, 2); self.assertEqual(self.grants, 1)
        self.inventory = None; self.module.resume(self.actor, 2); self.assertEqual(self.grants, 2)
    def test_native_backend_drops_destroyed_owner_without_python_roots(self):
        self.controller = None; self.start(); self.actor.invalid = True; self.tick()
        self.assertEqual(self.stats()["resumes"], 0); self.assertEqual(self.grants, 0)
    def test_reentrant_ready_and_preexisting_wait_both_preserved(self):
        controller = self.controller; self.controller = None; self.start(); self.controller = controller
        self.start(); self.tick(); self.assertEqual(self.grants, 2)
    def test_no_original_bp_wait_on_python_path(self):
        self.controller = None; self.start(); self.tick(); self.assertEqual(self.originals, [])
    def test_original_fallback_ready_remains_exact_alias(self):
        self.assertIs(self.fallback.__dict__["PythonExperienceReady"], self.ready.LyraCharacterInventoryReadyBlueprintFallbackProfile.__dict__["PythonExperienceReady"])
    def test_fallback_resume_interoperability_calls_original_entry(self):
        self.fallback.PythonInventoryWaitResume(self.actor, 1); self.assertEqual(self.originals, [self.ready.READY])
    def test_resume_signature_matches_native_int_linkage(self):
        for profile in (self.python, self.fallback):
            self.assertEqual(profile.PythonInventoryWaitResume.override, self.module.RESUME)
            self.assertEqual(list(inspect.signature(profile.PythonInventoryWaitResume).parameters), ["self", "Linkage"])
    def test_bad_linkage_rejected_before_grant(self):
        for value in (-1, 3):
            with self.assertRaises(ValueError): self.module.resume(self.actor, value)
        self.assertEqual(self.grants, 0)
    def test_twenty_accepted_other_python_methods_are_raw_aliases(self):
        for name, value in self.ready.LyraCharacterInventoryReadyPythonProfile.__dict__.items():
            if not name.startswith("__") and name != "PythonExperienceReady": self.assertIs(self.python.__dict__[name], value)
    def test_no_python_ticker_or_global_latent_cancellation(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/inventory_wait_mixin.py"
        source = file.read_text(encoding="utf-8"); self.assertNotIn("add_ticker", source); self.assertNotIn("CancelLatentActions", source); self.assertNotIn("add_to_root", source)
