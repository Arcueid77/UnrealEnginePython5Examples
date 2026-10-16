"""Helper models only; native death, timer and restart need runtime reports."""
import importlib.util
import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class AutoRespawnHelperModels(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.asc = types.SimpleNamespace(call_function=self.asc_call)
        self.avatar, self.owner = object(), object()
        self.health = types.SimpleNamespace(call_function=lambda name: self.dead)
        self.dead, self.handles, self.resolved = False, ["death-handle"], {}
        self.ended = []
        self.resolved["death-handle"] = (types.SimpleNamespace(call_function=lambda name: self.ended.append(name)), True)
        native, structs, helper = (types.ModuleType(name) for name in
            ("unreal_engine", "unreal_engine.structs", "uep_lyra_world.effect_pad_mixin"))
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=lambda method, *a: self.library(name, method, a)))
        structs.GameplayTag = structs.GameplayTagContainer = types.SimpleNamespace
        helper.valid = lambda value: value is not None
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_helpers_mixin.py"
        spec = importlib.util.spec_from_file_location("auto_respawn_helper_model", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs,
                "uep_lyra_world.effect_pad_mixin": helper}): spec.loader.exec_module(self.module)
        self.ability = types.SimpleNamespace(call_function=self.call, call_mixin_original=self.original)
        self.profile = self.module.LyraAutoRespawnHelpersPythonProfile

    def call(self, name):
        self.calls.append((name, (), {}))
        return self.asc if name == "GetLyraAbilitySystemComponentFromActorInfo" else self.avatar

    def asc_call(self, name, *a, **kw):
        self.calls.append((name, a, kw))
        return self.owner if name == "GetOwner" else (list(self.handles),)

    def library(self, cls, method, args):
        self.calls.append((cls+"."+method, args, {}))
        return self.health if cls == "LyraHealthComponent" else self.resolved[args[1]]

    def original(self, *args):
        self.calls.append(("original", args, {}))
        return (False,) if args[0] == "Is Avatar Dead or Dying" else "original-result"

    def test_owner_is_actual_asc_owner(self):
        self.assertIs(self.profile.GetOwningPlayerState(self.ability), self.owner)

    def test_missing_asc_owner_is_none(self):
        self.asc = None; self.assertIsNone(self.profile.GetOwningPlayerState(self.ability))

    def test_living_native_health_is_false(self):
        self.assertIs(self.profile.IsAvatarDeadOrDying(self.ability)["IsDeadOrDying"], False)

    def test_dying_native_health_is_true(self):
        self.dead = True; self.assertIs(self.profile.IsAvatarDeadOrDying(self.ability)["IsDeadOrDying"], True)

    def test_missing_avatar_is_false_without_health_lookup(self):
        self.avatar = None; self.assertIs(self.profile.IsAvatarDeadOrDying(self.ability)["IsDeadOrDying"], False)
        self.assertEqual(len(self.calls), 1)

    def test_missing_native_health_is_false(self):
        self.health = None; self.assertIs(self.profile.IsAvatarDeadOrDying(self.ability)["IsDeadOrDying"], False)

    def test_exact_original_tag_and_primary_instance_resolution(self):
        self.profile.EndDeathAbilities(self.ability, self.asc)
        call = next(row for row in self.calls if row[0] == "FindAllAbilitiesWithTags")
        self.assertEqual(call[1], ())
        self.assertIs(call[2]["bExactMatch"], True)
        self.assertEqual([tag.TagName for tag in call[2]["Tags"].GameplayTags], ["Ability.Type.StatusChange.Death"])
        self.assertEqual(self.ended, ["K2_EndAbility"])
        self.assertEqual(self.module.snapshot()["abilities_ended"], 1)

    def test_empty_tag_result_does_not_end_other_abilities(self):
        self.handles = []; self.profile.EndDeathAbilities(self.ability, self.asc)
        self.assertEqual(self.ended, [])

    def test_original_cdo_resolution_is_not_replaced_by_spec_or_activation(self):
        ability, flag = self.resolved["death-handle"]; self.resolved["death-handle"] = (ability, False)
        self.profile.EndDeathAbilities(self.ability, self.asc)
        self.assertEqual(self.ended, ["K2_EndAbility"])

    def test_missing_asc_or_resolved_ability_is_noop(self):
        self.profile.EndDeathAbilities(self.ability, None)
        self.resolved["death-handle"] = (None, False)
        self.profile.EndDeathAbilities(self.ability, self.asc)
        self.assertEqual(self.ended, [])

    def test_fallback_preserves_original_results_and_entry_names(self):
        fallback = self.module.LyraAutoRespawnHelpersBlueprintFallbackProfile
        self.assertEqual(fallback.GetOwningPlayerState(self.ability), "original-result")
        self.assertEqual(fallback.IsAvatarDeadOrDying(self.ability), {"IsDeadOrDying": False})
        fallback.EndDeathAbilities(self.ability, self.asc)
        self.assertEqual([row[1][0] for row in self.calls], list(self.module.METHODS))
        self.assertEqual(self.module.snapshot()["fallback_death_queries"], 1)
        self.assertEqual(self.profile.IsAvatarDeadOrDying.override, self.module.DEAD_QUERY)
        self.assertIs(self.profile.IsAvatarDeadOrDying.uep_named_outputs, True)
        self.assertIs(fallback.IsAvatarDeadOrDying.uep_named_outputs, True)

    def test_helpers_do_not_override_activation_or_lifecycle(self):
        self.assertEqual({name for name in vars(self.profile) if not name.startswith("__")},
            {"GetOwningPlayerState", "IsAvatarDeadOrDying", "EndDeathAbilities"})
        self.profile.GetOwningPlayerState(self.ability)
        other = types.SimpleNamespace()
        self.assertEqual(self.module.instance_snapshot(other), {})
        copy_ = self.module.snapshot(); copy_["player_state_queries"] = 999
        self.assertEqual(self.module.snapshot()["player_state_queries"], 1)


class ReadinessModels(unittest.TestCase):
    def server_ast(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_helpers_network_validation.py"
        return next(node for node in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Server")

    def test_restored_server_exit_never_rereads_disconnected_controllers(self):
        methods = [node for node in self.server_ast().body if isinstance(node, ast.FunctionDef) and node.name in ("restore_owners", "finish")]
        called = []
        def no_native_state(*args): raise AssertionError("disconnected Controller read")
        scope = dict(native_state=no_native_state, ue=types.SimpleNamespace(log=called.append, log_error=called.append,
            request_exit=lambda: called.append("exit")))
        exec(compile(ast.Module(body=methods, type_ignores=[]), "server-exit-model", "exec"), scope)
        owner = types.SimpleNamespace(restored=True, finished=False, contexts={"A": {"controller": "destroyed"}}, report={}, write=lambda: None)
        owner.restore_owners = lambda: scope["restore_owners"](owner)
        scope["finish"](owner)
        self.assertEqual(owner.report["status"], "awaiting_shutdown")
        self.assertIsNone(owner.report["error"]); self.assertIn("exit", called)

    def test_owner_restore_precedes_client_release_signal(self):
        tick = next(node for node in self.server_ast().body if isinstance(node, ast.FunctionDef) and node.name == "tick")
        release = next(node for node in ast.walk(tick) if isinstance(node, ast.If) and
            isinstance(node.test, ast.Compare) and isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value == "release")
        calls = [node.value for node in release.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)]
        self.assertEqual(calls[0].func.attr, "restore_owners")
        self.assertEqual(calls[1].func.id, "atomic_write")

    def test_network_phase_methods_do_not_shadow_native_instance_fields(self):
        root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities"
        trees = [ast.parse((root/name).read_text(encoding="utf-8")) for name in
            ("auto_respawn_helpers_validation.py", "auto_respawn_helpers_network_validation.py")]
        fields = {node.attr for tree in trees for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store) and isinstance(node.value, ast.Name) and node.value.id == "self"}
        for cls in (node for tree in trees for node in tree.body if isinstance(node, ast.ClassDef)):
            methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
            self.assertFalse(methods & fields, (cls.name, methods & fields))

    def run_ready(self, local_phase):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_helpers_validation.py"
        cls = next(node for node in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Validation")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "ready")
        called, phase_queries = [], []
        world = types.SimpleNamespace(get_world_type=lambda: 1)
        snap = types.SimpleNamespace(bExperienceLoaded=True, bHeroInputReady=True, bAbilitySystemReady=True,
            bHealthReady=True, bDamageImmune=False, Health=100.)
        bridge = types.SimpleNamespace(call_function=lambda name: snap)
        phase = types.SimpleNamespace(call_function=lambda *args: phase_queries.append(args) or False)
        def find_class(name):
            if name == "UEPLyraBridgeLibrary": value = types.SimpleNamespace(call_function=lambda *args: bridge)
            else: value = types.SimpleNamespace(call_function=lambda *args: phase)
            return types.SimpleNamespace(get_cdo=lambda: value)
        scope = dict(ue=types.SimpleNamespace(all_worlds=lambda: [world], find_class=find_class),
            valid=lambda value: value is not None, isolate_bots=lambda *args: None, GameplayTag=types.SimpleNamespace)
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(file), "exec"), scope)
        owner = types.SimpleNamespace(statics=types.SimpleNamespace(call_function=lambda *args: "controller"),
            report={}, require_local_playing_phase=local_phase, attach=lambda *args: True, begin=lambda: called.append(True))
        scope["ready"](owner)
        return called, phase_queries

    def test_standalone_requires_actual_local_authority_playing(self):
        called, queries = self.run_ready(True)
        self.assertEqual(called, []); self.assertEqual(len(queries), 1)

    def test_client_native_readiness_does_not_query_authority_only_phase_map(self):
        called, queries = self.run_ready(False)
        self.assertEqual(called, [True]); self.assertEqual(queries, [])
