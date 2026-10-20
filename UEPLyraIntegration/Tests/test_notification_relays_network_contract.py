"""Reject fake transport, nonowner leakage, dropped payload fields and DS UI."""
import copy
import unittest
from uep_lyra_hud.notification_relays_network_contract import PEERS,PLAN,FALSE,selected,validate,wire_key


def reports():
    roster={p:dict(player_id=i+1,state_wire=['Legacy',str(i+1)]) for i,p in enumerate(PEERS)}
    all_reports={}
    for peer in ('server',*PEERS):
        r=dict(status='passed',error=None,native_mode='DedicatedServer' if peer=='server' else 'Client',network_acceptance=True,run_id='run',peer=peer,cases=[],server_waited_for_client_process_exit=peer=='server',roster=roster,player_id=roster[peer]['player_id'] if peer!='server' else None,native_relay_counts=dict(kill=1,award=1),callbacks_bound_once_native=True,**{k:False for k in FALSE})
        for k in ('observer_scopes_closed','profile_overrides_cleared','profile_classes_restored','probe_roots_removed','original_scores_restored','target_score_restored'):r[k]=True
        all_reports[peer]=r
    for index,(kind,source,typ,profile) in enumerate(PLAN):
        payload=dict(kind='kill' if kind=='kill' else 'award',verb=kind,instigator=roster[source]['state_wire'] if source else None,magnitude=17.25)
        command=dict(index=index,kind=kind,source_peer=source,source_type=typ,profile=profile,expected_payload=payload,expected_kill=dict(attacker='a',attackee='b'),expected_award=dict(player=roster[source]['state_wire'] if source else None,payload_tag='award'))
        for peer,r in all_reports.items():
            server=peer=='server';delivery=kind!='parent' if server else selected(command,peer);label='kill' if kind=='kill' else 'award'
            row=dict(index=index,profile=profile,entries=dict(kill=int(delivery and label=='kill'),award=int(delivery and label=='award')),receipts=[copy.deepcopy(payload)] if delivery else [],kill_notifications=[] if server or not delivery or label!='kill' else [copy.deepcopy(command['expected_kill'])],award_notifications=[] if server or not delivery or label!='award' else [copy.deepcopy(command['expected_award'])],side_effects=dict(multicast_requests=int(server and profile=='Python' and kind=='kill'),client_requests=int(server and profile=='Python' and kind=='award'),cosmetic_broadcasts=int(not server and profile=='Python' and delivery)),health_unchanged=True,diagnostic_fallbacks=0,observation_seconds=1.1)
            if server:row['command']=copy.deepcopy(command)
            r['cases'].append(row)
    return all_reports


def check(r):return validate(r['server'],{p:r[p] for p in PEERS})


class NetworkRelayContractTests(unittest.TestCase):
    def test_complete_actual_role_matrix(self):self.assertEqual(check(reports())['client_observation_cases'],20)
    def test_nonowner_must_not_receive_owner_only_notification(self):
        r=reports();r['B0']['cases'][1]['entries']['award']=1
        with self.assertRaises(RuntimeError):check(r)
    def test_both_clients_must_receive_reliable_kill_feed(self):
        r=reports();r['B0']['cases'][0]['kill_notifications']=[]
        with self.assertRaises(RuntimeError):check(r)
    def test_native_payload_and_wire_reference_must_be_preserved(self):
        for field,value in (('instigator',['Legacy','999']),('magnitude',0.),('verb','rewritten')):
            r=reports();r['A']['cases'][0]['receipts'][0][field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):check(r)
    def test_dedicated_server_must_not_execute_ui(self):
        r=reports();r['server']['cases'][0]['kill_notifications']=[{'fake':True}]
        with self.assertRaises(RuntimeError):check(r)
    def test_remote_client_must_not_forward_again(self):
        r=reports();r['A']['cases'][4]['side_effects']['multicast_requests']=1
        with self.assertRaises(RuntimeError):check(r)
    def test_null_source_and_parent_channel_have_real_negative_windows(self):
        for index in (8,9):
            r=reports();r['A']['cases'][index]['observation_seconds']=0.
            with self.subTest(index=index),self.assertRaises(RuntimeError):check(r)
    def test_native_wire_ids_cannot_be_local_paths_or_floats(self):
        for value in (['Legacy',1],['Legacy','0'],['Legacy','/Game/Actor'],['Iris','1']):
            with self.subTest(value=value),self.assertRaises(RuntimeError):wire_key(value)
    def test_two_actual_owners_and_exit_barrier_required(self):
        r=reports();r['server']['roster']['B0']['state_wire']=['Legacy','1']
        with self.assertRaises(RuntimeError):check(r)
        r=reports();r['server']['server_waited_for_client_process_exit']=False
        with self.assertRaises(RuntimeError):check(r)
    def test_no_client_message_synthesis_rpc_replacement_or_replay(self):
        for key in ('client_fixture_broadcasts','native_rpc_implementation_replaced','callbacks_replayed'):
            r=reports();r['A'][key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):check(r)
