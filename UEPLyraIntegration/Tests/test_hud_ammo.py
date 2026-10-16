"""Contract tests for Python weapon HUD logic; real BP comparisons are separate."""

import copy
from pathlib import Path
import sys
import types
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"
sys.path.insert(0, str(SCRIPTS))

class Tag:
    def __init__(self, TagName):
        self.TagName = TagName

class Brush:
    def __init__(self):
        for name, value in {"TintColor": "white", "DrawAs": 1, "Tiling": 0,
                            "Mirroring": 0, "ImageSize": (32, 32), "Margin": 0,
                            "OutlineSettings": 0, "ResourceObject": None}.items():
            setattr(self, name, value)

fake_structs = types.ModuleType("unreal_engine.structs")
fake_structs.GameplayTag, fake_structs.SlateBrush = Tag, Brush
sys.modules["unreal_engine.structs"] = fake_structs
if "unreal_engine" not in sys.modules:
    sys.modules["unreal_engine"] = types.ModuleType("unreal_engine")
# Examples tests mock the optional plugin helper; its implementation has its
# own host/native tests in UEP. Do not depend on a sibling checkout layout.
class FakeScope:
    def bind_event(self, *args):
        pass
    def listen_gameplay_signal(self, *args):
        pass
    def close(self):
        pass
runtime_helpers = types.ModuleType("uep_runtime")
runtime_helpers.SubscriptionScope = FakeScope
sys.modules.setdefault("uep_runtime", runtime_helpers)
from uep_lyra_hud import ammo_mixin as ammo
from uep_lyra_hud import weapon_observer as observer

class Object:
    def __init__(self):
        self.valid = True

    def is_valid(self):
        return self.valid

    def get_path_name(self):
        return "object-" + str(id(self))

class Material(Object):
    def __init__(self):
        super().__init__()
        self.scalars, self.textures = {}, {}

    def call_function(self, name, key, value):
        if name == "SetScalarParameterValue":
            self.scalars[key] = value
        elif name == "SetTextureParameterValue":
            self.textures[key] = value
        else:
            raise AssertionError(name)

class Image(Object):
    def __init__(self):
        super().__init__()
        self.material, self.Brush = Material(), Brush()

    def call_function(self, name, *args):
        if name == "GetDynamicMaterial":
            return self.material
        if name == "SetBrush":
            self.Brush = copy.copy(args[0])
            return
        raise AssertionError(name)

class Item(Object):
    def __init__(self, current=10, maximum=30, spare=90):
        super().__init__()
        self.stats = {ammo.MAGAZINE_AMMO: current, ammo.MAGAZINE_SIZE: maximum, ammo.SPARE_AMMO: spare}

    def call_function(self, name, argument):
        if name == "GetStatTagStackCount":
            return self.stats[argument.TagName]
        if name == "FindFragmentByClass":
            return None
        raise AssertionError(name)

class Counter(ammo.LyraAmmoCounterPythonProfile, Object):
    def __init__(self, name):
        super().__init__()
        Object.__init__(self)
        self.name = name
        self.InventoryInstance = Item()
        self.AmmoCounter_Bar, self.AmmoCounter_Glow = Image(), Image()

    def get_class(self):
        return types.SimpleNamespace(get_name=lambda: self.name)

    def call_function(self, name):
        if name == "GetOwningPlayer":
            return None
        raise AssertionError(name)

class Display(Object):
    def __init__(self):
        super().__init__()
        self.text, self.visibility = "unchanged", None

    def call_function(self, name, value):
        if name == "SetText":
            self.text = value
        elif name == "SetVisibility":
            self.visibility = value
        else:
            raise AssertionError(name)

class Panel(ammo.LyraWeaponAmmoPythonProfile, Object):
    def __init__(self, item):
        super().__init__()
        Object.__init__(self)
        self.item = item
        self.InventoryItem, self.QuickBar = None, None
        self.VerticalBoxForHiding = Display()
        self.AmmoLeftInMagazineWidget, self.TotalCountWidget = Display(), Display()
        self.WeaponNameWidget = Display()
        quickbar = Object()
        quickbar.call_function = lambda name: self.item
        controller = Object()
        controller.get_component_by_type = lambda cls: quickbar
        controller.get_controlled_pawn = lambda: None
        self.controller = controller

    def call_function(self, name):
        if name == "GetOwningPlayer":
            return self.controller
        raise AssertionError("project BP business must not be called: " + name)

class AmmoPresenterTests(unittest.TestCase):
    def setUp(self):
        self.saved_ue = ammo.ue
        self.saved_observer_ue = observer.ue
        self.handles, self.removed = [], []
        def add_ticker(callback):
            handle = object()
            self.handles.append(handle)
            return handle
        observer.ue = types.SimpleNamespace(add_ticker=add_ticker, remove_ticker=self.removed.append,
                                            find_class=lambda name: name, log_error=lambda error: self.fail(error))
        library = types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda name, value, sign, grouping, minimum, maximum: format(value, ",") if grouping else str(value)))
        ammo.ue = types.SimpleNamespace(find_class=lambda name: library if name == "KismetTextLibrary" else name)

    def tearDown(self):
        observer.close()
        observer.ue = self.saved_observer_ue
        ammo.ue = self.saved_ue

    def test_three_counters_match_authored_low_ammo_thresholds(self):
        for name, threshold in ammo.LOW_AMMO_THRESHOLDS.items():
            counter = Counter(name)
            counter.OnWeaponInitialized()
            for count in (0, threshold, threshold + 1, 30):
                counter.InventoryInstance.stats[ammo.MAGAZINE_AMMO] = count
                counter.Tick(None, 0.016)
                observer.refresh()
                for image in (counter.AmmoCounter_Bar, counter.AmmoCounter_Glow):
                    self.assertEqual(image.material.scalars, {"Rounds_Max": 30.0,
                        "Rounds_Current": float(count), "IsLowAmmo": float(count <= threshold)})

    def test_brush_swap_preserves_counter_style(self):
        counter = Counter("W_AmmoCounter_Pistol_C")
        target, source = Image(), Image()
        target.Brush.ImageSize, target.Brush.TintColor = (73, 12), "red"
        source.Brush.ImageSize, source.Brush.ResourceObject = (999, 999), "texture"
        counter.SetWeaponSpecificImages(target, source)
        self.assertEqual(target.Brush.ImageSize, (73, 12))
        self.assertEqual(target.Brush.TintColor, "red")
        self.assertIs(target.Brush.ResourceObject, source)

    def test_weapon_switch_and_empty_slot(self):
        panel = Panel(Item(current=7, spare=1234))
        panel.Construct()
        panel.Tick(None, 0.016)
        self.assertEqual((panel.AmmoLeftInMagazineWidget.text, panel.TotalCountWidget.text), ("7", "1,234"))
        self.assertEqual(panel.WeaponNameWidget.text, "unchanged")
        panel.item = Item(current=3, spare=55)
        panel.Tick(None, 0.016)
        observer.refresh()
        self.assertEqual(panel.AmmoLeftInMagazineWidget.text, "3")
        panel.item = None
        panel.Tick(None, 0.016)
        observer.refresh()
        self.assertIsNone(panel.InventoryItem)
        self.assertEqual(panel.VerticalBoxForHiding.visibility, 2)

    def test_two_instances_never_share_current_inventory(self):
        a, b = Panel(Item(current=5)), Panel(Item(current=25))
        a.Construct()
        b.Construct()
        a.Tick(None, 0.016)
        b.Tick(None, 0.016)
        a.item.stats[ammo.MAGAZINE_AMMO] = 0
        a.Tick(None, 0.016)
        observer.refresh()
        self.assertEqual((a.AmmoLeftInMagazineWidget.text, b.AmmoLeftInMagazineWidget.text), ("0", "25"))

    def test_only_changes_notify_and_one_ticker_is_shared(self):
        a, b = Panel(Item(current=5)), Panel(Item(current=25))
        a.Construct()
        a.Construct()  # Idempotent bind, including native reconstruction.
        b.Construct()
        self.assertEqual(len(self.handles), 1)
        counts = (a._uep_weapon_hud_calls["AmmoChanged"], b._uep_weapon_hud_calls["AmmoChanged"])
        for _ in range(10):
            a.Tick(None, 0.016)
            b.Tick(None, 0.016)
            observer.refresh()
        self.assertEqual(counts, (a._uep_weapon_hud_calls["AmmoChanged"], b._uep_weapon_hud_calls["AmmoChanged"]))
        a.item.stats[ammo.MAGAZINE_AMMO] -= 1
        observer.refresh()
        self.assertEqual(a._uep_weapon_hud_calls["AmmoChanged"], counts[0] + 1)
        self.assertEqual(b._uep_weapon_hud_calls["AmmoChanged"], counts[1])
        a.Destruct()
        self.assertEqual(len(self.removed), 0)
        b.__uep_mixin_teardown__()
        b.__uep_mixin_teardown__()
        self.assertEqual(len(self.removed), 1)
        self.assertEqual(observer.snapshot()["active_count"], 0)
        self.assertFalse(observer.snapshot()["ticker_active"])

    def test_invalid_widget_and_controller_replacement(self):
        panel = Panel(Item(current=7))
        panel.Construct()
        panel.controller.valid = False
        observer.refresh()
        self.assertIsNone(panel.InventoryItem)
        self.assertEqual(panel.VerticalBoxForHiding.visibility, 2)
        panel.valid = False
        observer.refresh()
        self.assertEqual(observer.snapshot()["active_count"], 0)

    def test_live_profile_generation_resumes_without_construct(self):
        panel = Panel(Item(current=7))
        panel.Construct()
        panel.__uep_mixin_teardown__()
        self.assertEqual(observer.snapshot()["active_count"], 0)
        ammo.LyraWeaponAmmoPythonProfile.__init__(panel)
        panel.item.stats[ammo.MAGAZINE_AMMO] = 3
        panel.Tick(None, 0.016)
        self.assertEqual(observer.snapshot()["active_count"], 1)
        self.assertEqual(panel.AmmoLeftInMagazineWidget.text, "3")
        panel.Destruct()
        panel.Tick(None, 0.016)
        self.assertEqual(observer.snapshot()["active_count"], 0)

    def test_shared_inventory_is_read_once_per_sample(self):
        item = Item(current=9)
        a, b = Counter("W_AmmoCounter_Rifle_C"), Counter("W_AmmoCounter_Pistol_C")
        a.InventoryInstance = b.InventoryInstance = item
        a.Construct()
        b.Construct()
        before = observer.snapshot()["item_reads"]
        observer.refresh()
        self.assertEqual(observer.snapshot()["item_reads"] - before, 1)

    def test_custom_presenter_uses_same_owner_sample_and_lifetime(self):
        counter = Counter("W_AmmoCounter_Rifle_C")
        rendered = []
        observer.subscribe(counter, "reticle-ammo", lambda widget, value: rendered.append((widget, value["magazine"])))
        observer.refresh()
        self.assertEqual(rendered, [(counter, 10)])
        observer.refresh()
        self.assertEqual(len(rendered), 1)
        observer.unsubscribe(counter)
        self.assertFalse(observer.snapshot()["ticker_active"])

    def test_missing_inventory_is_zero_not_an_ownership_transfer(self):
        counter = Counter("W_AmmoCounter_Rifle_C")
        counter.InventoryInstance = None
        counter.OnWeaponInitialized()
        counter.Tick(None, 0.016)
        self.assertEqual(counter.AmmoCounter_Glow.material.scalars["Rounds_Current"], 0.0)

    def test_reload_event_injects_native_local_input_not_inventory_writes(self):
        panel = Panel(Item(current=7))
        calls = []
        subsystem = Object()
        subsystem.call_function = lambda *args: calls.append(args)
        library = types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda name, context, cls: subsystem if context is panel else None))
        ammo.ue = types.SimpleNamespace(
            find_class=lambda name: library if name == "SubsystemBlueprintLibrary" else name,
            load_object=lambda cls, path: path,
            FVector=lambda *values: values,
        )
        panel.ReloadClicked()
        self.assertEqual(calls, [("InjectInputVectorForAction",
            "/Game/Input/Actions/IA_Weapon_Reload.IA_Weapon_Reload", (1.0, 0.0, 0.0))])
        self.assertEqual(panel.item.stats[ammo.MAGAZINE_AMMO], 7)
        self.assertEqual(ammo.LyraWeaponAmmoPythonProfile.ReloadClicked.override, ammo.RELOAD_EVENT)
        def fail_injection(*args):
            raise RuntimeError("native input failure")
        subsystem.call_function = fail_injection
        with self.assertRaisesRegex(RuntimeError, "native input failure"):
            panel.ReloadClicked()
        self.assertEqual(panel._uep_weapon_hud_calls["ReloadClicked"], 1,
                         "failed callback must not add successful-call evidence")
