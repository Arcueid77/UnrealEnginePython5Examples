"""Source instigator, cache and interface branches without a UMG runtime."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native = types.ModuleType("unreal_engine")
helpers = types.ModuleType("uep_lyra_world.effect_pad_mixin"); helpers.valid = lambda value:value is not None
spec = importlib.util.spec_from_file_location("_cue_widget_policy",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/cue_widget_mixin.py")
policy = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":helpers}): spec.loader.exec_module(policy)


class Widget:
    def __init__(self): self.calls = []
    def call_function(self,*args): self.calls.append(args); return False


class CueWidgetPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls = []; self.widget = Widget(); self.seed = Widget(); self.local = True; self.bot = False; self.player_state = True; self.interface = True
        self.controller = types.SimpleNamespace(call_function=lambda name:self.local)
        self.instigator = types.SimpleNamespace(is_a=lambda cls:self.player_state, get_property=lambda name:self.bot,
            call_function=lambda name:self.controller)
        self.data = {"WidgetToSpawn":"widget-class", "SpawnedWidget":self.seed,"OptionalLocalController":"previous-controller"}
        self.actor = types.SimpleNamespace(get_property=self.data.get,set_property=self.write)
        native.find_class = lambda cls:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda method,*a,**kw:self.backend(method,a,kw)))
        native.load_class = lambda name:name; native.FLinearColor = lambda *args:args
    def write(self,name,value): self.calls.append(("write",name,value)); self.data[name] = value
    def backend(self,method,args,kwargs):
        self.calls.append((method,args,kwargs))
        if method == "GetInstigatorActor": return self.instigator
        if method == "GetDisplayName": return "fixture-instigator"
        if method == "Create": return self.widget
        if method == "DoesImplementInterface": return self.interface
    def start(self): return policy.start(self.actor,"cue-params")
    def test_native_instigator_helper_receives_original_parameters(self):
        self.start(); self.assertIn(("GetInstigatorActor",("cue-params",),{}),self.calls)
    def test_none_instigator_clears_controller_and_uses_native_world_creation(self):
        self.instigator = None; self.start(); self.assertIsNone(self.data["OptionalLocalController"])
        self.assertEqual(next(v[1] for v in self.calls if v[0] == "Create"),(self.actor,"widget-class",None))
    def test_local_player_state_creates_with_resolved_controller(self):
        self.start(); self.assertIs(self.data["OptionalLocalController"],self.controller)
        self.assertEqual(next(v[1] for v in self.calls if v[0] == "Create"),(self.actor,"widget-class",self.controller))
    def test_foreign_instigator_leaves_old_fields_untouched(self):
        self.player_state = False; self.start(); self.assertIs(self.data["SpawnedWidget"],self.seed); self.assertEqual(self.data["OptionalLocalController"],"previous-controller")
    def test_orphan_player_state_retains_existing_widget(self):
        self.controller = None; self.start(); self.assertIs(self.data["SpawnedWidget"],self.seed); self.assertFalse(any(v[0] == "Create" for v in self.calls))
    def test_bot_skips_without_warning_or_creation(self):
        self.bot = True; self.start(); self.assertEqual([v[0] for v in self.calls],["GetInstigatorActor"])
    def test_remote_controller_preserves_fields_without_creation(self):
        self.local = False; self.start(); self.assertEqual([v[0] for v in self.calls],["GetInstigatorActor"]); self.assertIs(self.data["SpawnedWidget"],self.seed)
    def test_unresolved_warning_keeps_exact_source_arguments(self):
        self.player_state = False; self.start(); message = next(v[2] for v in self.calls if v[0] == "PrintString")
        self.assertEqual(message,dict(WorldContextObject=self.actor,InString="Unable to determine local player for widget from Instigator:  fixture-instigator",
            bPrintToScreen=True,bPrintToLog=True,TextColor=(0.,.66,1.,1.),Duration=2.,Key="None"))
    def test_failed_creation_overwrites_cache_and_preserves_old_parent(self):
        self.widget = None; self.start(); self.assertIsNone(self.data["SpawnedWidget"]); self.assertEqual(self.seed.calls,[])
        self.assertEqual(next(v[2]["InString"] for v in self.calls if v[0] == "PrintString"),"Failed to create widget!")
    def test_screen_add_failure_still_sends_interface_message(self):
        self.start(); self.assertEqual(self.widget.calls,[("AddToPlayerScreen",0),("ConstructFromCueParams","cue-params")])
    def test_non_interface_widget_silently_skips_message(self):
        self.interface = False; self.start(); self.assertEqual(self.widget.calls,[("AddToPlayerScreen",0)])
    def test_repeated_start_does_not_remove_previous_widget(self):
        self.start(); old = self.widget; self.widget = Widget(); self.start()
        self.assertFalse(any(call[0] == "RemoveFromParent" for call in old.calls)); self.assertIs(self.data["SpawnedWidget"],self.widget)
    def test_removal_retains_cached_widget_and_controller(self):
        before = dict(self.data); self.assertIs(policy.remove(self.actor),False); self.assertEqual(self.data,before); self.assertEqual(self.seed.calls,[("RemoveFromParent",)])
    def test_removal_without_widget_is_noop(self):
        self.data["SpawnedWidget"] = None; policy.remove(self.actor); self.assertEqual(self.calls,[])
    def test_gate_ignores_target_and_spawn_results_and_suppresses_original_body(self):
        self.assertIs(policy.LyraCueWidgetPythonProfile.Start(self.actor,"unused-target","cue-params","unused-spawns"),False)
    def test_fallback_gates_preserve_original_business(self):
        self.assertIs(policy.LyraCueWidgetBlueprintFallbackProfile.Start(self.actor,None,None,None),True)
        self.assertIs(policy.LyraCueWidgetBlueprintFallbackProfile.Remove(self.actor,None,None,None),True); self.assertEqual(self.calls,[])
