"""Factory ordering and named native binding; host models, not UE acceptance."""
import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterTeamListenerPolicyModels(unittest.TestCase):
    def setUp(self):
        parent = types.ModuleType("uep_lyra_characters.team_observer_mixin")
        names = ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot", "AddInitialInventory", "CreateOrUpdateOutlineIfNeeded", "OnTeamOrCosmeticsChanged", "UpdateCustomStencilFromTeamID", "K2_OnDeathFinished", "K2_OnReset", "PythonCharacterPartsChanged", "PythonHealthChanged", "PythonObservedTeamChanged")
        self.fallback_parent = type("Fallback", (), {name: lambda *args: None for name in names})
        class Descriptor:
            def __call__(self, *args): pass
            def __get__(self, instance, owner): return lambda *args: None
        values = {name: self.fallback_parent.__dict__[name] for name in names}
        values.update({name: Descriptor() for name in ("PythonQuickSlotZero", "PythonQuickSlotOne", "PythonQuickSlotTwo", "PythonQuickSlotBackward", "PythonQuickSlotForward")})
        self.parent = type("Python", (), values)
        parent.LyraCharacterTeamObserverPythonProfile, parent.LyraCharacterTeamObserverBlueprintFallbackProfile = self.parent, self.fallback_parent
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        self.calls = []; self.proxy = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("proxy", *args)))
        self.factory_result = self.proxy
        def factory(name, actor):
            self.calls.append(("factory", name, actor)); return self.factory_result
        engine = types.ModuleType("unreal_engine"); engine.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=factory))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/team_listener_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._team_listener_policy_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {parent.__name__: parent, native.__name__: native, "unreal_engine": engine}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterTeamListenerPythonProfile, self.module.LyraCharacterTeamListenerBlueprintFallbackProfile
        self.actor = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("actor", *args)), call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def test_factory_then_named_bind_then_activate(self):
        self.python.ListenForTeam(self.actor)
        self.assertEqual(self.calls, [("factory", "ObserveTeamColors", self.actor), ("actor", self.module.BIND, self.proxy), ("proxy", "Activate")])
    def test_every_repeated_call_creates_and_activates_not_deduplicated(self):
        self.python.ListenForTeam(self.actor); self.python.ListenForTeam(self.actor)
        self.assertEqual(len(self.calls), 6); self.assertEqual(self.module.evidence(self.actor)["factories"], 2)
    def test_no_invented_cancellation_on_repeated_calls(self):
        self.python.ListenForTeam(self.actor); self.python.ListenForTeam(self.actor)
        self.assertNotIn("Cancel", repr(self.calls))
    def test_binding_failure_must_not_activate_unbound_proxy(self):
        self.actor.call_function = lambda *args: (_ for _ in ()).throw(RuntimeError("bind failure"))
        with self.assertRaises(RuntimeError): self.python.ListenForTeam(self.actor)
        self.assertEqual(len(self.calls), 1)
    def test_null_native_factory_never_binds_or_activates(self):
        self.factory_result = None; self.python.ListenForTeam(self.actor)
        self.assertEqual(len(self.calls), 1); self.assertEqual(self.module.evidence(self.actor)["null_factories"], 1)
    def test_python_actor_attributes_only_store_pod_counters(self):
        self.python.ListenForTeam(self.actor)
        self.assertTrue(all(type(value) is int for value in self.module.evidence(self.actor).values()))
        self.assertNotIn(self.proxy, vars(self.actor).values())
    def test_all_eighteen_accepted_aliases_are_exact_original_objects(self):
        for name, value in self.parent.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], value)
    def test_fallback_preserves_thirteen_aliases(self):
        for name, value in self.fallback_parent.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.fallback.__dict__[name], value)
    def test_five_input_descriptors_stay_absent_from_fallback(self):
        self.assertFalse(any(name.startswith("PythonQuickSlot") for name in self.fallback.__dict__))
    def test_original_no_argument_listener_signature(self):
        for profile in (self.python, self.fallback): self.assertEqual(list(inspect.signature(profile.ListenForTeam).parameters), ["self"])
    def test_fallback_calls_exact_retained_original_once(self):
        self.fallback.ListenForTeam(self.actor); self.assertEqual(self.calls, [("original", "ListenForTeam")])
    def test_python_never_calls_original_listener(self):
        self.python.ListenForTeam(self.actor); self.assertFalse(any(value[0] == "original" for value in self.calls))
    def test_named_transport_contains_no_new_business_event_or_closure(self):
        file = Path(__file__).resolve().parents[1]/"Tools/generate_character_team_listener_transport.py"
        source = file.read_text(encoding="utf-8")
        self.assertIn('delegate.SelectedFunctionName = BOUND_EVENT', source); self.assertIn('len(graph.Nodes) != 4', source)
        self.assertNotIn('K2Node_CustomEvent', source); self.assertNotIn('lambda', source)
    def test_member_reference_uses_separate_struct_not_self_assignment(self):
        file = Path(__file__).resolve().parents[1]/"Tools/generate_character_team_listener_transport.py"
        source = file.read_text(encoding="utf-8")
        self.assertIn('call.DelegateReference = MemberReference(', source)
        self.assertNotIn('reference = call.DelegateReference', source)
