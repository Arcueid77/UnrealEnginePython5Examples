"""Counterexample models for actual two-owner evidence,not native networking."""
import ast
import copy
from pathlib import Path
import unittest
from uep_lyra_abilities.grenade_activation_network_contract import CLASS,PROJECTILE,PLAN,PEERS,FALSE,validate,expected,accept_command


def identity(number,role): return dict(valid=True,transport="Legacy",wire_id=str(number),local_role=role)
def event(profile,authority,number):
    py=profile=="Python";row=dict(profile=profile,native_callback_count=1,native_role=3 if authority else 2,native_authority=authority,
        native_cost_ready=True,native_cooldown_ready=True,montage_continues_after_end=True,active_after=False,tasks_after=0,pawn="pawn"+str(number),
        cooldown=5.,native_cooldown=5. if authority else 0.,cooldown_before=5.,native_confirmed_cooldown_before_repeat=4.9,native_request_accepted=True,native_repeat_rejected=True,source_identity=identity(number,3 if authority else 2),
        before=dict(activation_mode=0 if authority else 2,actor_location=[0.,0.,0.],forward=[1.,0.,0.],up=[0.,0.,1.],control=[0.,0.,0.],trace=dict(hit=False,distance=0.,end=[100.,0.,25.],location=[0.,0.,0.])))
    row["location"],row["direction"]=expected(row)
    row["projectiles"]=[dict(**{"class":PROJECTILE},instigator=row["pawn"],owner=None,location=row["location"],rotation=row["direction"],scale=[1.,1.,1.])] if authority else []
    row["messages"]=[dict(channel="Ability.Grenade.Duration.Message",instigator=row["pawn"],duration=5.,native_active=True,native_montage_task_count=1)]
    row["stats"]=dict(python_calls=int(py),fallback_calls=int(not py),cost_checks=int(py),cooldown_checks=int(py),commits=int(py),denied=0,aim_queries=int(py),
        near_control_rotation=int(py),hit_aim=0,miss_aim=0,projectiles=int(py and authority),cooldown_writes=int(py and authority),montage_tasks=int(py),duration_messages=int(py),native_ends=int(py),invalid_receiver_defaults=0)
    return row


def source(number,own):
    role=2 if own else 1;binding=dict(role=role,health=100.,death_state=0,destroying=False,health_set="set",actor="pawn",player_state_pawn="pawn",
        actor_asc=dict(avatar="pawn",object="asc"),health_asc=dict(object="asc"),network_identity=identity(number,role))
    return dict(network_identity=identity(number,role),source_role=role,healthy_bound=True,binding=binding)


def model():
    def base(mode,peer):
        row=dict(status="passed",error=None,native_mode=mode,peer=peer,run_id="run",cases=[],observation_errors=[],network_acceptance=True,
            listener_closed=True,observers_restored=True,remaining_test_projectiles=0,native_class=CLASS)
        row.update({key:False for key in FALSE});return row
    viewers={peer:base("Client",peer) for peer in PEERS};server=base("DedicatedServer","server")
    server.update(player_ids=dict(A=1,B0=2),server_waited_for_client_process_exit=True,native_pre_release_cleanup={})
    for peer,value in viewers.items():
        value.update(player_id=server["player_ids"][peer],native_role=2,original_handles=[1],profile_restored=True,specs_preserved=True,handles_preserved=True,config_preserved=True,ui_preserved=True)
        server["native_pre_release_cleanup"][peer]=dict(native_asc_alive=True,profile_restored=True,specs_preserved=True,handles_preserved=True,config_preserved=True,original_handles=[1],current_handles=[1])
    for index,(owner,profile) in enumerate(PLAN):
        number=100+index;row=dict(position=index,owner=owner,profile=profile,native_reset_requests=1,quiet_ticks=20,all_pawn_health_unchanged=True,
            native_nonlocal_owner=True,native_ui_invalid=True,source_identity=identity(number,3),old_identity=identity(number+1000,3),activation=event(profile,True,number),prepared={},viewers={})
        for peer in PEERS:
            own=owner==peer;row["prepared"][peer]=dict(own=own,**source(number,own))
            observed=dict(position=index,owner=owner,profile=profile,own=own,quiet_ticks=20,source=source(number,own),ui_preserved=True,specs_preserved=True,
                handles_preserved=True,all_pawn_health_unchanged=True,native_montage_completed=True,foreign_owner_untouched=not own,activation=event(profile,False,number) if own else None)
            viewers[peer]["cases"].append(copy.deepcopy(observed));row["viewers"][peer]=observed
        server["cases"].append(row)
    return server,viewers


class TestGrenadeActivationNetworkContract(unittest.TestCase):
    def setUp(self): self.server,self.viewers=model()
    def reject(self):
        with self.assertRaises((RuntimeError,ValueError)): validate(self.server,self.viewers)
    def test_full_model_not_native_acceptance(self): self.assertEqual(validate(self.server,self.viewers)["native_authority_activations"],4)
    def test_real_two_owners(self): self.server["player_ids"]["B0"]=1;self.reject()
    def test_client_actual_mode(self): self.viewers["A"]["native_mode"]="Standalone";self.reject()
    def test_server_last_actual_exit_gate(self): self.server["server_waited_for_client_process_exit"]=False;self.reject()
    def test_no_local_rpc_bypass(self): self.server["native_rpc_bypassed"]=True;self.reject()
    def test_no_raw_health(self): self.server["health_properties_written"]=True;self.reject()
    def test_no_projectile_replication_claim(self): self.server["projectile_replication_tested"]=True;self.reject()
    def test_no_far_field_network_teleport(self): self.viewers["A"]["far_field_teleports"]=True;self.reject()
    def test_client_no_native_projectile_spawn(self): self.viewers["A"]["cases"][0]["activation"]["projectiles"]=[{}];self.reject()
    def test_server_must_spawn(self): self.server["cases"][0]["activation"]["projectiles"]=[];self.reject()
    def test_native_authority_must_be_actual(self): self.server["cases"][0]["activation"]["native_authority"]=False;self.reject()
    def test_client_retains_local_cooldown_property(self): self.viewers["A"]["cases"][0]["activation"]["cooldown_before"]=9.;self.reject()
    def test_client_cannot_write_authority_cooldown(self): self.viewers["A"]["cases"][1]["activation"]["stats"]["cooldown_writes"]=1;self.reject()
    def test_real_prediction_input(self): self.viewers["A"]["cases"][0]["activation"]["native_request_accepted"]=False;self.reject()
    def test_actual_predicting_mode_not_just_role(self): self.viewers["A"]["cases"][0]["activation"]["before"]["activation_mode"]=1;self.reject()
    def test_repeat_requires_real_replica_cooldown(self): self.viewers["A"]["cases"][0]["activation"]["native_confirmed_cooldown_before_repeat"]=0.;self.reject()
    def test_message_before_end(self): self.server["cases"][0]["activation"]["messages"][0]["native_active"]=False;self.reject()
    def test_no_late_callback(self): self.server["cases"][0]["activation"]["native_callback_count"]=2;self.reject()
    def test_same_wrong_numeric_outputs_rejected(self):
        for row in self.server["cases"]: row["activation"]["location"][0]+=20.
        self.reject()
    def test_native_projectile_instigator(self): self.server["cases"][0]["activation"]["projectiles"][0]["instigator"]="PS";self.reject()
    def test_native_no_nan(self): self.server["cases"][0]["activation"]["native_cooldown"]=float("nan");self.reject()
    def test_native_body_profile(self): self.server["cases"][0]["activation"]["profile"]="Python";self.reject()
    def test_preserve_original_spec_before_release(self): self.server["native_pre_release_cleanup"]["A"]["specs_preserved"]=False;self.reject()
    def test_no_dead_asc_after_disconnect_proof(self): self.server["native_pre_release_cleanup"]["A"]["native_asc_alive"]=False;self.reject()
    def test_native_ui_not_local_dedicated(self): self.server["cases"][0]["native_ui_invalid"]=False;self.reject()
    def test_native_foreign_role(self): self.server["cases"][0]["prepared"]["B0"]["source_role"]=2;self.reject()
    def test_actual_network_id_not_local_actor_name(self): self.server["cases"][0]["prepared"]["B0"]["network_identity"]["wire_id"]="other";self.reject()
    def test_no_unbound_canonical_pawn(self): self.server["cases"][0]["prepared"]["B0"]["binding"]["actor_asc"]=None;self.reject()
    def test_native_health_set_required(self): self.server["cases"][0]["prepared"]["B0"]["binding"]["health_set"]=None;self.reject()
    def test_real_new_native_pawn(self): self.server["cases"][0]["old_identity"]=self.server["cases"][0]["source_identity"];self.reject()
    def test_quiet_interval(self): self.viewers["B0"]["cases"][0]["quiet_ticks"]=19;self.reject()
    def test_foreign_ability_not_activated(self): self.viewers["B0"]["cases"][0]["activation"]={};self.reject()
    def test_ack_not_different_from_closed_report(self): self.server["cases"][0]["viewers"]["A"]["ui_preserved"]=False;self.reject()
    def test_actual_rpc_source_only_client(self):
        source=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_activation_network_validation.py").read_text(encoding="utf-8")
        tree=ast.parse(source);server=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=="Server")
        text=ast.get_source_segment(source,server)
        self.assertNotIn('"TryActivateAbilityByClass"',text);self.assertIn('"SendGameplayEventToActor"',text)
        for value in ('"K2_TeleportTo"','set_property("Health"','set_property("Cooldown Time"','call_function("K2_ActivateAbility"'): self.assertNotIn(value,source)
    def test_completed_activate_not_reconsumed_after_done_ack(self): self.assertFalse(accept_command(dict(position=0,stage="activate"),(0,"done"),0))
    def test_completed_prepare_not_reconsumed_after_done_ack(self): self.assertFalse(accept_command(dict(position=0,stage="prepare"),(0,"done"),0))
    def test_older_trial_not_reconsumed(self): self.assertFalse(accept_command(dict(position=0,stage="activate"),(1,"done"),1))
    def test_same_pending_stage_not_reconsumed(self): self.assertFalse(accept_command(dict(position=1,stage="activate"),(1,"activate"),0))
    def test_next_fresh_trial_consumed(self): self.assertTrue(accept_command(dict(position=1,stage="prepare"),(0,"done"),0))
    def test_complete_after_last_trial_consumed(self): self.assertTrue(accept_command(dict(position=4,stage="complete"),(3,"done"),3))
    def test_out_of_range_command_rejected(self):
        with self.assertRaises(RuntimeError): accept_command(dict(position=5,stage="activate"),None,-1)
