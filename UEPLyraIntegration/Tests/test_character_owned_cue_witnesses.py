"""Read-only native Cue identity-witness models; not a GC acceptance result."""
import ast
from pathlib import Path
import types
import unittest


class OwnedCueWitnessModels(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/inventory_wait_transitions.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Transition")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "observe_owned_cue_handles")
        self.world = object(); self.actor = types.SimpleNamespace(path="owned")
        self.handle = types.SimpleNamespace(path="handle")
        self.fields = dict(TargetActor=self.actor, TeamColorWatcherHandle=self.handle)
        self.cue = types.SimpleNamespace(path="cue", get_world=lambda: self.world, get_property=lambda name: self.fields[name])
        self.state = types.SimpleNamespace(world=self.world, actor=self.actor, owner=None, original_proxies=set(), owned_cue_witnesses={})
        engine = types.SimpleNamespace(load_class=lambda name: name, tobject_iterator=lambda cls: [self.cue])
        namespace = dict(ue=engine, valid=lambda value: value is not None, path=lambda value: value.path, CUE="exact-native-cue-class")
        module = ast.Module(body=[method], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(source), "exec"), namespace)
        self.observe = lambda: namespace[method.name](self.state)
    def test_actual_owned_target_records_exact_cue_handle_and_target(self):
        self.observe(); self.assertEqual(self.state.owned_cue_witnesses, {("cue", "handle"): "owned"})
    def test_foreign_target_never_recorded(self):
        self.fields["TargetActor"] = types.SimpleNamespace(path="foreign"); self.observe(); self.assertFalse(self.state.owned_cue_witnesses)
    def test_original_live_proxy_never_classified_as_fixture_owned(self):
        self.state.original_proxies.add("handle"); self.observe(); self.assertFalse(self.state.owned_cue_witnesses)
    def test_null_recycled_target_cannot_create_ownership(self):
        self.fields["TargetActor"] = None; self.observe(); self.assertFalse(self.state.owned_cue_witnesses)
    def test_null_handle_cannot_create_witness(self):
        self.fields["TeamColorWatcherHandle"] = None; self.observe(); self.assertFalse(self.state.owned_cue_witnesses)
    def test_foreign_world_never_recorded(self):
        self.cue.get_world = object; self.observe(); self.assertFalse(self.state.owned_cue_witnesses)
    def test_recycling_preserves_read_only_prior_identity(self):
        self.observe(); self.fields["TargetActor"] = None; self.observe()
        self.assertEqual(self.state.owned_cue_witnesses, {("cue", "handle"): "owned"}); self.assertIsNone(self.fields["TargetActor"])
    def test_replaced_handle_does_not_inherit_old_ownership(self):
        self.observe(); self.fields.update(TargetActor=None, TeamColorWatcherHandle=types.SimpleNamespace(path="foreign-handle")); self.observe()
        self.assertNotIn(("cue", "foreign-handle"), self.state.owned_cue_witnesses)
    def test_native_bot_ready_witness_survives_late_transition_cleanup(self):
        self.fields["TargetActor"] = None
        self.state.owner = types.SimpleNamespace(pawn=self.actor, spawn_cue_witnesses={("cue", "handle"): "owned"})
        self.observe(); self.assertEqual(self.state.owned_cue_witnesses, {("cue", "handle"): "owned"})
    def test_foreign_bot_witness_cannot_be_imported(self):
        self.fields["TargetActor"] = None
        self.state.owner = types.SimpleNamespace(pawn=self.actor, spawn_cue_witnesses={("cue", "handle"): "foreign"})
        self.observe(); self.assertFalse(self.state.owned_cue_witnesses)
    def test_native_bot_ready_captures_before_testing_immunity(self):
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/health_changed_observation.py"
        cls = next(node for node in ast.parse(source.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "OwnedAI")
        ready = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "ready")
        self.assertIsInstance(ready.body[0], ast.Expr)
        self.assertEqual(ready.body[0].value.func.attr, "observe_spawn_cue_handles")
    def test_native_bot_late_bootstrap_is_quarantined_during_ready(self):
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/health_changed_observation.py"
        tree = ast.parse(source.read_text(encoding="utf-8")); cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "OwnedAI")
        ready = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "ready")
        calls = [node.args[0].value for node in ast.walk(ready) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "call_function" and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertIn("IsRunning", calls); self.assertIn("StopLogic", calls); self.assertIn("StopMovement", calls)
