"""Explicit in-memory-only original/Python startup comparison control models."""
import importlib
from pathlib import Path
import types
import unittest
from unittest.mock import patch

control=importlib.import_module("uep_lyra_abilities.melee_character_default_control")


class TestCharacterDefaultControl(unittest.TestCase):
    def setUp(self):
        self.fields=dict(PythonMixinProfile="Python");self.writes=[]
        def write(name,value):self.writes.append((name,value));self.fields[name]=value
        self.cdo=types.SimpleNamespace(get_property=lambda name:self.fields[name],set_property=write,
            call_function=lambda name:self.fields["PythonMixinProfile"])
        item=patch.object(control,"ue",types.SimpleNamespace(load_class=lambda path:types.SimpleNamespace(get_cdo=lambda:self.cdo)))
        item.start();self.addCleanup(item.stop)
    def test_original_default_then_restore(self):
        value=control.CharacterDefaultControl("BlueprintFallback")
        self.assertEqual(self.fields["PythonMixinProfile"],"BlueprintFallback");self.assertTrue(value.restore());self.assertEqual(self.fields["PythonMixinProfile"],"Python")
    def test_matched_python_preload_control(self):
        value=control.CharacterDefaultControl("Python")
        self.assertTrue(value.report["preloaded_before_validation"]);self.assertEqual(value.report["profile"],"Python");self.assertTrue(value.restore())
    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):control.CharacterDefaultControl("guess")
        self.assertEqual(self.writes,[])
    def test_original_method_isolation_requires_matched_python(self):
        with self.assertRaises(ValueError):control.CharacterDefaultControl("BlueprintFallback",original_begin_play=True)
        self.assertEqual(self.writes,[])
    def test_original_halves_are_disjoint_and_complete(self):
        fn=lambda:None;values={name:fn for name in ("A","B","C","D","E")}
        first=control.original_methods(values,values,"first-half");second=control.original_methods(values,values,"second-half")
        self.assertEqual(first,["A","B","C"]);self.assertEqual(second,["D","E"])
    def test_original_halves_exclude_scaffolding_and_python_only_helpers(self):
        fn=lambda:None
        self.assertEqual(control.original_methods(dict(A=fn,__init__=fn,Helper=fn),dict(A=fn,__init__=fn),"first-half"),["A"])
    def test_unknown_subset_rejected(self):
        with self.assertRaises(ValueError):control.CharacterDefaultControl("Python",original_subset="guess")
        self.assertEqual(self.writes,[])
    def test_exact_inventory_group_does_not_change_possession(self):
        fn=lambda:None;values=dict(AddInitialInventory=fn,ReceivePossessed=fn)
        self.assertEqual(control.original_methods(values,values,"inventory"),["AddInitialInventory"])
    def test_group_requires_all_native_profile_functions(self):
        fn=lambda:None
        with self.assertRaises(ValueError):control.original_methods(dict(ReceivePossessed=fn),dict(ReceivePossessed=fn),"possession")
    def test_possession_subgroups_are_disjoint_and_complete(self):
        fn=lambda:None;values={name:fn for name in control.GROUPS["possession"]}
        first=control.original_methods(values,values,"possession_factory");second=control.original_methods(values,values,"experience")
        self.assertEqual(first,["ReceivePossessed"]);self.assertEqual(set(first+second),set(control.GROUPS["possession"]));self.assertFalse(set(first)&set(second))
    def test_no_asset_or_health_repair(self):
        text=Path(control.__file__).read_text(encoding="utf-8")
        for forbidden in ("save_package(","InitializeWithAbilitySystem","SetNumericAttribute"):
            self.assertTrue(forbidden not in text,forbidden)
    def test_restore_is_idempotent(self):
        value=control.CharacterDefaultControl("BlueprintFallback");value.restore();count=len(self.writes);value.restore();self.assertEqual(len(self.writes),count)
    def test_closed_monitor_never_checks_restored_native_class(self):
        value=control.CharacterDefaultControl("Python");value.restore()
        with patch.object(control,"ue",types.SimpleNamespace(load_class=lambda path:(_ for _ in ()).throw(AssertionError("no native read after close")))):
            value.observe_registration()
    def test_birth_observation_calls_selected_handler_exactly_once_and_restores(self):
        calls=[]
        class Production:
            def ReceiveBeginPlay(pawn): calls.append(("selected",pawn))
            def Other(pawn): pass
        cls=types.SimpleNamespace(get_cdo=lambda:self.cdo);actual=[Production]
        native=types.SimpleNamespace(load_class=lambda path:cls,
            get_registered_mixins=lambda:[dict(target_class=cls,profiles=dict(Python=dict(python_class=actual[0])))],
            register_mixin_profile=lambda target,name,value:actual.__setitem__(0,value))
        with patch.object(control,"ue",native):
            value=control.CharacterDefaultControl("Python")
            value.observe_births(types.SimpleNamespace(birth=lambda pawn:calls.append(("birth",pawn))))
            actual[0].ReceiveBeginPlay("pawn");value.observe_registration()
            self.assertEqual(calls,[("birth","pawn"),("selected","pawn")]);self.assertIs(actual[0].Other,Production.Other)
            value.restore();self.assertIs(actual[0],Production)
    def test_birth_observer_preserves_queued_unpublished_treatment(self):
        calls=[]
        class Selected:
            def ReceiveBeginPlay(pawn): calls.append(pawn)
        cls=types.SimpleNamespace(get_cdo=lambda:self.cdo);registered=[]
        native=types.SimpleNamespace(load_class=lambda path:cls,get_registered_mixins=lambda:[],
            register_mixin_profile=lambda target,name,value:registered.append(value))
        with patch.object(control,"ue",native):
            value=control.CharacterDefaultControl("Python");value.expected_class=Selected
            value.original_python_class=Selected
            value.observe_births(types.SimpleNamespace(birth=lambda pawn:None))
            registered[-1].ReceiveBeginPlay("pawn");self.assertEqual(calls,["pawn"])
            value.restore();self.assertIs(registered[-1],Selected)
    def test_construction_observer_calls_original_native_event_once(self):
        calls=[]
        class Production:
            def ReceiveBeginPlay(pawn): pass
        cls=types.SimpleNamespace(get_cdo=lambda:self.cdo);actual=[Production]
        native=types.SimpleNamespace(load_class=lambda path:cls,get_registered_mixins=lambda:[dict(target_class=cls,profiles=dict(Python=dict(python_class=actual[0])))],
            register_mixin_profile=lambda target,name,value:actual.__setitem__(0,value))
        pawn=types.SimpleNamespace(call_mixin_original=lambda name:calls.append(name))
        with patch.object(control,"ue",native):
            value=control.CharacterDefaultControl("Python")
            value.observe_births(types.SimpleNamespace(birth=lambda pawn:None,constructed=lambda pawn:calls.append("construction")),construction=True)
            actual[0].UserConstructionScript(pawn)
            self.assertEqual(calls,["construction","UserConstructionScript"]);value.restore()
    def test_construction_observer_preserves_selected_python_construction(self):
        calls=[]
        class Production:
            def ReceiveBeginPlay(pawn): pass
            def UserConstructionScript(pawn): calls.append("selected")
        cls=types.SimpleNamespace(get_cdo=lambda:self.cdo);actual=[Production]
        native=types.SimpleNamespace(load_class=lambda path:cls,get_registered_mixins=lambda:[dict(target_class=cls,profiles=dict(Python=dict(python_class=actual[0])))],
            register_mixin_profile=lambda target,name,value:actual.__setitem__(0,value))
        with patch.object(control,"ue",native):
            value=control.CharacterDefaultControl("Python")
            value.observe_births(types.SimpleNamespace(constructed=lambda pawn:calls.append("construction")),construction=True)
            actual[0].UserConstructionScript(object());self.assertEqual(calls,["construction","selected"]);value.restore()


if __name__ == "__main__": unittest.main()
