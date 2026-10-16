"""Host-side contract tests for the event-driven Lyra HUD presenter."""

from pathlib import Path
import importlib
import sys
import types
import unittest


class _FakeUnrealEngine(types.ModuleType):
    def __init__(self):
        super().__init__("unreal_engine")
        self.logs = []
        self.errors = []
        self.load_class_error = None
        self.loaded_class = object()
        self.registered_mixins = []

    def find_class(self, name):
        if name != "LyraHealthComponent":
            raise AssertionError("unexpected reflected class: " + name)
        return _FakeHealth

    def log(self, message):
        self.logs.append(str(message))

    def log_error(self, message):
        self.errors.append(str(message))

    def load_class(self, path):
        if path != "/Game/UI/Hud/W_Healthbar.W_Healthbar_C":
            raise AssertionError("unexpected class path: " + path)
        if self.load_class_error is not None:
            raise self.load_class_error
        return self.loaded_class

    def register_declared_mixin(self, target_class):
        self.registered_mixins.append(target_class)


fake_ue = _FakeUnrealEngine()
sys.modules["unreal_engine"] = fake_ue

SCRIPTS_ROOT = (
    Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"
)
sys.path.insert(0, str(SCRIPTS_ROOT))

from uep_lyra_hud import state  # noqa: E402
from uep_lyra_hud.healthbar_mixin import (  # noqa: E402
    LyraHealthbarBlueprintFallbackProfile,
    LyraHealthbarPythonProfile,
)


class _FakeObject:
    def __init__(self, path):
        self.path = path
        self.valid = True

    def is_valid(self):
        return self.valid

    def get_path_name(self):
        return self.path


class _FakeEventSource(_FakeObject):
    def __init__(self, path):
        super().__init__(path)
        self.callbacks = {}

    def bind_event(self, name, callback):
        self.callbacks.setdefault(name, []).append(callback)

    def unbind_event(self, name, callback):
        callbacks = self.callbacks.get(name, [])
        for index, candidate in enumerate(callbacks):
            if candidate is callback:
                del callbacks[index]
                return
        raise AssertionError("unbind did not receive the exact bound callback")

    def broadcast(self, name, *args):
        for callback in list(self.callbacks.get(name, [])):
            callback(*args)


class _FakeHealth(_FakeEventSource):
    def __init__(self, path, health=100.0, max_health=100.0):
        super().__init__(path)
        self.health = health
        self.max_health = max_health

    def call_function(self, name):
        if name == "GetHealth":
            return self.health
        if name == "GetMaxHealth":
            return self.max_health
        raise AssertionError("unexpected health function: " + name)

    def set_health(self, value):
        old_value = self.health
        self.health = value
        self.broadcast("OnHealthChanged", self, old_value, value, None)

    def set_max_health(self, value):
        old_value = self.max_health
        self.max_health = value
        self.broadcast("OnMaxHealthChanged", self, old_value, value, None)


class _FakePawn(_FakeObject):
    def __init__(self, path, health):
        super().__init__(path)
        self.health = health

    def get_component_by_type(self, component_class):
        if component_class is not _FakeHealth:
            raise AssertionError("unexpected component class")
        return self.health


class _FakeController(_FakeEventSource):
    def __init__(self, path, pawn):
        super().__init__(path)
        self.pawn = pawn

    def get_controlled_pawn(self):
        return self.pawn

    def possess(self, pawn):
        old_pawn = self.pawn
        self.pawn = pawn
        self.broadcast("OnPossessedPawnChanged", old_pawn, pawn)


class _FakeNumber(_FakeObject):
    def __init__(self, path):
        super().__init__(path)
        self.current_value = None
        self.target_value = None
        self.calls = []

    def call_function(self, name, *args):
        self.calls.append((name, *args))
        if name == "SetCurrentValue":
            self.current_value = self.target_value = args[0]
        elif name == "InterpolateToValue":
            self.target_value = args[0]
        else:
            raise AssertionError("unexpected number function: " + name)


class _FakeMaterial(_FakeObject):
    def __init__(self, path):
        super().__init__(path)
        self.scalars = {}

    def call_function(self, name, parameter, value):
        if name != "SetScalarParameterValue":
            raise AssertionError("unexpected material function: " + name)
        self.scalars[parameter] = value


class _FakeImage(_FakeObject):
    def __init__(self, path, material):
        super().__init__(path)
        self.material = material

    def call_function(self, name):
        if name != "GetDynamicMaterial":
            raise AssertionError("unexpected image function: " + name)
        return self.material


class _PythonHealthbarHarness(LyraHealthbarPythonProfile):
    next_id = 1

    def __init__(self, controller):
        instance_id = type(self).next_id
        type(self).next_id += 1
        self.path = "/Engine/Transient.W_Healthbar_C_{}".format(instance_id)
        self.controller = controller
        self.HealthNumber = _FakeNumber(self.path + ".HealthNumber")
        for name in ("BarBorderMID", "BarFillMID", "BarGlowMID"):
            setattr(self, name, _FakeMaterial(self.path + "." + name))
            setattr(self, name[:-3], _FakeImage(self.path + "." + name[:-3], getattr(self, name)))
        for name in ("OnDamaged", "OnHealed", "OnEliminated", "OnSpawned"):
            setattr(self, name, _FakeObject(self.path + "." + name))
        self.played_animations = []
        self.playing_animations = set()
        self.reset_visual_calls = 0
        self.dynamic_material_calls = 0
        self.initialize_visual_calls = 0
        self.original_calls = []
        self.routed_calls = []
        self.defer_native_stops = False
        self.pending_native_stops = []
        self.flush_calls = 0
        super().__init__()

    def SetDynamicMaterials(self):
        self.dynamic_material_calls += 1
        super().SetDynamicMaterials()

    def InitializeBarVisuals(self):
        self.initialize_visual_calls += 1
        super().InitializeBarVisuals()

    def ResetAnimatedState(self):
        self.reset_visual_calls += 1
        super().ResetAnimatedState()

    def is_valid(self):
        return True

    def get_path_name(self):
        return self.path

    def call_function(self, name, *args):
        aliases = {"Health Changed": "HealthChanged", "OnPosessedPawnChanged": "OnPosessedPawnChanged",
                   "EventOnEliminated": "EventOnEliminated"}
        if name in aliases:
            self.routed_calls.append(name)
            return getattr(self, aliases[name])(*args)
        if name == "GetOwningPlayer":
            return self.controller
        if name in ("SetDynamicMaterials", "InitializeBarVisuals", "ResetAnimatedState"):
            raise AssertionError("project visual helpers must execute in Python")
        if name == "PlayAnimationForward":
            self.played_animations.append(args[0])
            self.playing_animations.add(args[0])
            return None
        if name == "StopAnimation":
            if args[0] in self.playing_animations:
                self.playing_animations.remove(args[0])
                if self.defer_native_stops:
                    self.pending_native_stops.append(args[0])
                else:
                    self.OnAnimationFinished(args[0])
            return None
        if name == "FlushAnimations":
            self.flush_calls += 1
            pending, self.pending_native_stops = self.pending_native_stops, []
            for animation in pending:
                if animation == self.OnSpawned:
                    for field in ("BarBorderMID", "BarFillMID", "BarGlowMID"):
                        getattr(self, field).scalars["Health_Updated"] = 1.0
                self.OnAnimationFinished(animation)
            return None
        if name == "PauseAnimation":
            self.playing_animations.discard(args[0])
            return None
        if name == "IsAnimationPlaying":
            return args[0] in self.playing_animations
        raise AssertionError("unexpected widget function: " + name)

    def call_mixin_original(self, name, *args):
        self.original_calls.append(name)

    def finish_animation(self, animation):
        self.playing_animations.discard(animation)
        self.OnAnimationFinished(animation)


class _FallbackHarness(LyraHealthbarBlueprintFallbackProfile):
    def __init__(self):
        self.original_calls = []

    def call_mixin_original(self, name):
        self.original_calls.append(name)


class LyraHealthbarPresenterTests(unittest.TestCase):
    def make_harness(self):
        health = _FakeHealth("/Game/Test.HealthA")
        pawn = _FakePawn("/Game/Test.PawnA", health)
        controller = _FakeController("/Game/Test.Controller", pawn)
        return _PythonHealthbarHarness(controller), controller, pawn, health

    def test_bootstrap_allows_source_only_stage_without_healthbar_asset(self):
        module_name = "uep_lyra_hud.bootstrap"
        previous_log_count = len(fake_ue.logs)
        previous_registration_count = len(fake_ue.registered_mixins)
        fake_ue.load_class_error = Exception("unable to find class")
        sys.modules.pop(module_name, None)
        try:
            bootstrap = importlib.import_module(module_name)
        finally:
            fake_ue.load_class_error = None

        self.assertFalse(bootstrap.registered)
        self.assertFalse(state.snapshot()["source_asset_available"])
        self.assertEqual(
            len(fake_ue.registered_mixins), previous_registration_count
        )
        self.assertIn(
            "UEP_LYRA_HUD_SOURCE_ASSET_UNAVAILABLE",
            fake_ue.logs[previous_log_count:],
        )

    def test_construct_binds_and_renders_initial_health(self):
        before = state.snapshot()
        widget, _, _, health = self.make_harness()

        widget.Construct()

        after = state.snapshot()
        self.assertEqual(widget.dynamic_material_calls, 1)
        self.assertEqual(widget.initialize_visual_calls, 1)
        self.assertEqual(widget.HealthNumber.current_value, 100.0)
        self.assertEqual(widget.NormalizedHealth, 1.0)
        self.assertEqual(after["construct_count"] - before["construct_count"], 1)
        self.assertEqual(
            after["controller_bind_count"] - before["controller_bind_count"], 1
        )
        self.assertEqual(after["health_bind_count"] - before["health_bind_count"], 1)
        self.assertEqual(len(health.callbacks["OnHealthChanged"]), 1)
        self.assertEqual(len(health.callbacks["OnMaxHealthChanged"]), 1)

        widget.Destruct()

    def test_original_health_and_pawn_entries_are_reflected_production_ingress(self):
        before = state.snapshot()["public_entry_counts"]
        widget, controller, _, health = self.make_harness()
        widget.Construct()
        health.set_health(90.0)
        self.assertIn("Health Changed", widget.routed_calls)
        replacement = _FakePawn("/Game/Test.NewPawn", _FakeHealth("/Game/Test.NewHealth", 80.0))
        controller.possess(replacement)
        self.assertIn("OnPosessedPawnChanged", widget.routed_calls)
        self.assertEqual(widget.HealthNumber.current_value, 80.0)
        after = state.snapshot()["public_entry_counts"]
        self.assertEqual(after["Health Changed"]-before["Health Changed"], 1)
        self.assertEqual(after["OnPosessedPawnChanged"]-before["OnPosessedPawnChanged"], 1)
        widget.Destruct()

    def test_public_elimination_entry_uses_python_animation_policy(self):
        widget, _, _, _ = self.make_harness()
        widget.Construct()
        widget.call_function("EventOnEliminated")
        self.assertEqual(widget.played_animations[-1], widget.OnEliminated)
        self.assertEqual(LyraHealthbarPythonProfile.HealthChanged.override, "Health Changed")
        self.assertNotIn("EventOnEliminated", widget.original_calls)
        widget.Destruct()

    def test_health_change_is_event_driven_and_normalized(self):
        before = state.snapshot()
        widget, _, _, health = self.make_harness()
        widget.Construct()

        health.set_health(90.0)

        after = state.snapshot()
        self.assertEqual(widget.HealthNumber.target_value, 90.0)
        self.assertAlmostEqual(widget.NormalizedHealth, 0.9)
        self.assertEqual(widget.HealthOldValue, 100.0)
        self.assertEqual(widget.HealthNewValue, 90.0)
        self.assertEqual(
            after["visual_update_count"] - before["visual_update_count"], 2
        )
        self.assertEqual(after["health_events"][-1]["event"], "health_changed")

        health.set_max_health(200.0)
        self.assertAlmostEqual(widget.NormalizedHealth, 0.45)
        self.assertEqual(widget.HealthOldValue, 90.0)
        self.assertEqual(widget.HealthNewValue, 90.0)
        self.assertEqual(state.snapshot()["health_events"][-1]["event"], "max_health_changed")

        widget.Destruct()

    def test_pawn_replacement_unbinds_old_component(self):
        widget, controller, _, old_health = self.make_harness()
        widget.Construct()
        new_health = _FakeHealth("/Game/Test.HealthB", health=75.0)
        new_pawn = _FakePawn("/Game/Test.PawnB", new_health)

        controller.possess(new_pawn)
        old_update_count = widget.initialize_visual_calls
        old_health.set_health(50.0)

        self.assertEqual(widget.initialize_visual_calls, old_update_count)
        self.assertEqual(old_health.callbacks["OnHealthChanged"], [])
        self.assertEqual(old_health.callbacks["OnMaxHealthChanged"], [])
        self.assertEqual(widget.HealthNumber.current_value, 75.0)
        self.assertEqual(len(new_health.callbacks["OnHealthChanged"]), 1)

        new_health.set_health(70.0)
        self.assertEqual(widget.HealthNumber.target_value, 70.0)
        widget.Destruct()

    def test_destruct_removes_exact_callbacks_without_blueprint_business(self):
        before = state.snapshot()
        widget, controller, _, health = self.make_harness()
        widget.Construct()

        widget.Destruct()

        after = state.snapshot()
        self.assertEqual(controller.callbacks["OnPossessedPawnChanged"], [])
        self.assertEqual(health.callbacks["OnHealthChanged"], [])
        self.assertEqual(health.callbacks["OnMaxHealthChanged"], [])
        self.assertNotIn("Destruct", widget.original_calls)
        self.assertEqual(after["destruct_count"] - before["destruct_count"], 1)
        self.assertEqual(
            after["controller_bind_count"] - after["controller_unbind_count"],
            before["controller_bind_count"] - before["controller_unbind_count"],
        )
        self.assertEqual(
            after["health_bind_count"] - after["health_unbind_count"],
            before["health_bind_count"] - before["health_unbind_count"],
        )

    def test_registry_teardown_removes_callbacks_without_destruct_dispatch(self):
        before = state.snapshot()
        widget, controller, _, health = self.make_harness()
        widget.Construct()

        widget.__uep_mixin_teardown__()

        after = state.snapshot()
        self.assertEqual(controller.callbacks["OnPossessedPawnChanged"], [])
        self.assertEqual(health.callbacks["OnHealthChanged"], [])
        self.assertNotIn("Destruct", widget.original_calls)
        self.assertEqual(after["teardown_count"] - before["teardown_count"], 1)

    def test_blueprint_fallback_profile_only_calls_original_construct(self):
        widget = _FallbackHarness()

        widget.Construct()

        self.assertEqual(widget.original_calls, ["Construct"])


if __name__ == "__main__":
    unittest.main()
