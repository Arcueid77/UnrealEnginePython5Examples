"""Discovery, descriptor and owned-listener model; no Engine acceptance claim."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_nameplate_mixin import Object


class NameplateComponents(unittest.TestCase):
    def setUp(self):
        self.bus, self.descriptors, self.roots, self.messages = {}, [], 0, []
        self.controller = Object("controller", lambda name, *args: True if name == "IsLocalPlayerController" else None)
        self.controller.is_a = lambda cls: cls in ("Controller", "LyraPlayerController")
        self.pawn = Object("pawn")
        self.pawn.is_a = lambda cls: cls in ("Pawn", "Character")
        self.pawn.CapsuleComponent, self.pawn.RootComponent = Object("capsule"), Object("root")
        self.indicators = []
        self.native_manager = Object("native-indicators", lambda name, descriptor: self.indicators.append(descriptor) if name == "AddIndicator" else None)
        native = types.ModuleType("unreal_engine")
        native.FVector = lambda *values: values
        native.find_class = lambda cls: cls
        structs = types.ModuleType("unreal_engine.structs")
        structs.LinearColor = structs.GameplayTag = lambda **values: types.SimpleNamespace(**values)

        def new(cls):
            if cls == "IndicatorDescriptor":
                descriptor = Object("descriptor"+str(len(self.descriptors)))
                descriptor.handler = lambda name, *args: self.indicators.remove(descriptor) if name == "UnregisterIndicator" and descriptor in self.indicators else None
                self.descriptors.append(descriptor)
                return descriptor
            reader = Object("reader")
            reader.add_to_root = lambda: setattr(self, "roots", self.roots+1)
            reader.remove_from_root = lambda: setattr(self, "roots", self.roots-1)
            return reader

        native.new_object = new
        runtime = types.ModuleType("uep_runtime")
        owner = self

        class Scope:
            def __init__(self):
                self.closed, self.bindings = False, []

            def listen_gameplay_message(self, context, channel, payload_type, reader, callback):
                def dispatch(value):
                    if not self.closed:
                        callback(channel, value)
                owner.bus.setdefault(channel, []).append(dispatch)
                self.bindings.append((channel, dispatch))

            def close(self):
                self.closed = True
                for channel, dispatch in self.bindings:
                    owner.bus[channel].remove(dispatch)
                self.bindings = []

        runtime.SubscriptionScope = Scope
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None and value.is_valid()
        message = types.ModuleType("uep_lyra_hud.nameplate_messages")
        message.INFO, message.REQUEST, message.PAWN, message.MANAGER, message.PREFIX = "info", "request", "pawn", "manager", "Nameplate."
        message.payload_type = lambda name: name
        message.owner_pawn = lambda source: self.pawn
        message.read = lambda helper, proxy, info: proxy

        def broadcast(context, helper, action, value):
            self.messages.append(action)
            payload = types.SimpleNamespace(**{"manager" if action == "Discover" else "pawn": value})
            for dispatch in list(self.bus.get("Nameplate."+action, [])):
                dispatch(payload)
        message.broadcast = broadcast

        root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud"
        modules = {"unreal_engine": native, "unreal_engine.structs": structs, "uep_runtime": runtime,
                   "uep_lyra_hud.weapon_observer": observer, "uep_lyra_hud.nameplate_messages": message}
        self.source_module = self.load(root/"nameplate_source_mixin.py", "uep_lyra_hud._np_source_test", modules)
        self.manager_module = self.load(root/"nameplate_manager_mixin.py", "uep_lyra_hud._np_manager_test", modules)
        self.source = self.source_module.LyraNameplateSourcePythonProfile()
        self.manager = self.manager_module.LyraNameplateManagerPythonProfile()
        self.manager.IndicatorMap = {}
        self.source.PythonMessageAdapterClass = self.manager.PythonMessageAdapterClass = "Reader"
        for value, name in ((self.source, "source"), (self.manager, "manager")):
            value.get_path_name = lambda name=name: name
            value.is_valid = lambda: True
            value.set_property = lambda field, content, value=value: setattr(value, field, content)
            value.call_function = lambda function, *args, value=value: self.call(value, function, *args)
        self.events = []
        self.manager_module.print_native = lambda context, text: self.events.append(text)
        # The class registry remains explicit, while CDO calls represent native
        # Library functions. Only the IndicatorLibrary is needed in this model.
        native.find_class = lambda cls: Class(cls, self.native_manager)
        self.pawn.is_a = lambda cls: cls.name in ("Pawn", "Character")
        self.controller.is_a = lambda cls: cls.name in ("Controller", "LyraPlayerController")
        native.new_object = lambda cls: new(cls.name if isinstance(cls, Class) else cls)

    @staticmethod
    def load(path, name, modules):
        spec = importlib.util.spec_from_file_location(name, path)
        value = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(value)
        return value

    def call(self, obj, name, *args):
        if name == "GetOwner":
            return self.pawn if obj is self.source else self.controller
        if name == "K2_DestroyComponent":
            self.assertEqual(args, (obj,), "ProcessEvent does not fill the Blueprint DefaultToSelf caller pin")
            self.events.append("destroy")
            return
        return getattr(obj, name)(*args)

    def test_source_add_before_discovery_listen_and_manager_ready_discovers(self):
        self.source.BeginPlay()
        self.assertEqual(self.messages, ["Add"])
        self.assertEqual(self.indicators, [])
        self.manager.BeginPlay()
        self.assertEqual(self.messages, ["Add", "Discover"])
        self.assertEqual(len(self.indicators), 1)
        self.assertEqual(self.source._uep_np_discoveries, 1)

    def test_manager_subscriptions_exist_before_source_native_add(self):
        self.manager.BeginPlay()
        self.source.BeginPlay()
        self.assertEqual(self.messages, ["Discover", "Add"])
        self.assertEqual(len(self.indicators), 1)

    def test_character_descriptor_exact_native_configuration_and_local_storage(self):
        self.manager.RegisterNameplateSource(self.pawn)
        calls = self.descriptors[0].calls
        self.assertEqual(calls, [("SetIndicatorClass", self.manager_module.WIDGET),
            ("SetSceneComponent", self.pawn.CapsuleComponent), ("SetProjectionMode", 1),
            ("SetBoundingBoxAnchor", (.5, .5, 1.0)), ("SetDataObject", self.pawn),
            ("SetVAlign", 3), ("SetAutoRemoveWhenIndicatorComponentIsNull", True), ("SetClampToScreen", True)])
        self.assertFalse(hasattr(self.manager, "Indicator"))
        self.assertIs(self.manager.IndicatorMap[self.pawn], self.descriptors[0])

    def test_noncharacter_uses_root_point_and_world_offset(self):
        self.pawn.is_a = lambda cls: cls.name == "Pawn"
        self.manager.RegisterNameplateSource(self.pawn)
        self.assertEqual(self.descriptors[0].calls[1:4], [("SetSceneComponent", self.pawn.RootComponent),
            ("SetWorldPositionOffset", (0.0, 0.0, 100.0)), ("SetProjectionMode", 0)])

    def test_unregister_removes_map_and_native_descriptor_missing_key_is_noop(self):
        self.manager.RegisterNameplateSource(self.pawn)
        self.manager.UnregisterNameplateSource(self.pawn)
        self.manager.UnregisterNameplateSource(self.pawn)
        self.assertEqual(self.indicators, [])
        self.assertEqual(self.manager.IndicatorMap, {})
        self.assertEqual(self.descriptors[0].calls.count(("UnregisterIndicator",)), 1)

    def test_repeated_key_retains_original_map_add_behavior_as_an_explicit_gap(self):
        self.manager.RegisterNameplateSource(self.pawn)
        self.manager.RegisterNameplateSource(self.pawn)
        self.assertEqual(len(self.manager.IndicatorMap), 1)
        self.assertEqual(len(self.indicators), 2)
        self.assertIs(self.manager.IndicatorMap[self.pawn], self.descriptors[1])
        self.assertEqual(self.manager_module.snapshot()["duplicate_keys"], 1)
        self.manager.EndPlay(0)
        self.assertEqual(self.indicators, [self.descriptors[0]])
        # Source audit predicts this old-descriptor behavior; real native BP
        # comparison/release policy is still required, not claimed by this mock.

    def test_native_unregister_callback_nested_removal_must_not_restore_stale_map(self):
        other = Object("other-pawn")
        other.is_a = self.pawn.is_a
        other.CapsuleComponent, other.RootComponent = Object("other-capsule"), Object("other-root")
        self.manager.RegisterNameplateSource(self.pawn)
        self.manager.RegisterNameplateSource(other)
        first, second = self.descriptors
        native_handler = first.handler

        def reentrant(name, *args):
            if name == "UnregisterIndicator":
                self.manager.UnregisterNameplateSource(other)
            return native_handler(name, *args)

        first.handler = reentrant
        self.manager.UnregisterNameplateSource(self.pawn)
        self.assertEqual(self.manager.IndicatorMap, {})
        self.assertEqual(self.indicators, [])
        self.assertEqual(second.calls.count(("UnregisterIndicator",)), 1)

    def test_native_unregister_callback_nested_registration_is_preserved(self):
        other = Object("new-pawn")
        other.is_a = self.pawn.is_a
        other.CapsuleComponent, other.RootComponent = Object("new-capsule"), Object("new-root")
        self.manager.RegisterNameplateSource(self.pawn)
        first = self.descriptors[0]
        native_handler = first.handler

        def reentrant(name, *args):
            if name == "UnregisterIndicator":
                self.manager.RegisterNameplateSource(other)
            return native_handler(name, *args)

        first.handler = reentrant
        self.manager.UnregisterNameplateSource(self.pawn)
        self.assertEqual(list(self.manager.IndicatorMap), [other])
        self.assertEqual(len(self.indicators), 1)

    def test_endplays_close_roots_scopes_and_remove_once(self):
        self.source.BeginPlay()
        self.manager.BeginPlay()
        self.source.EndPlay(0)
        self.source.EndPlay(0)
        self.manager.EndPlay(0)
        self.manager.EndPlay(0)
        self.assertEqual(self.messages, ["Add", "Discover", "Remove"])
        self.assertEqual(self.indicators, [])
        self.assertEqual(self.roots, 0)
        for module in (self.source_module, self.manager_module):
            final = module.snapshot()
            self.assertEqual(final["scopes_created"], final["scopes_closed"])
            self.assertGreater(final["helpers_rooted"], 0)
            self.assertEqual(final["helpers_rooted"], final["helpers_unrooted"])
            self.assertEqual(final["active_count"], 0)

    def test_nonlocal_controller_destroys_without_reader_or_scope(self):
        self.controller.handler = lambda name, *args: False
        self.manager.BeginPlay()
        self.assertEqual(self.events, ["destroy"])
        self.assertEqual(self.roots, 0)
        self.assertEqual(self.manager_module.snapshot()["scopes_created"], 0)

    def test_wrong_owner_type_destroys_without_islocal_call(self):
        self.controller.is_a = lambda cls: False
        self.manager.BeginPlay()
        self.assertEqual(self.events, ["destroy"])
        self.assertEqual(self.controller.calls, [])

    def test_source_profile_teardown_is_not_remove_and_resume_is_listener_only(self):
        self.source.BeginPlay()
        self.source.__uep_mixin_teardown__()
        self.source.ResumeDiscovery()
        self.assertEqual(self.messages, ["Add"])
        self.source.EndPlay(0)
        self.source.ResumeDiscovery()
        self.assertEqual(self.messages, ["Add", "Remove"])
        self.assertEqual(self.roots, 0)

    def test_manager_profile_teardown_keeps_map_and_resume_does_not_discover(self):
        self.manager.BeginPlay()
        self.source.BeginPlay()
        before = self.manager.IndicatorMap.copy()
        self.manager.__uep_mixin_teardown__()
        self.assertEqual(self.manager.IndicatorMap, before)
        self.manager.ResumeObservation()
        self.assertEqual(self.messages, ["Discover", "Add"])
        self.assertEqual(self.manager.IndicatorMap, before)

    def test_held_discovery_callback_is_disarmed_after_close(self):
        self.source.BeginPlay()
        callback = self.bus["Nameplate.Discover"][0]
        self.source.__uep_mixin_teardown__()
        callback(types.SimpleNamespace(manager=self.manager))
        self.assertEqual(self.descriptors, [])

    def test_original_proxy_cleanup_uses_runtime_set_property_not_editor_assignment(self):
        proxies = {field: Object(field) for field in (self.source_module.PROXY, "AsyncListForAdd", "AsyncListenForRemove")}

        class Receiver:
            def __getattr__(self, field):
                return proxies[field]

            def __setattr__(self, field, value):
                raise AssertionError("Editor property notification would reconstruct the owner")

            def set_property(self, field, value):
                self_writes.append((field, value))

        self_writes = []
        original = Receiver()
        self.source_module.close_original(original)
        self.manager_module.close_original(original)
        self.assertEqual(self_writes, [(self.source_module.PROXY, None), ("AsyncListForAdd", None), ("AsyncListenForRemove", None)])
        for proxy in proxies.values():
            self.assertEqual(proxy.calls, [("Cancel",)])

    def test_null_manager_discovery_has_no_registration(self):
        self.source.BeginPlay()
        self.bus["Nameplate.Discover"][0](types.SimpleNamespace(manager=None))
        self.assertEqual(self.descriptors, [])
        self.assertEqual(self.source_module.snapshot()["null_managers"], 1)

    def test_descriptor_cleanup_attempts_remaining_entries_after_native_failure(self):
        other = Object("other-pawn")
        self.manager.RegisterNameplateSource(self.pawn)
        self.manager.IndicatorMap[other] = Object("remaining-descriptor")
        self.descriptors[0].handler = lambda *args: (_ for _ in ()).throw(RuntimeError("native unregister failed"))
        remaining = self.manager.IndicatorMap[other]
        with self.assertRaisesRegex(RuntimeError, "descriptor cleanup failed"):
            self.manager_module.clear_descriptors(self.manager)
        self.assertEqual(remaining.calls, [("UnregisterIndicator",)])
        self.assertEqual(self.manager.IndicatorMap, {})
        self.assertEqual(self.manager_module.snapshot()["errors"], ["native unregister failed"])


class Class:
    def __init__(self, name, manager):
        self.name, self.manager = name, manager

    def get_cdo(self):
        if self.name == "IndicatorLibrary":
            return types.SimpleNamespace(call_function=lambda *args: self.manager)
        raise AssertionError(self.name)
