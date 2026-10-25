import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_weapons import netshooter_ammo_contract as gate
from test_netshooter_ability_contract import report as ability_report
from test_netshooter_network_contract import reports as network_reports


def config():return [dict(native_class='/Script/LyraGame.LyraAbilityCost_ItemTagStack',tag=gate.MAGAZINE,failure_tag=gate.COST,quantity=1.)]
def failures():return [dict(native_ability='/Native/Ability',native_class=gate.CLASS,tags=[gate.COST])]


def standalone():
    value=ability_report();value.update(native_cost_configuration=config(),failure_observer_restored=True,production_cue_binding_preserved=True)
    value['cases']=[]
    for profile in ('BlueprintFallback','Python'):
        shot=dict(activations=1,target_data=1,projectiles=1,callbacks=['OnCompleted'])
        value['cases'].append(dict(profile=profile,native_selected_profile=profile,native_autoreload_grant_count_before=0,
            native_autoreload_grant_count=0,input_gestures=2,input_released=True,ammo_before=1,ammo_after_last_round=0,
            ammo_after_empty_attempt=0,first_shot=shot,after_empty=copy.deepcopy(shot),native_failure_events=failures(),ability_ended=True,
            policy_activations=dict(activations=int(profile=='Python'),fallback_activations=int(profile=='BlueprintFallback'))))
    return value


def network():
    server,clients=network_reports()
    for value in [server,*clients.values()]:value.update(native_cost_configuration=config(),failure_observer_restored=True,ammo_exhaustion_only=True)
    for index,(owner,profile) in enumerate(gate.PLAN):
        probe=dict(owner=owner,profile=profile,ammo_after=0,native_failure_events=failures(),activations=1,target_data=1,
            input_gestures=2,input_released=True,native_autoreload_grant_count=0)
        server['cases'][index].update(ammo_before=1,ammo_after=0,native_autoreload_grant_count=0,empty_probe=copy.deepcopy(probe))
        for peer in gate.PEERS:
            row=clients[peer]['cases'][index];row['native_autoreload_grant_count']=0
            if peer==owner:row.update(ammo_before=1,ammo_after=0,input_gestures=2,empty_probe=copy.deepcopy(probe))
    return server,clients


class NetShooterAmmoGateTests(unittest.TestCase):
    def test_both_actual_standalone_profiles_and_two_native_owners(self):
        self.assertEqual(gate.validate_standalone(standalone())['native_empty_cost_refusals'],2)
        self.assertEqual(gate.validate_network(*network())['native_empty_cost_refusals'],4)

    def test_no_second_shot_without_native_cost_failure_is_insufficient(self):
        for events in ([],[dict(native_ability='/Native/Ability',native_class=gate.CLASS,tags=['Ability.ActivateFail.TagsBlocked'])]):
            value=standalone();value['cases'][0]['native_failure_events']=events
            with self.subTest(events=events),self.assertRaises(RuntimeError):gate.validate_standalone(value)

    def test_empty_attempt_must_not_activate_or_spawn_or_consume_again(self):
        for key,replacement in (('activations',2),('target_data',2),('projectiles',2)):
            value=standalone();value['cases'][1]['after_empty'][key]=replacement
            with self.subTest(key=key),self.assertRaises(RuntimeError):gate.validate_standalone(value)
        value=standalone();value['cases'][1]['ammo_after_empty_attempt']=-1
        with self.assertRaises(RuntimeError):gate.validate_standalone(value)

    def test_native_grant_cost_configuration_and_profile_cannot_be_replaced(self):
        for key,value in (('native_autoreload_grant_count',1),('native_selected_profile','Python'),('input_gestures',1)):
            report=standalone();report['cases'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):gate.validate_standalone(report)
        report=standalone();report['native_cost_configuration'][0]['quantity']=0.
        with self.assertRaises(RuntimeError):gate.validate_standalone(report)

    def test_observer_and_original_inventory_cleanup_are_required(self):
        for key in ('failure_observer_restored','original_inventory_restored','production_profiles_restored','production_cue_binding_preserved'):
            value=standalone();value[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):gate.validate_standalone(value)

    def test_owner_ack_cannot_replace_the_independent_native_owner_capture(self):
        server,clients=network();server['cases'][0]['empty_probe']['ammo_after']=1
        with self.assertRaises(RuntimeError):gate.validate_network(server,clients)

    def test_first_shot_projection_keeps_the_actual_two_gesture_reports_unchanged(self):
        server,clients=network();before=copy.deepcopy((server,clients))
        gate.validate_network(server,clients)
        self.assertEqual((server,clients),before)
        self.assertEqual(clients['A']['cases'][0]['input_gestures'],2)

    def test_new_empty_gate_keeps_original_prediction_and_foreign_owner_checks(self):
        server,clients=network();clients['A']['cases'][0]['activations'][0]['prediction_key']=0
        with self.assertRaises(RuntimeError):gate.validate_network(server,clients)
        server,clients=network();clients['B0']['cases'][0]['input_gestures']=1
        with self.assertRaises(RuntimeError):gate.validate_network(server,clients)

    def test_network_missing_cost_callback_or_synthetic_autoreload_is_rejected(self):
        for key,value in (('native_failure_events',[]),('native_autoreload_grant_count',1)):
            server,clients=network();clients['A']['cases'][0]['empty_probe'][key]=value
            server['cases'][0]['empty_probe']=copy.deepcopy(clients['A']['cases'][0]['empty_probe'])
            with self.subTest(key=key),self.assertRaises(RuntimeError):gate.validate_network(server,clients)
