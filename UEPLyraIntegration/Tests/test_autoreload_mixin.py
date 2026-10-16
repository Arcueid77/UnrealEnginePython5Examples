"""AutoReload decision/scope native-call models, not native GAS proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_heal_ability_mixin import Scope


class AutoReloadPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.tasks, self.ammo, self.active, self.tagged, self.idle = [], [], [0, 12], True, False, 3.
        native, structs, runtime, helpers = (types.ModuleType(name) for name in
            ("unreal_engine", "unreal_engine.structs", "uep_runtime", "uep_lyra_world.effect_pad_mixin"))
        structs.GameplayTag = lambda **values: types.SimpleNamespace(**values)
        structs.GameplayEventData = lambda: "native-empty-payload"
        runtime.SubscriptionScope = Scope; helpers.valid = lambda value: value is not None
        def factory(name, *args):
            self.calls.append((name, args))
            if name == "DoesTagAssetInterfaceHaveTag": return self.tagged
            task = types.SimpleNamespace(call_function=lambda name: self.calls.append((name, ())))
            self.tasks.append(task); return task
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=factory)) if name != "LyraWeaponInstance" else "native-weapon-class"
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/autoreload_mixin.py"
        spec = importlib.util.spec_from_file_location("autoreload_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs, "uep_runtime": runtime,
                                     "uep_lyra_world.effect_pad_mixin": helpers}): spec.loader.exec_module(self.module)
        self.item = types.SimpleNamespace(call_function=lambda name, tag: self.ammo[0 if tag.TagName == self.module.MAGAZINE else 1])
        self.equipment = types.SimpleNamespace(is_a=lambda cls: cls == "native-weapon-class", call_function=lambda name: self.idle)
        self.avatar = object(); self.props = {self.module.GUARD: False}
        self.ability = types.SimpleNamespace(PollInterval=.2, TimeSinceActivityToReload=2., call_function=self.call,
            get_path_name=lambda: "native-auto-reload", get_property=lambda key: self.active if key == "bIsActive" else self.props.get(key),
            set_property=lambda key, value: self.props.__setitem__(key, value))
        self.module.LyraAutoReloadPythonProfile.__init__(self.ability)

    def call(self, name, *args):
        self.calls.append((name, args))
        if name == "GetAssociatedItem": return self.item
        if name == "GetAssociatedEquipment": return self.equipment
        if name == "GetAvatarActorFromActorInfo": return self.avatar
        if name == "CheckAmmoState": return self.module.check_ammo(self.ability)
        if name == "PeriodicCheck": self.module.periodic(self.ability)
        if name == "K2_CancelAbility":
            self.active = False
            if not self.props[self.module.GUARD]: self.module.LyraAutoReloadPythonProfile.NativeEnded(self.ability, True)

    def test_ammo_truth_table_and_invalid_item(self):
        for values, expected in (([0, 12], True), ([1, 12], False), ([0, 0], False), ([1, 0], False)):
            self.ammo = values; self.assertEqual(self.module.check_ammo(self.ability), expected)
        self.item = None; self.assertFalse(self.module.check_ammo(self.ability))

    def test_native_wait_closes_before_next_poll_and_sends_original_event(self):
        self.module.periodic(self.ability); previous = self.ability._uep_autoreload_scope
        previous.callbacks["OnFinish"]()
        self.assertTrue(previous.closed)
        events = [args for name, args in self.calls if name == "SendGameplayEvent"]
        self.assertEqual(events[0][0].TagName, "InputTag.Weapon.Reload")
        self.assertEqual(events[0][1], "native-empty-payload")
        self.assertEqual(self.module.snapshot()["scopes_created"], 2)
        self.assertEqual(self.module.snapshot()["scopes_closed"], 1)

    def test_recent_interaction_and_existing_reload_suppress_request(self):
        for idle, tagged in ((.1, False), (3., True)):
            self.idle, self.tagged = idle, tagged
            self.module.periodic(self.ability); self.ability._uep_autoreload_scope.callbacks["OnFinish"]()
        self.assertFalse(any(name == "SendGameplayEvent" for name, args in self.calls))

    def test_missing_weapon_skips_request(self):
        self.equipment = None
        self.module.periodic(self.ability); self.ability._uep_autoreload_scope.callbacks["OnFinish"]()
        self.assertFalse(any(name == "SendGameplayEvent" for name, args in self.calls))

    def test_long_native_poll_chain_does_not_accumulate_scopes(self):
        self.ammo = [12, 12]; self.module.periodic(self.ability)
        for _ in range(100): self.ability._uep_autoreload_scope.callbacks["OnFinish"]()
        state = self.module.snapshot()
        self.assertEqual((state["scopes_created"], state["scopes_closed"], state["active_count"]), (101, 100, 1))
        self.module.LyraAutoReloadPythonProfile.NativeEnded(self.ability, False)
        self.assertEqual(self.module.snapshot()["scopes_closed"], 101)
        self.assertEqual(self.module.snapshot()["active_count"], 0)

    def test_profile_teardown_uses_native_cancel_without_busy_end_route(self):
        self.module.periodic(self.ability); scope = self.ability._uep_autoreload_scope
        self.module.LyraAutoReloadPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertTrue(scope.closed); self.assertFalse(self.active)
        self.assertFalse(self.props[self.module.GUARD]); self.assertEqual(self.module.snapshot()["native_ends"], 0)

    def test_inactive_periodic_call_creates_no_orphan_task(self):
        self.active = False; self.module.periodic(self.ability)
        self.assertEqual(self.tasks, [])

    def test_instance_counters_do_not_mix_other_weapon_abilities(self):
        self.module.periodic(self.ability)
        other = types.SimpleNamespace(get_path_name=lambda: "other-native-auto-reload")
        self.module.note(other, "polls")
        self.assertEqual(self.module.instance_snapshot(self.ability)["polls"], 0)
        self.assertEqual(self.module.instance_snapshot(other)["polls"], 1)
