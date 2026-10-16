"""Adversarial network matrices and startup isolation, not native peer proof."""
import ast
import copy
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"Overlay/Content/Scripts"))
from uep_lyra_world.spawner_network_protocol import PLAN,PEERS,CASES,expected_inventory,validate_cases
from uep_lyra_hud.startup import validation_module

def inventory(rifles=0,active=0,spare=60):
    items=["Pistol"]+["Rifle"]*rifles
    return {"items":items,"slots":items+[None]*(3-len(items)),"active":active,"definition":"Rifle" if active else "Pistol",
        "magazine":30 if active else 12,"spare":spare if active else 48,"equipment_class":"Rifle" if active else "Pistol",
        "equipment_instigator_matches":True}

class SpawnerNetworkGate(unittest.TestCase):
    def setUp(self):
        self.rows=[]
        for index,(target,name,profile) in enumerate(PLAN):
            kind=CASES.index(name);original={peer:inventory() for peer in PEERS}
            prepared=copy.deepcopy(original)
            if kind in (2,3,6):prepared[target]=inventory(1,1,55 if kind==2 else 60)
            if kind==1:prepared[target]=inventory(2)
            expected=copy.deepcopy(prepared)
            if kind in (0,4,5):expected[target]=inventory(1,int(kind!=4))
            if kind==6:expected[target]=inventory(2,2)
            if kind==2:expected[target]["spare"]=60
            row={"run_id":"run","case_index":index,"target":target,"scenario":name,"profile":profile,"pad_name":"pad","pad_class":"Spawner",
                "pad_replicates":True,"original":original,"prepared":prepared,"expected":expected,
                "prepared_health":{peer:75.0 if kind==7 and peer==target else 100.0 for peer in PEERS},
                "expected_health":{peer:100.0 for peer in PEERS},"original_health":{peer:100.0 for peer in PEERS},
                "roster":{peer:{"player_id":number} for number,peer in enumerate(PEERS)},
                "client_pawns":{peer:"pawn-"+peer for peer in PEERS},"client_worlds":{peer:"world-"+peer for peer in PEERS},
                "success":kind not in (1,3,8),"physical_events":["begin","end"],"fixture_scope_closed":True,
                "original_level_actor_preserved":True,"cooldown_duration":10.0,"cooldown_seconds":10.01,
                "python_gives":int(profile=="Python"),"fallback_gives":int(profile=="BlueprintFallback"),
                "python_failures":int(profile=="Python" and kind==3),"acks":{}}
            row["after"]={peer:expected_inventory(row,peer) for peer in PEERS}
            for stage in ("prepared","observed","restored"):
                row["acks"][stage]={}
                for number,peer in enumerate(PEERS):
                    health=(row["prepared_health"] if stage=="prepared" else row["expected_health"])[peer]
                    available=not row["success"] if stage=="observed" else True
                    row["acks"][stage][peer]={"run_id":"run","case_index":index,"peer":peer,"stage":stage,
                        "player":{"player_id":number,"pawn_path":"pawn-"+peer,"world_token":"world-"+peer,"health":health,"max_health":100.0},
                        "inventory":copy.deepcopy(prepared[peer] if stage=="prepared" else original[peer] if stage=="restored" else row["after"][peer]),
                        "health_visual":{"number":health,"target":health,"ratio":health/100.0},
                        "pad":{"name":"pad","class":"Spawner","profile":profile,"available":available,"light":available,"weapon_visible":available},
                        "input_frames":int(stage=="observed" and kind==0 and peer==target),
                        "failure_delta":int(stage=="observed" and kind==3 and peer==target),"failure_text":"Spare Ammo Full"}
            self.rows.append(row)

    def test_complete_original_level_actor_matrix(self):
        self.assertEqual(len(PLAN),36)
        self.assertTrue(validate_cases(self.rows))

    def test_wrong_owner_inventory_or_hud_rejected(self):
        for mutate in (lambda r:r[0]["acks"]["observed"]["A"]["player"].update(player_id=99),
                       lambda r:r[0]["acks"]["observed"]["B0"]["inventory"].update(spare=1),
                       lambda r:r[0]["acks"]["observed"]["A"]["health_visual"].update(ratio=.75)):
            rows=copy.deepcopy(self.rows);mutate(rows)
            with self.assertRaises(RuntimeError):validate_cases(rows)

    def test_short_timer_replayed_failure_or_replaced_actor_rejected(self):
        for mutate in (lambda r:r[0].update(cooldown_seconds=.5),lambda r:r[0].update(original_level_actor_preserved=False),
                       lambda r:r[7]["acks"]["observed"]["A"].update(failure_delta=2),
                       lambda r:r[1].update(python_gives=0)):
            rows=copy.deepcopy(self.rows);mutate(rows)
            with self.assertRaises(RuntimeError):validate_cases(rows)

    def test_missing_availability_restore_or_wrong_fire_rejected(self):
        for mutate in (lambda r:r[0]["acks"]["restored"]["B0"]["pad"].update(available=False),
                       lambda r:r[0]["acks"]["observed"]["A"].update(input_frames=0),
                       lambda r:r[0].update(physical_events=["begin"])):
            rows=copy.deepcopy(self.rows);mutate(rows)
            with self.assertRaises(RuntimeError):validate_cases(rows)

    def test_exclusive_import_guards(self):
        self.assertEqual(validation_module(["-UEPSpawnerNetwork","-UEPLyraMultiClient"]),"uep_lyra_world.spawner_network_validation")
        for relative in ("uep_lyra_network.py","uep_lyra_world/effect_pad_network_validation.py","uep_lyra_world/inventory_pad_network_validation.py"):
            tree=ast.parse((ROOT/"Overlay/Content/Scripts"/relative).read_text(encoding="utf-8"))
            self.assertFalse(eval(compile(ast.Expression(tree.body[-1].test),"guard","eval"),{"sys":types.SimpleNamespace(argv=["-UEPSpawnerNetwork"])}))

    def test_runtime_parses_without_destroying_original_level_actors(self):
        source=(ROOT/"Overlay/Content/Scripts/uep_lyra_world/spawner_network_validation.py").read_text(encoding="utf-8")
        tree=ast.parse(source)
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=="actor_destroy" for n in ast.walk(tree)))
