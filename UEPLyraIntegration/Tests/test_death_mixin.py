"""Camera/cue pins and native noncancelable cleanup models, not runtime proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object
from test_heal_ability_mixin import Scope


class DeathPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.factory_calls = [], []
        native, structs, runtime = types.ModuleType("unreal_engine"), types.ModuleType("unreal_engine.structs"), types.ModuleType("uep_runtime")
        runtime.SubscriptionScope = Scope; structs.GameplayTag = lambda **values: types.SimpleNamespace(**values)
        native.FVector = lambda *values: values
        self.params = object()
        def factory(name, *args):
            self.factory_calls.append((name, args))
            if name == "MakeGameplayCueParameters": return self.params
            return Object("task", lambda name, *args: self.calls.append((name, args)))
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: Object("factory", factory))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/death_mixin.py"
        spec = importlib.util.spec_from_file_location("death_policy_test", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs, "uep_runtime": runtime}): spec.loader.exec_module(self.module)
        self.props = {"Camera Mode": "original-camera", "bIsActive": True}
        self.ability = Object("ability", self.call); self.ability.Duration = 4.
        self.ability.get_path_name = lambda: "death-ability"
        self.ability.get_property = self.props.get
        self.ability.set_property = lambda key, value: self.props.__setitem__(key, value)
        self.module.LyraDeathPythonProfile.__init__(self.ability)
        self.event = types.SimpleNamespace(EventMagnitude=100., ContextHandle="native-context", EventTag="native-death-tag",
            InstigatorTags="source-tags", TargetTags="target-tags", Instigator="instigator", Target="target")

    def call(self, name, *args):
        self.calls.append((name, args))
        if name == "K2_EndAbility":
            self.props["bIsActive"] = False
            if not self.props.get(self.module.GUARD): self.module.LyraDeathPythonProfile.NativeEnded(self.ability, False)

    def test_native_cue_builder_preserves_all_original_event_pins(self):
        self.module.activate(self.ability, self.event)
        self.assertEqual(self.factory_calls[0], ("MakeGameplayCueParameters", (100., 100., "native-context",
            "native-death-tag", "native-death-tag", "source-tags", "target-tags", (0., 0., 0.), (0., 0., 0.),
            "instigator", None, "target", None, 1, 1, None, False)))

    def test_original_camera_cue_and_native_delay_order(self):
        self.module.activate(self.ability, self.event)
        self.assertEqual([name for name, _ in self.calls], ["SetCameraMode", "K2_ExecuteGameplayCueWithParams", "ReadyForActivation"])
        self.assertEqual(self.calls[0][1], ("original-camera",))
        self.assertEqual(self.calls[1][1][0].TagName, "GameplayCue.Character.Death")
        self.assertEqual(self.factory_calls[1], ("WaitDelay", (self.ability, 4.)))

    def test_native_wait_finish_ends_and_closes_owned_scope(self):
        self.module.activate(self.ability, self.event); scope = self.ability._uep_death_scope
        scope.callbacks["OnFinish"]()
        self.assertTrue(scope.closed); self.assertFalse(self.props["bIsActive"])
        self.assertEqual(self.module.snapshot()["waits_finished"], 1)
        self.assertEqual(self.module.snapshot()["native_ends"], 1)

    def test_teardown_ends_without_overriding_native_noncancelable_policy(self):
        self.module.activate(self.ability, self.event); scope = self.ability._uep_death_scope
        self.module.LyraDeathPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertTrue(scope.closed); self.assertFalse(self.props[self.module.GUARD])
        self.assertNotIn("K2_CancelAbility", [name for name, _ in self.calls])
        self.assertEqual(self.module.snapshot()["native_ends"], 0)

    def test_inactive_teardown_does_not_end_again(self):
        self.props["bIsActive"] = False
        self.module.LyraDeathPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertFalse(self.calls)
