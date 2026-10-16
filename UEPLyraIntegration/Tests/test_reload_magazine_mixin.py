"""Reload policy/native-call models, not actual montage or replication proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_heal_ability_mixin import Scope


class ReloadMagazinePolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.tasks, self.active, self.authority, self.blocks = [], [], True, True, 0
        native, structs, runtime, helpers = (types.ModuleType(name) for name in
            ("unreal_engine", "unreal_engine.structs", "uep_runtime", "uep_lyra_world.effect_pad_mixin"))
        structs.GameplayTag = lambda **values: types.SimpleNamespace(**values)
        structs.GameplayTagContainer = lambda: []
        runtime.SubscriptionScope = Scope; helpers.valid = lambda value: value is not None
        def factory(name, *args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "MakeGameplayTagContainerFromTag": return [args[0].TagName]
            if name in ("AddLooseGameplayTags", "RemoveLooseGameplayTags"):
                self.blocks += 1 if name.startswith("Add") else -1; return True
            task = types.SimpleNamespace(call_function=lambda name: self.calls.append((name, (), {})))
            self.tasks.append(task); return task
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=factory))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/reload_magazine_mixin.py"
        spec = importlib.util.spec_from_file_location("reload_magazine_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs,
            "uep_runtime": runtime, "uep_lyra_world.effect_pad_mixin": helpers}): spec.loader.exec_module(self.module)
        self.values = dict(zip((self.module.MAGAZINE, self.module.CAPACITY, self.module.SPARE), (0, 12, 30)))
        self.item = types.SimpleNamespace(call_function=self.item_call)
        self.props = {self.module.GUARD: False}
        self.ability = types.SimpleNamespace(DidBlockFiring=False, ReloadMontage="original-montage", Playrate=1.1,
            call_function=self.call, get_path_name=lambda: "native-reload", call_mixin_original=lambda *args: True,
            get_property=lambda key: self.active if key == "bIsActive" else self.props[key],
            set_property=lambda key, value: self.props.__setitem__(key, value))
        self.module.LyraReloadMagazinePythonProfile.__init__(self.ability)

    def item_call(self, name, tag, count=0):
        if name == "GetStatTagStackCount": return self.values[tag.TagName]
        self.values[tag.TagName] += count if name == "AddStatTagStack" else -count

    def call(self, name, *args):
        self.calls.append((name, args, {}))
        if name == "GetAssociatedItem": return self.item
        if name == "GetOwningActorFromActorInfo": return "native-owner"
        if name == "K2_HasAuthority": return self.authority
        if name == "ReloadAmmoIntoMagazine": self.module.reload_ammo(self.ability)
        if name in ("K2_EndAbility", "K2_EndAbilityLocally"):
            self.active = False
            if not self.props[self.module.GUARD]: self.module.LyraReloadMagazinePythonProfile.NativeEnded(self.ability, False)

    def test_can_activate_priority_and_named_output_opt_in(self):
        for magazine, spare, failure in ((12, 0, "MagazineFull"), (1, 0, "NoSpareAmmo"), (1, 2, None)):
            self.values[self.module.MAGAZINE], self.values[self.module.SPARE] = magazine, spare
            result = self.module.can_activate(self.ability)
            self.assertEqual(result, dict(ReturnValue=failure is None, RelevantTags=[] if failure is None else ["Ability.ActivateFail."+failure]))
        self.assertTrue(self.module.LyraReloadMagazinePythonProfile.K2_CanActivateAbility.uep_named_outputs)
        self.assertEqual(self.module.LyraReloadMagazinePythonProfile.K2_CanActivateAbility(self.ability, "actor-info", "native-handle"), result)

    def test_native_tasks_preserve_original_pins(self):
        self.module.activate(self.ability)
        factory = next(kwargs for name, args, kwargs in self.calls if name == "CreatePlayMontageAndWaitProxy")
        self.assertEqual((factory["MontageToPlay"], factory["Rate"], factory["bStopWhenAbilityEnds"]), ("original-montage", 1.1, False))
        wait = next(args for name, args, kwargs in self.calls if name == "WaitGameplayEvent")
        self.assertEqual((wait[1].TagName, wait[2:]), (self.module.RELOAD_DONE, (None, True, True)))
        self.assertEqual(len(self.tasks), 2)

    def test_native_authority_event_transfers_and_closes_owned_scope(self):
        self.module.activate(self.ability); scope = self.ability._uep_reload_magazine_scope
        scope.callbacks["EventReceived"](object())
        self.assertEqual(self.module.ammo(self.item), (12, 12, 18)); self.assertFalse(self.active)
        self.assertTrue(scope.closed); self.assertEqual(self.blocks, 0)
        self.assertEqual(self.module.snapshot()["authority_reloads"], 1)

    def test_client_event_never_mutates_ammo_or_ends_authority(self):
        self.authority = False; self.module.activate(self.ability)
        self.ability._uep_reload_magazine_scope.callbacks["EventReceived"](object())
        self.assertEqual(self.module.ammo(self.item), (0, 12, 30)); self.assertTrue(self.active)
        self.assertEqual(self.module.snapshot()["client_events"], 1)

    def test_partial_spare_transfer_preserves_total_and_public_method(self):
        self.values[self.module.MAGAZINE], self.values[self.module.SPARE] = 5, 3
        self.module.reload_ammo(self.ability)
        self.assertEqual(self.module.ammo(self.item), (8, 12, 0))
        self.module.LyraReloadMagazinePythonProfile.ReloadAmmoIntoMagazine(self.ability, "unused-original-state-pin")
        self.assertEqual(self.module.ammo(self.item), (8, 12, 0))

    def test_local_montage_completion_and_interruption_end_cleanup(self):
        self.module.activate(self.ability); self.ability._uep_reload_magazine_scope.callbacks["OnCompleted"]()
        self.assertTrue(any(name == "K2_EndAbilityLocally" for name, args, kwargs in self.calls))
        self.assertEqual(self.blocks, 0)
        self.active = True; self.module.activate(self.ability)
        self.ability._uep_reload_magazine_scope.callbacks["OnInterrupted"]()
        self.assertFalse(self.active); self.assertEqual(self.blocks, 0)

    def test_teardown_is_guarded_and_preserves_foreign_loose_tag(self):
        self.blocks = 1; self.module.activate(self.ability); scope = self.ability._uep_reload_magazine_scope
        self.module.teardown(self.ability); self.module.cleanup(self.ability)
        self.assertTrue(scope.closed); self.assertFalse(self.active); self.assertEqual(self.blocks, 1)
        self.assertFalse(self.props[self.module.GUARD]); self.assertEqual(self.module.snapshot()["active_count"], 0)
