"""Network evidence must come from native prediction, RPC payloads and replicas."""
import copy
import unittest
from uep_lyra_weapons import weapon_ability_fire_network_contract as policy


def ident(value,role):return dict(valid=True,transport="Legacy",wire_id=str(value),local_role=role)
def reports():
    def common(peer,mode):
        value=dict(status="passed",error=None,peer=peer,native_mode=mode,network_acceptance=True,observation_errors=[],observers_restored=True,cases=[],weapon="pistol",original_inventory_restored=True)
        value.update({name:False for name in policy.FALSE});return value
    server=common("server","DedicatedServer");server.update(server_waited_for_client_process_exit=True,player_ids=dict(A=1,B0=2))
    clients={peer:common(peer,"Client") for peer in policy.PEERS}
    for peer,value in clients.items():value.update(player_id=server["player_ids"][peer],control_rotation_restored=True)
    for position,(owner,profile) in enumerate(policy.PLAN):
        source=ident(10+policy.PEERS.index(owner),3);target=ident(30+position,3);prediction=position+1;point=[100.,200.,50.]
        activation=dict(authority=True,mode=0,locally_controlled=False,prediction_key=prediction,source=source)
        data=dict(authority=True,target_hits=1,count=1,prediction_key=prediction,source=source,hit_identities=[["Legacy",target["wire_id"]]],points=[point])
        row=dict(position=position,owner=owner,profile=profile,native_class=policy.WEAPONS["pistol"],ammo_before=6,ammo_after=5,health_before=100.,health_after=82.,
            activations=[activation],target_data=[data],ability_ended=True,source_identity=source,target_identity=target,human_health_after=dict(A=100.,B0=100.))
        server["cases"].append(row)
        for peer,value in clients.items():
            predicted=peer==owner;local_source=ident(source["wire_id"],2 if predicted else 1)
            local_activation=dict(authority=False,mode=2,locally_controlled=True,prediction_key=prediction,source=local_source)
            local_data=copy.deepcopy(data);local_data.update(authority=False,source=local_source)
            value["cases"].append(dict(position=position,owner=owner,profile=profile,source_identity=local_source,target_identity=ident(target["wire_id"],1),health_after=82.,
                human_health_unchanged=True,quiet_ticks=6,weapon_fire_entries=1,input_gestures=int(predicted),input_released=True,activations=[local_activation] if predicted else [],
                target_data=[local_data] if predicted else [],ability_ended=True,ammo_before=6,ammo_after=5 if predicted else 6))
    return server,clients


class TestWeaponFireNetworkContract(unittest.TestCase):
    def setUp(self):self.server,self.clients=reports()
    def rejected(self):
        with self.assertRaises(RuntimeError):policy.validate(self.server,self.clients)
    def test_complete_actual_network_evidence(self):self.assertEqual(policy.validate(self.server,self.clients)["native_prediction_key_pairs"],4)
    def test_server_replays_activation(self):self.server["authority_activation_requested_by_fixture"]=True;self.rejected()
    def test_server_targets_locally(self):self.server["cases"][0]["activations"][0]["locally_controlled"]=True;self.rejected()
    def test_owner_not_predicting(self):self.clients["A"]["cases"][0]["activations"][0]["mode"]=0;self.rejected()
    def test_owner_wrong_role(self):self.clients["A"]["cases"][0]["activations"][0]["source"]["local_role"]=1;self.rejected()
    def test_prediction_key_not_native_pair(self):self.clients["A"]["cases"][0]["activations"][0]["prediction_key"]=999;self.rejected()
    def test_target_data_rpc_key_differs(self):self.clients["A"]["cases"][0]["target_data"][0]["prediction_key"]=999;self.rejected()
    def test_client_applies_authority_damage(self):self.clients["A"]["cases"][0]["target_data"][0]["authority"]=True;self.rejected()
    def test_target_data_actor_payload_differs(self):self.clients["A"]["cases"][0]["target_data"][0]["hit_identities"]=[["Legacy","999"]];self.rejected()
    def test_target_data_point_differs_beyond_native_quantization(self):self.clients["A"]["cases"][0]["target_data"][0]["points"]=[[105.,200.,50.]];self.rejected()
    def test_native_half_centimeter_quantization_allowed(self):self.clients["A"]["cases"][0]["target_data"][0]["points"]=[[100.49,200.,50.]];policy.validate(self.server,self.clients)
    def test_native_target_wire_mismatch(self):self.clients["B0"]["cases"][0]["target_identity"]["wire_id"]="999";self.rejected()
    def test_native_source_wire_mismatch(self):self.clients["B0"]["cases"][0]["source_identity"]["wire_id"]="999";self.rejected()
    def test_owner_ammo_not_replicated(self):self.clients["A"]["cases"][0]["ammo_after"]=6;self.rejected()
    def test_source_cost_not_native(self):self.server["cases"][0]["ammo_after"]=6;self.rejected()
    def test_no_positive_native_damage(self):self.server["cases"][0]["health_after"]=100.;self.rejected()
    def test_remote_health_not_replicated(self):self.clients["B0"]["cases"][0]["health_after"]=100.;self.rejected()
    def test_remote_cue_missing(self):self.clients["B0"]["cases"][0]["weapon_fire_entries"]=0;self.rejected()
    def test_owner_predicted_cue_duplicated(self):self.clients["A"]["cases"][0]["weapon_fire_entries"]=2;self.rejected()
    def test_foreign_owner_activates_ability(self):self.clients["B0"]["cases"][0]["activations"]=[{}];self.rejected()
    def test_unrelated_human_damage(self):self.server["cases"][0]["human_health_after"]["B0"]=90.;self.rejected()
    def test_server_did_not_wait_actual_exits(self):self.server["server_waited_for_client_process_exit"]=False;self.rejected()
    def test_health_repair_rejected(self):self.server["asc_binding_repaired"]=True;self.rejected()
    def test_client_inventory_write_rejected(self):self.clients["A"]["client_inventory_written"]=True;self.rejected()
    def test_state_delivered_by_file_rejected(self):self.clients["A"]["gameplay_state_delivered_by_files"]=True;self.rejected()
    def test_command_stages_do_not_repeat(self):self.assertFalse(policy.accept_command(dict(position=0,stage="prepare"),-1,(0,"prepare")))
    def test_completed_position_does_not_restart(self):self.assertFalse(policy.accept_command(dict(position=0,stage="fire"),0,(0,"prepare")))
    def test_complete_command_has_terminal_position(self):self.assertTrue(policy.accept_command(dict(position=4,stage="complete"),3,(3,"fire")))
    def test_invalid_command_stage_rejected(self):
        with self.assertRaises(RuntimeError):policy.accept_command(dict(position=0,stage="set-health"),-1,None)
    def test_native_static_actor_guid_used_when_owner_has_no_wire_id(self):
        a=dict(count=1,hit_identities=[None],hit_identity_details=[dict(wire=None,replicated=False,static_guid="0123456789ABCDEF0123456789ABCDEF")])
        b=dict(count=1,hit_identities=[["Legacy","299"]],hit_identity_details=[dict(wire=["Legacy","299"],replicated=False,static_guid="0123456789ABCDEF0123456789ABCDEF")])
        self.assertTrue(policy.same_hits(a,b))
    def test_unidentified_static_actor_cannot_be_matched_by_position(self):
        a=dict(count=1,hit_identities=[None],hit_identity_details=[dict(wire=None,replicated=False,static_guid=None)])
        self.assertFalse(policy.same_hits(a,a))
    def test_replicated_actor_requires_actual_wire_identity(self):
        a=dict(count=1,hit_identities=[None],hit_identity_details=[dict(wire=None,replicated=True,static_guid="0123")])
        self.assertFalse(policy.same_hits(a,a))
    def test_new_pose_attempt_can_reenter_native_prepare(self):self.assertTrue(policy.accept_command(dict(position=0,stage="prepare",attempt=1),-1,(0,"prepare",0)))
