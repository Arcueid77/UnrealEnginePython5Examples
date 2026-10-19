"""Reject missing inherited/native calls and source menu/guard drift."""
import copy
import unittest
from uep_lyra_audio.music_manager_contract import PLANS,validate


def report():
    value=dict(status="passed",error=None,natural_python_tick_before_probe=1,pairs={})
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","begin_play_listeners_migrated","child_delay_business_migrated","cpp_compile_executed"):value[key]=False
    for key in ("profile_restored","manager_fields_restored","owned_actors_destroyed","player_health_unchanged","original_signatures_preserved"):value[key]=True
    for method,plan in PLANS.items():
        rows=[]
        for index,args in enumerate(plan):
            state=dict(intensity=.4,movement=.2,menu=False,parameters={})
            if method=="SetIsMenu":state["menu"]=args[2]
            if method=="Receive Player Death":state["intensity"]=1. if args[0]=="local" else args[1]
            if method=="Receive Weapon Fire":state["intensity"]=max(0.,min(1.,args[2]+args[1])) if args[0]=="local" else args[2]
            if method=="Fire Stinger":state["intensity"]=0.
            count=1 if method=="ReceiveTick" else 2
            rows.append(dict(index=index,observations=[copy.deepcopy(state) for _ in range(count*2)],fallback_dispatches=count,python_dispatches=count))
        value["pairs"][method]=rows
    return value


class TestMusicManagerContract(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())["base_methods"],5)
    def test_registered_profile_without_actual_calls_rejected(self):
        value=report();value["pairs"]["ReceiveTick"][0]["python_dispatches"]=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_identical_but_repaired_menu_property_rejected(self):
        value=report()
        for state in value["pairs"]["SetIsMenu"][0]["observations"]:state["menu"]=True
        with self.assertRaises(RuntimeError):validate(value)
    def test_native_parameter_or_original_state_disagreement_rejected(self):
        value=report();value["pairs"]["ReceiveTick"][0]["observations"][1]["parameters"]["Intensity"]=99.
        with self.assertRaises(RuntimeError):validate(value)
    def test_natural_tick_and_full_original_restoration_required(self):
        for key,wrong in (("natural_python_tick_before_probe",0),("manager_fields_restored",False),("original_signatures_preserved",False)):
            value=report();value[key]=wrong
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_listener_or_child_delay_migration_not_claimed(self):
        for key in ("begin_play_listeners_migrated","child_delay_business_migrated","full_acceptance"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
