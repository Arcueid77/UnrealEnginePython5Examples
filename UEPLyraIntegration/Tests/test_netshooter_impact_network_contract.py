"""Require real native impacts/RPC/wires/life and preserve original defect parity."""
import copy
import unittest
from uep_lyra_weapons.netshooter_impact_network_contract import PEERS,PLAN,FALSE,MESH,MATERIAL,validate


def wire(number,role=0):return dict(valid=number is not None,transport="Legacy",wire_id=str(number) if number is not None else "0",local_role=role)


def component(number,multicast=True):return dict(wire=wire(number),from_native_multicast=multicast,mesh=MESH if multicast else None,material=MATERIAL if multicast else None,collision="OverlapOnlyPawn" if multicast else "BlockAllDynamic",replicated=True)


def reports():
    def common(mode):
        value=dict(status="passed",error=None,native_mode=mode,network_acceptance=True,cases=[],original_template_baseline_fixture_actors=1,native_seed_set_at_actual_hit=True,
            actor_observers_and_selector_restored=True,observers_restored=True,original_inventory_restored=True)
        for name in FALSE+("gameplay_projectile_spawn_requested_by_fixture","projectile_physics_written","life_callback_replayed","impact_or_strand_replication_accepted"):value[name]=False
        return value
    server=common("DedicatedServer");server.update(server_waited_for_client_process_exit=True,original_native_pose_movement_restored=True,native_fixture_colliders_destroyed=True)
    clients={peer:common("Client") for peer in PEERS}
    for client in clients.values():client["control_rotation_restored"]=True
    for position,(owner,profile) in enumerate(PLAN):
        numbers=[1000+position*10+i for i in range(2)];activation=dict(profile=profile,authority=True,mode=0,native_spawn_delta=1,prediction_key=position+1)
        event=dict(profile=profile,source_identity=wire(10+PEERS.index(owner),3),new_components=1,native_geometry_matches=True,sphere_hidden=True)
        row=dict(position=position,owner=owner,profile=profile,activations=[activation],target_data=[dict(authority=True,prediction_key=position+1,count=1)],native_hit_events=[dict(profile=profile,next_native_random=42)],natural_hit_entries=1,
            authority_fixture_cleanup=False,native_delay_elapsed=12.1,projectile_destruction_observed=True,ammo_before=8,ammo_after=7,parent_target_data_calls=0,human_health_unchanged=True,
            native_rpc_events=[copy.deepcopy(event) for _ in numbers],components=[component(number) for number in numbers],projectile_identity=wire(300+position,3),source_identity=wire(10+PEERS.index(owner),3))
        server["cases"].append(row)
        for peer,client in clients.items():
            replica=copy.deepcopy(row);replica.update(projectile_identity=wire(300+position,1),natural_hit_entries=0,components_stable_ticks=6,weapon_fire_entries=1,input_gestures=int(peer==owner),input_released=True)
            replica["components"]=[component(None) for _ in numbers]+[component(number,False) for number in numbers]
            if peer==owner:replica["activations"][0].update(authority=False,mode=2,native_spawn_delta=0);replica["target_data"][0]["authority"]=False
            else:replica.update(activations=[],target_data=[],ammo_after=8)
            client["cases"].append(replica)
    return server,clients


class TestNetShooterImpactNetworkContract(unittest.TestCase):
    def test_native_parity_includes_original_template_defect_without_full_acceptance(self):
        value=validate(*reports());self.assertTrue(value["native_component_state_original_python_parity"]);self.assertFalse(value["full_component_replication_correctness_accepted"])
    def test_real_authority_hit_and_native_twelve_second_life_required(self):
        for key,value in (("natural_hit_entries",0),("native_hit_events",[]),("authority_fixture_cleanup",True),("native_delay_elapsed",1.),("projectile_destruction_observed",False)):
            server,clients=reports();server["cases"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_unmatched_component_wire_identity_rejected(self):
        server,clients=reports();clients["B0"]["cases"][0]["components"][-1]["wire"]=wire(9999)
        with self.assertRaises(RuntimeError):validate(server,clients)
    def test_rpc_count_geometry_hidden_and_actual_profile_required(self):
        for key,value in (("new_components",0),("native_geometry_matches",False),("sphere_hidden",False),("profile","Python")):
            server,clients=reports();clients["A"]["cases"][0]["native_rpc_events"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_python_only_replication_behavior_change_fails_original_comparison(self):
        server,clients=reports();clients["A"]["cases"][1]["components"][-1]["mesh"]=MESH
        with self.assertRaises(RuntimeError):validate(server,clients)
    def test_original_and_python_native_rng_consumption_must_match(self):
        server,clients=reports();server["cases"][1]["native_hit_events"][0]["next_native_random"]=99
        with self.assertRaises(RuntimeError):validate(server,clients)
    def test_true_owner_prediction_and_target_data_required(self):
        for name,value in (("mode",0),("native_spawn_delta",1),("prediction_key",99)):
            server,clients=reports();clients["A"]["cases"][0]["activations"][0][name]=value
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(server,clients)
        server,clients=reports();clients["A"]["cases"][0]["target_data"][0]["count"]=2
        with self.assertRaises(RuntimeError):validate(server,clients)
    def test_foreign_client_cannot_run_hit_business_or_consume_ammo(self):
        for key,value in (("natural_hit_entries",1),("ammo_after",7),("activations",[{}])):
            server,clients=reports();clients["B0"]["cases"][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_missing_original_control_baseline_or_selector_restore_rejected(self):
        for key,value in (("original_template_baseline_fixture_actors",0),("actor_observers_and_selector_restored",False),("original_inventory_restored",False)):
            server,clients=reports();server[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
    def test_no_source_defect_full_acceptance_or_callback_replay_overclaim(self):
        for key in ("impact_or_strand_replication_accepted","full_acceptance","life_callback_replayed","gameplay_projectile_spawn_requested_by_fixture","projectile_physics_written"):
            server,clients=reports();server[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(server,clients)
