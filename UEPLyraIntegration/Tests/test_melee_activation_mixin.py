"""Melee activation primitives/order models; native gameplay is a separate gate."""
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

effects = types.ModuleType("uep_lyra_world.effect_pad_mixin"); effects.valid = lambda value: value is not None
with patch.dict(sys.modules, {"unreal_engine": types.ModuleType("unreal_engine"), "uep_lyra_world.effect_pad_mixin": effects}):
    policy = importlib.import_module("uep_lyra_abilities.melee_activation_mixin")


class Scope:
    def __init__(self): self.closed = False; self.bindings = []
    def bind_event(self, task, event, callback): self.bindings.append((task, event, callback)); task.events[event] = callback
    def close(self):
        if self.closed: return
        self.closed = True
        for task, event, callback in self.bindings: task.events.pop(event, None)


class Ability:
    def __init__(self):
        self.calls = []; self.active = True; self.authority = True; self.fields = {policy.GUARD: False}; self.weapons = [Weapon("first")]
        self.manager = types.SimpleNamespace(call_function=lambda name, cls: self.weapons)
    def get_path_name(self): return "model-melee"
    def get_property(self, name): return self.active if name == "bIsActive" else self.fields[name]
    def set_property(self, name, value): self.fields[name] = value
    def call_function(self, name, *args):
        self.calls.append((name, args))
        if name == "K2_CommitAbility": return False
        if name == "GetLyraCharacterFromActorInfo": return self
        if name == "GetComponentByClass": return self.manager
        if name == "K2_HasAuthority": return self.authority
        if name == "K2_EndAbility":
            if not self.fields[policy.GUARD]: policy.LyraMeleeActivationPythonProfile.NativeEnded(self, False)
            self.active = False
    def call_mixin_original(self, name): self.calls.append(("original", (name,)))


class Weapon:
    def __init__(self, value, cast=True): self.value, self.cast = value, cast
    def is_a(self, cls): return self.cast
    def get_property(self, name): assert name == "MeleeAttackMontage"; return self.value


class MeleeActivationPolicyModels(unittest.TestCase):
    def setUp(self):
        self.ability = Ability(); self.kwargs = None
        self.task = types.SimpleNamespace(events={}, call_function=lambda name: self.ability.calls.append(("task-"+name, ())))
        def factory(name, **kwargs): self.kwargs = kwargs; return self.task
        self.patches = [patch.object(policy, "SubscriptionScope", Scope), patch.object(policy, "valid", lambda value: value is not None),
            patch.object(policy, "ue", types.SimpleNamespace(find_class=lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=factory)) if name == "AbilityTask_PlayMontageAndWait" else name,
                load_class=lambda name: name))]
        for item in self.patches: item.start(); self.addCleanup(item.stop)
        policy._active.clear(); policy._instances.clear()
        for name in policy._stats: policy._stats[name] = [] if name == "errors" else 0
        policy.LyraMeleeActivationPythonProfile.__init__(self.ability)
    def activate(self): policy.activate(self.ability)
    def names(self): return [name for name, _ in self.ability.calls]
    def test_original_commit_return_is_ignored(self): self.activate(); self.assertIsNotNone(self.kwargs); self.assertEqual(self.names()[0], "K2_CommitAbility")
    def test_first_equipment_not_a_new_filter(self): self.ability.weapons.append(Weapon("second")); self.activate(); self.assertEqual(self.kwargs["MontageToPlay"], "first")
    def test_failed_first_cast_does_not_search_next_weapon(self):
        self.ability.weapons = [Weapon("bad", False), Weapon("good")]; self.activate(); self.assertIsNone(self.kwargs); self.assertFalse(self.ability.active)
    def test_empty_equipment_ends_without_task(self): self.ability.weapons = []; self.activate(); self.assertIsNone(self.kwargs); self.assertFalse(self.ability.active)
    def test_missing_manager_uses_original_cast_failure_outcome(self): self.ability.manager = None; self.activate(); self.assertFalse(self.ability.active)
    def test_montage_parameters_match_original(self):
        self.activate(); self.assertEqual((self.kwargs["Rate"], self.kwargs["StartSection"], self.kwargs["bStopWhenAbilityEnds"], self.kwargs["AnimRootMotionTranslationScale"], self.kwargs["StartTimeSeconds"], self.kwargs["bAllowInterruptAfterBlendOut"]), (1., "None", True, 1., 0., False))
    def test_all_four_original_end_events_bound(self): self.activate(); self.assertEqual(set(self.task.events), {"OnCompleted", "OnBlendOut", "OnInterrupted", "OnCancelled"})
    def test_authority_uses_native_trace_entry_after_montage_ready(self): self.activate(); self.assertLess(self.names().index("task-ReadyForActivation"), self.names().index(policy.TRACE))
    def test_client_does_not_run_authority_trace(self): self.ability.authority = False; self.activate(); self.assertNotIn(policy.TRACE, self.names())
    def test_blendout_ends_and_closes_scope(self): self.activate(); self.task.events["OnBlendOut"](); self.assertFalse(self.ability.active); self.assertEqual(policy.snapshot()["active_count"], 0)
    def test_interruption_ends_and_closes_scope(self): self.activate(); self.task.events["OnInterrupted"](); self.assertEqual(policy.snapshot()["scopes_created"], policy.snapshot()["scopes_closed"])
    def test_teardown_guards_native_end_and_disarms_callbacks(self):
        self.activate(); policy.teardown(self.ability); self.assertFalse(self.ability.fields[policy.GUARD]); self.assertEqual(self.task.events, {}); self.assertEqual(policy.snapshot()["native_ends"], 0)
    def test_fallback_only_calls_preserved_original_event(self): policy.LyraMeleeActivationBlueprintFallbackProfile.Activate(self.ability); self.assertEqual(self.ability.calls, [("original", ("K2_ActivateAbility",))])
    def test_helper_named_metadata_is_explicitly_forwarded(self):
        for cls in (policy.LyraMeleeActivationPythonProfile, policy.LyraMeleeActivationBlueprintFallbackProfile):
            self.assertIs(cls.SelectHitMontage.uep_named_outputs, True); self.assertEqual(cls.SelectHitMontage.override, "Slelect Hit Montage")
            self.assertEqual(cls.Activate.override, "K2_ActivateAbility"); self.assertEqual(cls.NativeEnded.override, policy.ENDED)
    def test_native_end_generation_requires_real_override_owner(self):
        source = (Path(__file__).parents[1]/"Tools/generate_melee_activation_assets.py").read_text(encoding="utf-8")
        self.assertIn('end.set_property("bOverrideFunction", True)', source); self.assertIn('end_signature["owner"] != original_class', source)
        self.assertIn('connect(trace, "then", capsule, "execute")', source)
        self.assertNotIn("break_link_to", source)
