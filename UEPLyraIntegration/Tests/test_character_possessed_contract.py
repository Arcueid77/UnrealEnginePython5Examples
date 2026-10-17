"""Synthetic factory report guards; old wait-only success is insufficient."""
import unittest
import test_character_inventory_wait_contract as wait_models
from uep_lyra_characters.possessed_contract import validate


def counters(py=True, controller="controller", proxy="new-proxy"):
    return dict(python_calls=int(py), fallback_calls=int(not py), authority_noops=0, factories=int(py), binds=int(py), activations=int(py),
        null_factories=0, last_controller=controller, last_proxy=proxy if py else None)


def upgrade(value):
    value.update(experience_ready_factory_migrated=True, native_possession_ingress_tested=True, possession_event_manually_called_by_fixture=False, begin_play_business_migrated=False)
    return value


def report():
    value = upgrade(wait_models.report()); value.update(natural_startup_possession=counters(), natural_startup_controller="controller")
    for row in value["readiness_transition_cases"]:
        row.update(native_possession_controller="controller", native_possession_counters=counters(row["profile"] == "Python"),
            old_owned_pawn_natural_python_factory=counters(proxy="old-proxy"), native_possession_factory_proxy_paths=["old-proxy", "new-proxy"],
            native_possession_factory_proxies_created=2, native_possession_factory_proxies_collected=True, possession_event_manually_called_by_fixture=False)
        row.update(native_controller_bootstrap_experience_proxy_paths=["controller-bootstrap"], native_controller_bootstrap_experience_proxies_collected=True)
    return value


class CharacterPossessedReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def row(self): return self.report["readiness_transition_cases"][1]
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.report)
    def test_complete_shape_is_a_model(self): self.assertEqual(validate(self.report)["native_owned_possessions"], 24)
    def test_old_wait_only_report_does_not_certify_factory(self): self.report["experience_ready_factory_migrated"] = False; self.reject()
    def test_event_not_replayed(self): self.report["possession_event_manually_called_by_fixture"] = True; self.reject()
    def test_row_event_not_replayed(self): self.row()["possession_event_manually_called_by_fixture"] = True; self.reject()
    def test_begin_play_not_overclaimed(self): self.report["begin_play_business_migrated"] = True; self.reject()
    def test_natural_startup_profile_required(self): self.report["natural_startup_possession"]["python_calls"] = 0; self.reject()
    def test_exact_controller_payload(self): self.row()["native_possession_counters"]["last_controller"] = "wrong"; self.reject()
    def test_actual_independent_native_proxy(self): self.row()["native_possession_counters"]["last_proxy"] = "invented"; self.reject()
    def test_no_owned_factory_proxy_leak(self): self.row()["native_possession_factory_proxies_collected"] = False; self.reject()
    def test_both_actual_owned_possessions_required(self): self.row()["native_possession_factory_proxies_created"] = 1; self.reject()
    def test_distinct_native_proxy_identities(self): self.row()["native_possession_factory_proxy_paths"] = ["new-proxy"]*2; self.reject()
    def test_named_binding_required(self): self.row()["native_possession_counters"]["binds"] = 0; self.reject()
    def test_no_duplicate_factory(self): self.row()["native_possession_counters"]["factories"] = 2; self.reject()
    def test_previous_native_wait_matrix_still_required(self): self.row()["no_grant_before_native_readiness"] = False; self.reject()
    def test_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterPossessedResult=x"]), "uep_lyra_characters.possessed_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterPossessedResult=x"]))
    def test_proxy_path_is_captured_before_native_gc(self):
        import ast
        from pathlib import Path
        from types import SimpleNamespace
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/possessed_observation.py"
        cls = next(value for value in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(value, ast.ClassDef) and value.name == "Transition")
        method = next(value for value in cls.body if isinstance(value, ast.FunctionDef) and value.name == "capture_factory")
        proxy = SimpleNamespace(path="actual-native-proxy")
        def require(value, message):
            if not value: raise RuntimeError(message)
        namespace = dict(live=lambda: {"actual-native-proxy": proxy}, path=lambda value: value.path, require=require)
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(file), "exec"), namespace)
        observation = SimpleNamespace(possession_proxies=[], possession_proxy_paths=[], bootstrap_proxies=[], bootstrap_paths=[])
        namespace["capture_factory"](observation, set()); proxy.path = None
        self.assertEqual(observation.possession_proxy_paths, ["actual-native-proxy"])
    def test_controller_bootstrap_task_cannot_be_miscounted_as_character(self): self.row()["native_controller_bootstrap_experience_proxy_paths"] = ["old-proxy"]; self.reject()
    def test_controller_bootstrap_tasks_must_collect(self): self.row()["native_controller_bootstrap_experience_proxies_collected"] = False; self.reject()
