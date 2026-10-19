"""Reject fabricated prediction, owner spawns, mismatched wires and weak motion."""
import copy
import unittest
from uep_lyra_weapons.netshooter_network_contract import PLAN,PEERS,FALSE,validate,accept_command


def identity(number,role):return dict(valid=True,transport="Legacy",wire_id=str(number),local_role=role)


def reports():
    server=dict(status="passed",error=None,native_mode="DedicatedServer",network_acceptance=True,cases=[],observation_errors=[],observers_restored=True,original_inventory_restored=True,
        player_ids={"A":100,"B0":101},server_waited_for_client_process_exit=True,original_native_pose_movement_restored=True)
    clients={peer:dict(status="passed",error=None,native_mode="Client",network_acceptance=True,cases=[],observation_errors=[],observers_restored=True,original_inventory_restored=True,player_id=server["player_ids"][peer],control_rotation_restored=True) for peer in PEERS}
    for report in [server,*clients.values()]:
        for field in FALSE+("projectile_spawn_requested_by_fixture","impact_or_strand_replication_accepted","projectile_physics_written"):report[field]=False
    for position,(owner,profile) in enumerate(PLAN):
        key=position+1;row=dict(position=position,owner=owner,profile=profile,source_identity=identity(10+PEERS.index(owner),3),projectile_identity=identity(100+position,3),
            projectile_replicates=True,projectile_replicates_movement=True,native_moving_samples=4,distance_moved=300.,natural_hit_entries=0,projectile_destruction_observed=True,human_health_unchanged=True,
            activations=[dict(profile=profile,authority=True,mode=0,locally_controlled=False,native_spawn_delta=1,prediction_key=key)],target_data=[dict(authority=True,prediction_key=key,count=1)],
            ability_ended=True,ammo_before=8,ammo_after=7,parent_target_data_calls=0,authority_fixture_cleanup=True,native_aim_sync=True)
        server["cases"].append(row)
        for peer in PEERS:
            replica=copy.deepcopy(row);replica.update(projectile_identity=identity(100+position,1),weapon_fire_entries=1,input_gestures=int(peer==owner),input_released=True)
            if peer==owner:
                replica["activations"][0].update(authority=False,mode=2,locally_controlled=True,native_spawn_delta=0);replica["target_data"][0]["authority"]=False
            else:replica.update(activations=[],target_data=[],ammo_after=8)
            clients[peer]["cases"].append(replica)
    return server,clients


class TestNetShooterNetworkContract(unittest.TestCase):
    def test_native_two_owner_preimpact_matrix_passes(self):
        self.assertEqual(validate(*reports())["native_moving_replica_observations"],8)
    def test_predicted_owner_key_mode_or_local_spawn_mismatch_rejected(self):
        for key,value in (("prediction_key",99),("mode",0),("native_spawn_delta",1),("locally_controlled",False),("profile","Python")):
            server,clients=reports();clients["A"]["cases"][0]["activations"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_authority_must_follow_actual_remote_prediction(self):
        for key,value in (("authority",False),("locally_controlled",True),("native_spawn_delta",0),("prediction_key",0)):
            server,clients=reports();server["cases"][0]["activations"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_native_wire_identity_and_simulated_proxy_role_required(self):
        for key,value in (("wire_id","999"),("local_role",2),("valid",False)):
            server,clients=reports();clients["B0"]["cases"][0]["projectile_identity"][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_reused_projectile_identity_cannot_substitute_for_four_spawns(self):
        server,clients=reports();server["cases"][1]["projectile_identity"]["wire_id"]=server["cases"][0]["projectile_identity"]["wire_id"]
        for report in clients.values():report["cases"][1]["projectile_identity"]["wire_id"]=server["cases"][0]["projectile_identity"]["wire_id"]
        with self.assertRaises(RuntimeError):validate(server,clients)
    def test_real_motion_and_no_impact_boundary_required(self):
        for key,value in (("native_moving_samples",2),("distance_moved",99.),("natural_hit_entries",1),("projectile_replicates_movement",False),("projectile_destruction_observed",False),("human_health_unchanged",False)):
            server,clients=reports();clients["A"]["cases"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_native_cost_and_empty_target_data_and_cue_required(self):
        for key,value in (("ammo_after",8),("parent_target_data_calls",1),("weapon_fire_entries",0)):
            server,clients=reports();clients["A"]["cases"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_foreign_client_cannot_activate_or_consume_ammo(self):
        for key,value in (("input_gestures",1),("ammo_after",7),("activations",[{}])):
            server,clients=reports();clients["B0"]["cases"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_scope_cannot_claim_impact_physics_writes_or_fixture_spawn(self):
        for key in ("impact_or_strand_replication_accepted","projectile_physics_written","projectile_spawn_requested_by_fixture","gameplay_state_delivered_by_files","authority_activation_requested_by_fixture","full_acceptance"):
            server,clients=reports();server[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_incomplete_owner_matrix_and_native_cleanup_rejected(self):
        server,clients=reports();server["cases"].pop()
        with self.assertRaises(RuntimeError):validate(server,clients)
        server,clients=reports();server["original_native_pose_movement_restored"]=False
        with self.assertRaises(RuntimeError):validate(server,clients)
    def test_schedule_deduplicates_without_delivering_gameplay_state(self):
        command=dict(position=0,stage="prepare")
        self.assertTrue(accept_command(command,-1,None));self.assertFalse(accept_command(command,-1,(0,"prepare",0)))
        self.assertFalse(accept_command(command,0,None))
        with self.assertRaises(RuntimeError):accept_command(dict(position=0,stage="set-client-state"),-1,None)
