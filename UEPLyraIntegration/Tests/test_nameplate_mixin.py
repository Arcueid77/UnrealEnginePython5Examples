"""Mock policy/lifetime checks only; never a native nameplate acceptance."""
import importlib.util
import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Object:
    def __init__(self, name, handler=None):
        self.name, self.handler, self.calls, self.events = name, handler, [], {}
        self.active = True

    def is_valid(self):
        return self.active

    def is_a(self, cls):
        return self.name == "pawn"

    def get_path_name(self):
        return self.name

    def set_property(self, field, value):
        setattr(self, field, value)

    def call_function(self, name, *args):
        self.calls.append((name, *args))
        if name == "Cancel":
            self.active = False
        return self.handler(name, *args) if self.handler else None

    def bind_event(self, event, callback):
        self.events.setdefault(event, []).append(callback)

    def unbind_event(self, event, callback):
        self.events[event].remove(callback)

    def emit(self, event, *args):
        for callback in list(self.events.get(event, [])):
            callback(*args)


class NameplatePolicy(unittest.TestCase):
    def setUp(self):
        self.percent, self.team, self.comparison = .37, 1, 0
        self.health = Object("health", lambda name, *args: self.percent if name == "GetHealthNormalized" else None)
        self.extension = Object("extension", lambda name, *args: self.pawn if name == "GetOwner" else None)
        self.owner = Object("owner")
        self.player_state = Object("state", lambda name, *args: "Player One")
        self.pawn = Object("pawn", lambda name, *args: self.owner if name == "GetController" else None)
        self.pawn.PlayerState = self.player_state
        self.indicator = Object("indicator", lambda name, *args: self.pawn if name == "GetDataObject" else None)
        self.proxies = []
        self.materials = {}
        native = types.ModuleType("unreal_engine")

        def native_call(cls, name, *args):
            if cls == "LyraHealthComponent":
                return self.health if args[0] is self.pawn else None
            if cls == "LyraPawnExtensionComponent":
                return self.extension if args[0] is self.pawn else None
            if cls == "SubsystemBlueprintLibrary":
                return Object("team_subsystem", lambda *args: (self.comparison, self.team, self.team))
            if cls == "KismetTextLibrary":
                return args[0]
            if cls == "AsyncAction_ObserveTeam":
                proxy = Object("team-proxy-"+str(len(self.proxies)))
                proxy.handler = lambda name, *args: proxy.emit("OnTeamChanged", self.team >= 0, self.team) if name == "Activate" else None
                self.proxies.append(proxy)
                return proxy
            raise AssertionError((cls, name))

        native.find_class = lambda cls: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda name, *args: native_call(cls, name, *args)))
        native.load_object = lambda cls, path: path
        structs = types.ModuleType("unreal_engine.structs")
        structs.SlateBrush = lambda **values: types.SimpleNamespace(**values)
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None and (not hasattr(value, "is_valid") or value.is_valid())
        runtime = types.ModuleType("uep_runtime")
        scope_spec = importlib.util.spec_from_file_location("_np_test_scope", Path(__file__).resolve().parents[3]/"Content/Scripts/uep_runtime/subscriptions.py")
        scope_module = importlib.util.module_from_spec(scope_spec)
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/nameplate_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._nameplate_policy_test", source)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs,
                                     "uep_runtime": runtime, "uep_lyra_hud.weapon_observer": observer}):
            scope_spec.loader.exec_module(scope_module)
            runtime.SubscriptionScope = scope_module.SubscriptionScope
            spec.loader.exec_module(self.module)
        self.widget = self.module.LyraNameplatePythonProfile()
        self.widget.Pawn = self.widget.Indicator = None
        self.widget.TeamId, self.widget.HideOwnerName, self.widget.ShowTeamNamesOnly = 0, False, False
        self.widget.UEPOriginalNameplateTeamProxy = None
        self.widget.get_path_name = lambda: "nameplate"
        self.widget.set_property = lambda field, value: setattr(self.widget, field, value)
        self.calls = []
        self.visibility = 0
        for name in ("Health", "Name", "Glow", "TeamIcon"):
            value = Object(name)
            value.Brush = types.SimpleNamespace(TintColor="tint", DrawAs=1, Tiling=2, Mirroring=3,
                ImageSize="size", Margin="margin", OutlineSettings="outline", ResourceObject="original")
            material = Object(name+"Material")
            self.materials[name] = material
            value.handler = lambda method, *args, material=material: material if method in ("GetDynamicMaterial", "GetDynamicFontMaterial") else None
            setattr(self.widget, name, value)

        def call(name, *args):
            self.calls.append((name, *args))
            if name == "GetOwningPlayer":
                return self.owner
            if name == "SetVisibility":
                self.visibility = args[0]
                return
            if name == self.module.INIT_BIND:
                self.widget.PawnReadyEvent(None)  # Explicit immediate callback mock.
                return
            if name in (self.module.INIT_UNBIND, self.module.ORIGINAL_HEALTH_CLEANUP):
                return
            if name == "Health Changed":
                return self.widget.HealthChanged(*args)
            return getattr(self.widget, name)(*args)

        self.widget.call_function = call

    def bind(self):
        self.widget.BindIndicator(self.indicator)

    def test_runtime_reflected_state_writes_bypass_editor_notifications(self):
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/nameplate_mixin.py"
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                fields = [target.attr for group in targets for target in ast.walk(group) if isinstance(target, ast.Attribute)]
                self.assertFalse(set(fields) & {"Pawn", "Indicator", "TeamId", "NameText"}, fields)

    def test_immediate_init_callback_has_ownership_before_reentry(self):
        self.bind()
        self.assertTrue(self.widget._uep_np_live)
        self.assertIs(self.widget._uep_np_extension, self.extension)
        self.assertEqual(self.widget.NameText, "Player One")
        self.assertEqual(self.widget._uep_np_init_callbacks, 1)
        self.assertEqual(self.indicator.calls[:2], [("GetDataObject",), ("SetDesiredVisibility", False)])
        self.assertIn(("SetDesiredVisibility", True), self.indicator.calls)

    def test_health_callback_queries_native_normalized_not_payload_arithmetic(self):
        self.bind()
        self.percent = .23
        self.health.emit("OnHealthChanged", self.health, 999, -2, None)
        self.assertEqual(self.materials["Health"].calls[-1], ("SetScalarParameterValue", "Progress", .23))
        self.assertEqual(self.widget._uep_np_health_callbacks, 1)

    def test_team_callback_false_ignores_id_and_does_not_recompute_visibility(self):
        self.bind()
        before = len(self.calls)
        self.proxies[-1].emit("OnTeamChanged", False, 2)
        self.assertEqual(self.widget.TeamId, 1)
        self.assertEqual(len(self.calls), before)
        self.proxies[-1].emit("OnTeamChanged", True, 2)
        self.assertEqual(self.widget.TeamId, 2)
        self.assertNotIn(("UpdateVisibility",), self.calls[before:])

    def test_repeat_initialize_replays_native_team_activation_but_not_health_binding(self):
        self.bind()
        self.widget.InitializeNameplate(self.pawn, "New Name")
        self.assertEqual(len(self.proxies), 2)
        self.assertFalse(self.proxies[0].active)
        self.assertEqual(len(self.health.events["OnHealthChanged"]), 1)
        self.assertEqual(self.widget._uep_np_team_callbacks, 2)
        self.widget.UnbindIndicator(self.indicator)
        final = self.module.snapshot()
        self.assertEqual((final["scopes_created"], final["scopes_closed"]), (3, 3))
        self.assertEqual((final["team_proxies_created"], final["team_proxies_cancelled"]), (2, 2))

    def test_hidden_owner_branch_precedes_team_comparison(self):
        self.bind()
        self.widget.HideOwnerName = self.widget.ShowTeamNamesOnly = True
        self.module.subsystem = lambda context: self.fail("owner branch must not compare teams")
        self.widget.UpdateVisibility()
        self.assertEqual(self.visibility, 1)

    def test_team_filter_same_team_does_not_restore_collapsed_visibility(self):
        self.bind()
        self.widget.ShowTeamNamesOnly = True
        self.comparison = 1
        self.widget.UpdateVisibility()
        self.assertEqual(self.visibility, 1)
        self.comparison = 0
        self.widget.UpdateVisibility()
        self.assertEqual(self.visibility, 1)

    def test_team_comparison_uses_enum_not_the_two_out_parameters(self):
        self.module.subsystem = lambda context: Object("team_subsystem", lambda *args: (0, 17, 29))
        self.assertEqual(self.module.compare_teams(self.widget, self.pawn, self.owner), 0)
        self.module.subsystem = lambda context: Object("team_subsystem", lambda *args: (1, 0, 0))
        self.assertEqual(self.module.compare_teams(self.widget, self.pawn, self.owner), 1)

    def test_team_comparison_rejects_wrong_reflected_output_shape(self):
        self.module.subsystem = lambda context: Object("team_subsystem", lambda *args: (0, 1))
        with self.assertRaises(ValueError):
            self.module.compare_teams(self.widget, self.pawn, self.owner)

    def test_missing_native_init_manager_is_not_called_after_shutdown(self):
        self.bind()
        original_find = self.module.ue.find_class
        self.module.ue.find_class = lambda cls: types.SimpleNamespace(get_cdo=lambda:
            types.SimpleNamespace(call_function=lambda *args: None)) if cls == "SubsystemBlueprintLibrary" else original_find(cls)
        self.widget.UnbindIndicator(self.indicator)
        self.assertNotIn((self.module.INIT_UNBIND, self.extension), self.calls)
        final = self.module.snapshot()
        self.assertEqual((final["init_bound"], final["init_unbound"], final["init_owner_released"]), (1, 0, 1))
        self.assertEqual((final["scopes_created"], final["scopes_closed"]), (2, 2))

    def test_no_team_filter_does_not_implicitly_restore_visibility(self):
        self.bind()
        self.visibility = 1
        self.widget.ShowTeamNamesOnly = False
        self.widget.UpdateVisibility()
        self.assertEqual(self.visibility, 1)

    def test_brush_rebuild_retains_designer_fields_and_leaves_unexecuted_icon_alone(self):
        self.bind()
        brush = self.widget.Health.calls[0][1]
        self.assertEqual((brush.ImageSize, brush.TintColor, brush.OutlineSettings), ("size", "tint", "outline"))
        self.assertIn("RedTeam_HealthBar", brush.ResourceObject)
        self.assertEqual(self.widget.TeamIcon.calls, [])

    def test_select_invalid_index_matches_option_zero_without_team_substitute(self):
        self.bind()
        for index in (0, -1, 255):
            self.widget.TeamId = index
            self.widget.SetTeamVisuals()
            self.assertIsNone(self.widget.Health.calls[-2][1].ResourceObject)
            self.assertEqual(self.materials["Glow"].calls[-1][-1], 0.0)

    def test_unbind_closes_once_and_held_callbacks_do_not_deliver_later(self):
        self.bind()
        health = self.health.events["OnHealthChanged"][0]
        team = self.proxies[-1].events["OnTeamChanged"][0]
        self.widget.UnbindIndicator(self.indicator)
        before = len(self.calls)
        health(self.health, 100, 50, None)
        team(True, 2)
        self.widget.PawnReadyEvent(None)
        self.assertEqual(len(self.calls), before)
        self.assertIsNone(self.widget.Pawn)
        self.assertIsNone(self.widget.Indicator)
        self.widget.__uep_mixin_teardown__()
        final = self.module.snapshot()
        self.assertEqual(final["active_count"], 0)
        self.assertEqual((final["init_bound"], final["init_unbound"]), (1, 1))
        self.assertEqual((final["scopes_created"], final["scopes_closed"]), (2, 2))

    def test_death_uses_native_unregister_and_disarmed_callback_cannot_repeat(self):
        self.bind()
        self.health.emit("OnDeathStarted", self.pawn)
        self.assertEqual(self.indicator.calls.count(("UnregisterIndicator",)), 1)
        self.widget.UnbindIndicator(self.indicator)
        self.widget.DeathStarted(self.pawn)
        self.assertEqual(self.indicator.calls.count(("UnregisterIndicator",)), 1)

    def test_missing_extension_remains_not_ready_without_new_tick(self):
        self.extension = None
        self.bind()
        self.assertFalse(self.widget._uep_np_live)
        self.assertEqual(self.module.snapshot()["active_count"], 0)
        self.assertEqual(self.proxies, [])
        self.assertFalse(hasattr(self.widget, "Tick"))

    def test_invalid_indicator_does_not_register_or_create_sources(self):
        self.widget.BindIndicator(None)
        self.assertEqual(self.proxies, [])
        self.assertFalse(self.widget._uep_np_live)

    def test_destruct_does_not_clear_native_descriptor_model(self):
        self.bind()
        self.widget.Destruct()
        self.assertIs(self.widget.Indicator, self.indicator)
        self.assertIs(self.widget.Pawn, self.pawn)
        self.assertEqual(self.module.snapshot()["active_count"], 0)
