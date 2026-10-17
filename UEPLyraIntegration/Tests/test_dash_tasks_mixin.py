"""Native task/delegate stand-ins test choices/order, not gameplay acceptance."""
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

structs = types.ModuleType("unreal_engine.structs")
for name in ("GameplayTag", "GameplayTagContainer", "GameplayEffectContextHandle", "LyraInteractionDurationMessage"):
    setattr(structs, name, lambda **values: types.SimpleNamespace(**values))
enums = types.ModuleType("unreal_engine.enums"); enums.ERootMotionFinishVelocityMode = types.SimpleNamespace(ClampVelocity=2)
effects = types.ModuleType("uep_lyra_world.effect_pad_mixin"); effects.valid = lambda value: value is not None
with patch.dict(sys.modules, {"unreal_engine": types.ModuleType("unreal_engine"), "unreal_engine.structs": structs,
        "unreal_engine.enums": enums, "uep_lyra_world.effect_pad_mixin": effects}):
    policy = importlib.import_module("uep_lyra_abilities.dash_tasks_mixin")


class V:
    def __init__(self, x=0., y=0., z=0.): self.x, self.y, self.z = x, y, z


class Task:
    def __init__(self, name, order): self.name, self.order, self.events = name, order, {}
    def call_function(self, name): self.order.append((self.name, name))
    def emit(self, name):
        for value in list(self.events.get(name, [])): value()


class Scope:
    def __init__(self): self.closed = False; self.bindings = []
    def bind_event(self, source, event, callback):
        if self.closed: raise RuntimeError("closed scope")
        source.events.setdefault(event, []).append(callback); self.bindings.append((source, event, callback))
    def close(self):
        if self.closed: return
        self.closed = True
        for source, event, callback in self.bindings: source.events[event].remove(callback)
        self.bindings = []


class Ability:
    def __init__(self, order):
        self.order = order; self.active = True; self.authority = True
        self.fields = dict(Direction=V(1., 0., 0.), Montage=types.SimpleNamespace(get_path_name=lambda: "native-montage"),
            Strength=1850., RootMotionDuration=.25, AbilityDuration=.55)
    def get_path_name(self): return "actual-model-ability"
    def get_property(self, name): return self.active if name == "bIsActive" else self.fields[name]
    def set_property(self, name, value): self.order.append(("store", name)); self.fields[name] = value
    def call_function(self, name, *args):
        self.order.append((name, args))
        if name == "K2_HasAuthority": return self.authority
        if name == "GetLyraCharacterFromActorInfo": return "native-pawn"
        if name == "GetCooldownTimeRemaining": return 1.5
        if name == "K2_CommitAbility": return False  # Server intentionally ignores it.
        if name == "K2_EndAbility":
            if not self.fields.get(policy.GUARD): policy.LyraDashTasksPythonProfile.NativeEnded(self, False)
            self.active = False
    def call_mixin_original(self, name, *args): self.order.append(("original", (name,)+args))


class DashTaskPolicyModels(unittest.TestCase):
    def setUp(self):
        self.order = []; self.ability = Ability(self.order); self.tasks = {}; self.arguments = {}; self.invalid_root = False
        policy._active.clear(); policy._instances.clear()
        for key in policy._stats: policy._stats[key] = [] if key == "errors" else 0
        self.patches = [patch.object(policy, "SubscriptionScope", Scope), patch.object(policy, "valid", lambda value: value is not None),
            patch.object(policy, "library", lambda cls: types.SimpleNamespace(call_function=lambda name, *args, **kwargs: self.native(cls, name, args, kwargs))),
            patch.object(policy, "ue", types.SimpleNamespace(FVector=V, find_class=lambda name: name,
                load_class=lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=lambda method, *args: self.order.append((method, args))))))]
        for item in self.patches: item.start(); self.addCleanup(item.stop)
        policy.LyraDashTasksPythonProfile.__init__(self.ability)
    def native(self, cls, name, args, kwargs):
        self.order.append((name, kwargs)); self.arguments[name] = kwargs
        if name in ("CreatePlayMontageAndWaitProxy", "ApplyRootMotionConstantForce"):
            if self.invalid_root and name == "ApplyRootMotionConstantForce": return None
            self.tasks[name] = Task(name, self.order); return self.tasks[name]
        if name == "MakeGameplayCueParameters": return "native-cue-parameters"
        if name == "GetGameInstanceSubsystem": return "native-router"
        raise AssertionError(name)
    def start(self): policy.start(self.ability)
    def test_original_two_native_tasks_created(self): self.start(); self.assertEqual(len(self.tasks), 2)
    def test_montage_does_not_stop_when_ability_ends(self): self.start(); self.assertIs(self.arguments["CreatePlayMontageAndWaitProxy"]["bStopWhenAbilityEnds"], False)
    def test_original_montage_parameters(self):
        self.start(); data = self.arguments["CreatePlayMontageAndWaitProxy"]
        self.assertEqual((data["Rate"], data["StartSection"], data["AnimRootMotionTranslationScale"], data["StartTimeSeconds"], data["bAllowInterruptAfterBlendOut"]), (1., "None", 1., 0., False))
    def test_original_root_additive_and_finish_velocity(self):
        self.start(); data = self.arguments["ApplyRootMotionConstantForce"]
        self.assertEqual((data["Strength"], data["Duration"], data["bIsAdditive"], data["VelocityOnFinishMode"], data["ClampVelocityOnFinish"], data["bEnableGravity"]), (1850., .25, True, 2, 1000., False))
    def test_raw_direction_not_normalized_in_script(self): self.start(); self.assertIs(self.arguments["ApplyRootMotionConstantForce"]["WorldDirection"], self.ability.fields["Direction"])
    def test_only_original_montage_interruption_events_bound(self):
        self.start(); self.assertEqual(set(self.tasks["CreatePlayMontageAndWaitProxy"].events), {"OnInterrupted", "OnCancelled"})
    def test_root_finish_starts_original_native_delay(self):
        self.start(); self.tasks["ApplyRootMotionConstantForce"].emit("OnFinish")
        self.assertAlmostEqual(next(args[0] for name, args in self.order if name == policy.DELAY), .3)
    def test_nonpositive_delay_is_not_clamped_or_replaced(self):
        self.ability.fields["AbilityDuration"] = .1; policy.root_finished(self.ability)
        self.assertAlmostEqual(self.order[-1][1][0], -.15)
    def test_client_does_not_execute_authority_cue(self): self.ability.authority = False; self.start(); self.assertNotIn("MakeGameplayCueParameters", self.arguments)
    def test_cue_uses_native_make_full_defaults(self):
        self.start(); data = self.arguments["MakeGameplayCueParameters"]
        self.assertEqual((data["NormalizedMagnitude"], data["RawMagnitude"], data["GameplayEffectLevel"], data["AbilityLevel"], data["bReplicateLocationWhenUsingMinimalRepProxy"]), (.25, 1850., 1, 1, False))
        self.assertIs(data["Normal"], self.ability.fields["Direction"])
    def test_original_sequence_root_then_cue_then_ui(self):
        self.start(); names = [name for name, _ in self.order]
        self.assertLess(names.index("ApplyRootMotionConstantForce"), names.index("K2_ExecuteGameplayCueWithParams")); self.assertLess(names.index("K2_ExecuteGameplayCueWithParams"), names.index("BroadcastDuration"))
    def test_ui_uses_actual_native_cooldown_and_pawn(self):
        self.start(); args = next(args for name, args in self.order if name == "BroadcastDuration")
        self.assertEqual((args[1].TagName, args[2].Instigator, args[2].Duration), ("Ability.Dash.Duration.Message", "native-pawn", 1.5))
    def test_end_closes_scope_and_disarms_native_callbacks(self):
        self.start(); self.ability.call_function("K2_EndAbility"); self.tasks["ApplyRootMotionConstantForce"].emit("OnFinish")
        self.assertEqual(policy.snapshot()["active_count"], 0); self.assertEqual(policy.snapshot()["scopes_created"], policy.snapshot()["scopes_closed"])
        self.assertEqual(policy.snapshot()["native_delays_started"], 0)
    def test_montage_interrupt_ends_ability(self): self.start(); self.tasks["CreatePlayMontageAndWaitProxy"].emit("OnInterrupted"); self.assertFalse(self.ability.active)
    def test_montage_cancel_ends_ability(self): self.start(); self.tasks["CreatePlayMontageAndWaitProxy"].emit("OnCancelled"); self.assertFalse(self.ability.active)
    def test_after_delay_skips_original_end(self): self.start(); self.assertIs(policy.LyraDashTasksPythonProfile.AfterNativeDelay(self.ability), False); self.assertFalse(self.ability.active)
    def test_teardown_closes_before_native_end(self): self.start(); policy.teardown(self.ability); self.assertFalse(self.ability.active); self.assertEqual(policy.snapshot()["active_count"], 0)
    def test_task_failure_releases_owned_scope(self):
        self.invalid_root = True
        with self.assertRaises(RuntimeError): self.start()
        self.assertEqual(policy.snapshot()["scopes_created"], policy.snapshot()["scopes_closed"]); self.assertFalse(self.ability.active)
    def test_remote_native_commit_return_is_deliberately_ignored(self):
        result = policy.LyraDashTasksPythonProfile.StoreRemoteInput(self.ability, V(0., 1., 0.), self.ability.fields["Montage"])
        self.assertIs(result, False); names = [name for name, _ in self.order]
        self.assertLess(names.index("K2_CommitAbility"), names.index(policy.TASKS)); self.assertNotIn("K2_CancelAbility", names)
    def test_fallback_calls_actual_original_native_task_entry(self):
        policy.LyraDashTasksBlueprintFallbackProfile.StartNativeTasks(self.ability); self.assertEqual(self.order, [("original", (policy.TASKS,))])
    def test_fallback_delay_continuation_keeps_original_end(self): self.assertIs(policy.LyraDashTasksBlueprintFallbackProfile.AfterNativeDelay(self.ability), True)
    def test_seven_explicit_profile_methods(self):
        for cls in (policy.LyraDashTasksPythonProfile, policy.LyraDashTasksBlueprintFallbackProfile):
            functions = [value for name, value in cls.__dict__.items() if not name.startswith("__") and callable(value)]
            self.assertEqual(len(functions), 7); self.assertEqual(cls.NativeEnded.override, policy.ENDED)
    def test_transport_does_not_clone_business_or_replace_native_delay(self):
        source = (Path(__file__).parents[1]/"Tools/generate_dash_tasks_assets.py").read_text(encoding="utf-8")
        self.assertIn("task_transport_nodes=15", source); self.assertIn("original_native_delay_reused=True", source)
        self.assertIn('remote_branch.node_find_pin("else").break_link_to(old_remote)', source)
        self.assertNotIn("graph_remove_node", source)
    def test_teardown_native_end_is_guarded_and_does_not_reenter_python(self):
        self.start(); policy.teardown(self.ability)
        self.assertEqual(policy.snapshot()["native_ends"], 0); self.assertIs(self.ability.fields[policy.GUARD], False)
    def test_generated_end_is_an_actual_override_not_an_unbound_event(self):
        source = (Path(__file__).parents[1]/"Tools/generate_dash_tasks_assets.py").read_text(encoding="utf-8")
        self.assertIn('end_event.set_property("bOverrideFunction", True)', source)
        self.assertIn('end_signature["owner"] != original_class', source)
