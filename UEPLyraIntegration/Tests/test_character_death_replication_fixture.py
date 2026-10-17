"""Private native signal-only fixture routing and non-rooting source guards."""
import ast
from pathlib import Path
import types
import unittest
from uep_lyra_hud.startup import validation_module

ROOT = Path(__file__).parents[1]/"Overlay/Content/Scripts"
FLAG = "-UEPCharacterDeathReplicationNetworkResult=x"


class DeathReplicationFixtureModels(unittest.TestCase):
    def test_explicit_selector_and_commandlet_disarm(self):
        self.assertEqual(validation_module([FLAG]), "uep_lyra_characters.death_replication_network_validation")
        self.assertIsNone(validation_module(["-run=Py", FLAG]))
    def test_parent_footers_do_not_start_duplicate_fixtures(self):
        for relative in ("uep_lyra_abilities/auto_respawn_helpers_network_validation.py", "uep_lyra_abilities/auto_respawn_activation_network_validation.py",
                "uep_lyra_characters/lifecycle_network_validation.py", "uep_lyra_characters/death_started_network_validation.py"):
            file = ROOT/relative; footer = ast.parse(file.read_text(encoding="utf-8")).body[-1]
            def unexpected(*args): raise AssertionError("duplicate native fixture")
            namespace = dict(sys=types.SimpleNamespace(argv=[FLAG, "-UEPAutoRespawnActivation"]), Client=unexpected, Server=unexpected, arg=unexpected)
            with self.subTest(file=relative): exec(compile(ast.Module(body=[footer], type_ignores=[]), str(file), "exec"), namespace)
    def test_witness_is_read_only_except_owned_profile_selection_and_cleanup(self):
        file = ROOT/"uep_lyra_characters/death_replication_observation.py"; tree = ast.parse(file.read_text(encoding="utf-8"))
        text = ast.unparse(tree)
        for forbidden in ("set_property", "add_to_root", "death_damage", "K2_DestroyActor", "Delay", "PlayAnimMontage", "SetActorHiddenInGame", "SetAllBodiesBelowSimulatePhysics"):
            self.assertNotIn(forbidden, text)
        self.assertIn("bind_event", text); self.assertIn("OnDeathStarted", text)
        self.assertIn("self.actor = None", text)
    def test_cross_world_identity_uses_native_playerstate_not_actor_name(self):
        file = ROOT/"uep_lyra_characters/death_replication_network_validation.py"; text = file.read_text(encoding="utf-8")
        self.assertIn('int(actor.get_property("PlayerState").PlayerId)', text)
        self.assertNotIn("spawn_actor", text)
    def test_death_observers_close_before_native_shutdown_reporting(self):
        file = ROOT/"uep_lyra_characters/death_replication_network_validation.py"
        scope = next(node for node in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef) and node.name == "Scope")
        final = next(node for node in scope.body if isinstance(node, ast.FunctionDef) and node.name == "finalize")
        self.assertEqual(ast.unparse(final.body[0]), "self.close_death_witness()")
        self.assertIn("death_replication_fixture_shutdown", ast.unparse(final.body[1]))
        self.assertEqual(ast.unparse(final.body[2]), "super().finalize()")
    def test_native_perception_pointer_read_handles_world_without_ai_and_ai_without_system(self):
        file = ROOT/"uep_lyra_characters/death_replication_observation.py"
        node = next(value for value in ast.parse(file.read_text(encoding="utf-8")).body if isinstance(value, ast.FunctionDef) and value.name == "perception_systems")
        namespace = dict(valid=lambda value: value is not None, path=lambda value: value)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), "exec"), namespace)
        def world(system, ai=True):
            def ai_property(name): self.assertEqual(name, "PerceptionSystem"); return system
            def world_property(name): self.assertEqual(name, "AISystem"); return types.SimpleNamespace(get_property=ai_property) if ai else None
            return types.SimpleNamespace(get_property=world_property)
        read = namespace["perception_systems"]
        self.assertEqual(read(world(None, False)), [])
        self.assertEqual(read(world(None)), [])
        self.assertEqual(read(world("actual-native-system")), ["actual-native-system"])
        self.assertNotIn("get_world()", ast.unparse(node)); self.assertNotIn("CreateAISystem", ast.unparse(node))
    def test_native_relevancy_precedes_trial_baseline_without_replication_property_writes(self):
        text = (ROOT/"uep_lyra_characters/death_replication_network_validation.py").read_text(encoding="utf-8")
        self.assertLess(text.index('actor.call_function("K2_TeleportTo"'), text.index("super().prepare()"))
        self.assertNotIn("set_property", text)
        self.assertNotIn("bAlwaysRelevant", text)
