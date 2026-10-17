"""Original authority/cast/self/AI guards and exact native sense arguments."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterHealthChangedPolicyModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.authority, self.controller = [], True, object()
        self.ai = types.SimpleNamespace(get_path_name=lambda: "ai-controller")
        self.location = types.SimpleNamespace(x=17., y=-23., z=61.)
        self.source_pawn = types.SimpleNamespace(call_function=lambda name: self.location, get_path_name=lambda: "source-pawn")
        self.instigator = types.SimpleNamespace(is_a=lambda cls: cls == "PlayerState", call_function=lambda name: self.source_pawn)
        engine = types.ModuleType("unreal_engine"); engine.FVector = lambda x, y, z: types.SimpleNamespace(x=x, y=y, z=z)
        def find(name):
            if name == "PlayerState": return name
            return types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=lambda *args: self.native(name, *args)))
        engine.find_class = find
        parent = types.ModuleType("uep_lyra_characters.parts_changed_mixin")
        prior_names = ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot", "AddInitialInventory",
            "CreateOrUpdateOutlineIfNeeded", "OnTeamOrCosmeticsChanged", "UpdateCustomStencilFromTeamID", "K2_OnDeathFinished", "K2_OnReset", "PythonCharacterPartsChanged")
        self.parent = type("Prior", (), {name: lambda *args: None for name in prior_names})
        parent.LyraCharacterPartsChangedPythonProfile = parent.LyraCharacterPartsChangedBlueprintFallbackProfile = self.parent
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/health_changed_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._health_policy_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": engine, parent.__name__: parent, native.__name__: native}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterHealthChangedPythonProfile, self.module.LyraCharacterHealthChangedBlueprintFallbackProfile
        self.actor = types.SimpleNamespace(call_function=self.actor_call, call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def native(self, cls, *args):
        self.calls.append((cls, *args))
        if cls == "AIBlueprintHelperLibrary": return self.ai

    def actor_call(self, name):
        self.calls.append(("actor", name)); return self.authority if name == "HasAuthority" else self.controller

    def invoke(self, old=100., new=95.): self.python.PythonHealthChanged(self.actor, object(), old, new, self.instigator)

    def test_exact_original_receiver_and_four_parameter_shape(self):
        import inspect
        for profile in (self.python, self.fallback):
            self.assertEqual(profile.PythonHealthChanged.override, self.module.BOUND_EVENT)
            self.assertEqual(list(inspect.signature(profile.PythonHealthChanged).parameters), ["self", "HealthComponent", "OldValue", "NewValue", "Instigator"])

    def test_authority_guard_precedes_cast_controller_and_native_report(self):
        self.authority = False; self.instigator = object(); self.invoke()
        self.assertEqual(self.calls, [("actor", "HasAuthority")]); self.assertEqual(self.module.evidence(self.actor)["authority_noops"], 1)

    def test_none_instigator_preserves_failed_cast_noop(self):
        self.instigator = None; self.invoke(); self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.module.evidence(self.actor)["instigator_noops"], 1)

    def test_non_playerstate_preserves_failed_cast_noop(self):
        self.instigator.is_a = lambda cls: False; self.invoke(); self.assertEqual(len(self.calls), 1)

    def test_instigating_pawn_equal_self_does_not_query_ai(self):
        self.source_pawn = self.actor; self.invoke(); self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.module.evidence(self.actor)["self_noops"], 1)

    def test_original_get_controller_then_native_get_ai_controller(self):
        self.invoke(); self.assertEqual(self.calls[:3], [("actor", "HasAuthority"), ("actor", "GetController"), ("AIBlueprintHelperLibrary", "GetAIController", self.controller)])

    def test_player_controller_is_valid_but_native_ai_cast_fails(self):
        self.ai = None; self.invoke(); self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.module.evidence(self.actor)["controller_noops"], 1)

    def test_exact_world_damaged_controller_instigating_pawn_and_location(self):
        self.invoke(); call = self.calls[-1]
        self.assertEqual(call[:7], ("AISense_Damage", "ReportDamageEvent", self.actor, self.ai, self.source_pawn, 5., self.location))
        self.assertEqual(vars(call[7]), dict(x=0., y=0., z=0.)); self.assertEqual(len(call), 8)

    def test_health_component_payload_remains_unused(self):
        class Opaque:
            def __getattribute__(self, name): raise AssertionError("original receiver does not read component payload")
        self.python.PythonHealthChanged(self.actor, Opaque(), 100., 95., self.instigator)
        self.assertEqual(self.module.evidence(self.actor)["damage_reports"], 1)

    def test_healing_keeps_negative_raw_damage_instead_of_new_guard_or_clamp(self):
        self.invoke(95., 98.); self.assertEqual(self.calls[-1][5], -3.)

    def test_equal_health_keeps_original_zero_damage_report(self):
        self.invoke(95., 95.); self.assertEqual(self.calls[-1][5], 0.)

    def test_no_pawn_keeps_default_vector_and_null_native_source_without_warning(self):
        self.source_pawn = None; self.invoke(); self.assertIsNone(self.calls[-1][4])
        self.assertEqual(vars(self.calls[-1][6]), dict(x=0., y=0., z=0.))

    def test_fallback_only_calls_original_with_exact_four_arguments(self):
        component = object(); self.fallback.PythonHealthChanged(self.actor, component, 10., 4., self.instigator)
        self.assertEqual(self.calls, [("original", self.module.BOUND_EVENT, component, 10., 4., self.instigator)])

    def test_eleven_prior_methods_are_explicit_aliases(self):
        for name, value in self.parent.__dict__.items():
            if not name.startswith("__"):
                self.assertIs(self.python.__dict__[name], value); self.assertIs(self.fallback.__dict__[name], value)

    def test_evidence_is_per_actor_pod_not_actor_or_component_roots(self):
        self.invoke(); self.assertEqual(self.module.evidence(self.actor)["last_report"], dict(amount=5., controller="ai-controller", instigator="source-pawn", location=[17., -23., 61.], hit_location=[0., 0., 0.]))
        self.assertEqual(self.module.evidence(types.SimpleNamespace())["python_calls"], 0)

    def test_native_failure_is_not_counted_as_completed_damage_report(self):
        def fail(*args): raise RuntimeError("native sense refused")
        self.module.ue.find_class = lambda name: "PlayerState" if name == "PlayerState" else types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=(fail if name == "AISense_Damage" else lambda *args: self.ai)))
        with self.assertRaisesRegex(RuntimeError, "native sense refused"): self.invoke()
        self.assertEqual(self.module.evidence(self.actor)["damage_reports"], 0)
