"""Adversarial spawner evidence models, never native acceptance by themselves."""
import ast
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
file=ROOT/"Overlay/Content/Scripts/uep_lyra_world/spawner_contract.py"
spec=importlib.util.spec_from_file_location("spawner_contract_model",file)
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)

class SpawnerContract(unittest.TestCase):
    def setUp(self):
        self.report={"status":"passed","actors_created":18,"actors_destroyed":18,"collision_scopes_created":18,
            "collision_scopes_closed":18,"message_scope_closed":True,"message_helper_unrooted":True,"original_player_restored":True,
            "initial_player_health":100.0,"maximum_health":100.0,"cases":[],"policy_shutdown":{"errors":[]},
            "player_restore":{"inventory_identity_equal":True,"position_error":0.0,"aim_error":0.0,"movement":[1,0],
                "expected_movement":[1,0],"health":100.0,"expected_health":100.0}}
        for flag in ("full_acceptance","network_acceptance","packaged_runtime","handler_called_by_probe","give_weapon_called_by_probe",
                     "timeline_driven_by_probe","cooldown_duration_overridden","ammo_properties_written","inventory_properties_written",
                     "health_properties_written","postgame_native_branch_tested","culture_switch_tested"):
            self.report[flag]=False
        for index,name in enumerate(contract.CASES):
            value={"physical_events":["begin","end"],"cooldown_duration":10.0,"fixture_inventory_rollback":True,
                "reload_tag_removed":True,"cooldown_completed":index in (0,7),"curve_matches":index in (0,7),"respawn_light":index in (0,7),
                "magazine_before":12,"magazine_after":11,"native_equipment_matches":True,"health":100.0,
                "item_delta":int(index in (0,4,5,6)),"available_after_pickup":index in (1,3,8),"spare_delta":5,
                "failure_messages":["Spare Ammo Full"] if index==3 else [],"failure_owner_matches":True}
            self.report["cases"].append({"name":name,"passed":True,"same_class":True,"python":copy.deepcopy(value),"blueprint":copy.deepcopy(value),
                "python_counters":{"constructions":1,"begins":1,"weapon_gives":int(index<7),"ability_gives":int(index>=7)},
                "observed_cooldowns":{"Python":10.01,"BlueprintFallback":10.02} if index in (0,7) else {}})

    def test_complete_bounded_model(self):
        self.assertEqual(contract.validate(self.report)["cases"],9)

    def test_fresh_grant_does_not_select_the_initial_lyra_pistol(self):
        pistol="/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C"
        rifle="/ShooterCore/Weapons/Rifle/ID_Rifle.ID_Rifle_C"
        self.assertEqual(contract.choose_unowned_weapon([pistol]),"Rifle")
        self.assertEqual(contract.choose_unowned_weapon([pistol,rifle]),"Shotgun")

    def test_shortened_timer_and_missing_native_fire_rejected(self):
        for mutate in (lambda r:r["cases"][0]["observed_cooldowns"].update(Python=.5),
                       lambda r:r["cases"][0]["python"].update(magazine_after=12)):
            row=copy.deepcopy(self.report);mutate(row)
            with self.assertRaises(RuntimeError):contract.validate(row)

    def test_both_wrong_grant_or_heal_even_if_equal_rejected(self):
        for index,changes in ((0,{"item_delta":0}),(7,{"health":75.0}),(3,{"available_after_pickup":False})):
            row=copy.deepcopy(self.report)
            for side in ("python","blueprint"):row["cases"][index][side].update(changes)
            with self.assertRaises(RuntimeError):contract.validate(row)

    def test_cleanup_identity_and_native_message_required(self):
        for mutate in (lambda r:r.update(message_scope_closed=False),lambda r:r.update(actors_destroyed=17),
                       lambda r:r["player_restore"].update(inventory_identity_equal=False),
                       lambda r:r["cases"][3]["python"].update(failure_owner_matches=False)):
            row=copy.deepcopy(self.report);mutate(row)
            with self.assertRaises(RuntimeError):contract.validate(row)

    def test_replay_or_profile_bypass_rejected(self):
        for mutate in (lambda r:r.update(give_weapon_called_by_probe=True),lambda r:r["cases"][1]["python_counters"].update(weapon_gives=0)):
            row=copy.deepcopy(self.report);mutate(row)
            with self.assertRaises(RuntimeError):contract.validate(row)

    def test_fixture_parses_and_base_import_does_not_start_another_ticker(self):
        scripts=ROOT/"Overlay/Content/Scripts/uep_lyra_world"
        ast.parse((scripts/"spawner_validation.py").read_text(encoding="utf-8"))
        tree=ast.parse((scripts/"inventory_pad_player_validation.py").read_text(encoding="utf-8"))
        guard=ast.Expression(tree.body[-1].test)
        self.assertFalse(eval(compile(guard,"guard","eval"),{"sys":type("Args",(),{"argv":["-UEPSpawnerResult=result.json"]})()}))
