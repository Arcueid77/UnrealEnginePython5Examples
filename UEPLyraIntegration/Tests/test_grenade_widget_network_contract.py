"""Network report counterexamples only; model rows do not prove replication."""
import copy
from pathlib import Path
import unittest
from test_grenade_widget_contract import model as single
from uep_lyra_abilities.grenade_widget_network_contract import PEERS,PLAN,client,validate


def model():
    ids=dict(A=256,B0=257);viewers={};templates={row["profile"]:row for row in single()["cases"]}
    for peer in PEERS:
        report=dict(status="passed",error=None,native_mode="Client",native_role=2,peer=peer,player_id=ids[peer],
            owning_player_state=peer+"-state",observation_errors=[],observers_restored=True,test_owned_specs_removed=True,cases=[])
        report.update({field:False for field in ("client_native_give_clear_called","native_give_clear_called_by_fixture","callback_replay","health_properties_written","ability_spec_properties_written","inventory_properties_written","native_ui_pool_written","full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","grenade_throw_projectile_damage_migrated","packet_loss_tested","travel_rejoin_tested")})
        for position,(owner,profile) in enumerate(PLAN):
            own=peer==owner;events=copy.deepcopy(templates[profile]["native_callbacks"]) if own else []
            for event in events: event["owner"]=peer+"-state"
            widgets=[peer+"-original"]+([peer+"-clone"] if own else [])
            waves=[dict(number=number,pawn=peer+owner+str(number),old_pawn=peer+owner+str(number-1),source_role=2 if own else 1,
                health=100.,canonical_bound_asc=True,widgets=widgets,own=own) for number in (1,2)]
            report["cases"].append(dict(position=position,owner=owner,profile=profile,own=own,waves=waves,native_callbacks=events,
                quiet_ticks=20,original_widgets_restored=True,original_specs_restored=True))
        viewers[peer]=report
    server=dict(status="passed",error=None,native_mode="DedicatedServer",player_ids=ids,server_waited_for_client_process_exit=True,
        observers_restored=True,test_owned_specs_removed=True,observation_errors=[],cases=[])
    server.update({field:False for field in ("health_properties_written","callback_replay","native_ui_pool_written","full_acceptance","packaged_runtime","physical_input_tested","packet_loss_tested","travel_rejoin_tested")})
    server["native_pre_release_specs"]={peer:dict(native_asc_alive=True,original_handles=[20+index],current_handles=[20+index],original_specs_restored=True) for index,peer in enumerate(PEERS)}
    for position,(owner,profile) in enumerate(PLAN):
        events=copy.deepcopy(templates[profile]["native_callbacks"])
        for event in events:
            event["owner"]="server-"+owner;event["before"]["valid"]=False;event["after"]["valid"]=False
            if profile=="Python": event["counts"].update(existing_noops=0,nonlocal_noops=2,registrations=0)
        waves=[dict(number=number,pawn=owner+str(number),old_pawn=owner+str(number-1),health=100.,
            viewers={peer:copy.deepcopy(value["cases"][position]["waves"][number-1]) for peer,value in viewers.items()}) for number in (1,2)]
        server["cases"].append(dict(position=position,owner=owner,profile=profile,reset_requests=2,native_locally_controlled=False,
            owning_player_state="server-"+owner,native_callbacks=events,original_specs_restored=True,waves=waves,
            viewers={peer:copy.deepcopy(value["cases"][position]) for peer,value in viewers.items()}))
    return server,viewers


class TestGrenadeWidgetNetworkContract(unittest.TestCase):
    def setUp(self): self.server,self.clients=model()
    def reject(self):
        with self.assertRaises((RuntimeError,ValueError)): validate(self.server,self.clients)
    def add_wire_identity(self):
        probe=dict(valid=False,transport="InvalidObject",wire_id="")
        self.server.update(network_identity_required=True,native_identity_null_probe=probe)
        for value in self.clients.values(): value.update(network_identity_required=True,native_identity_null_probe=probe)
        for position,row in enumerate(self.server["cases"]):
            for index,wave in enumerate(row["waves"]):
                value=str(18446744073709550000+position*4+index*2)
                wave["network_identity"]=dict(valid=True,transport="Legacy",wire_id=value,local_role=3,object_path="server-pawn")
                for peer in PEERS:
                    local=self.clients[peer]["cases"][position]["waves"][index]
                    local["network_identity"]=dict(valid=True,transport="Legacy",wire_id=value,local_role=local["source_role"],object_path=peer+"-pawn")
        self.sync_wire_acks()
    def sync_wire_acks(self):
        for position,row in enumerate(self.server["cases"]):
            for index,wave in enumerate(row["waves"]):
                wave["viewers"]={peer:copy.deepcopy(value["cases"][position]["waves"][index]) for peer,value in self.clients.items()}
            row["viewers"]={peer:copy.deepcopy(value["cases"][position]) for peer,value in self.clients.items()}
    def add_join_stress(self):
        self.add_wire_identity()
        requests=[]
        for peer in PEERS:
            self.clients[peer]["join_reset_stress_requested"]=True
            for number in (1,2):
                requests.append(dict(player_id=self.server["player_ids"][peer],old_actor=peer+str(number),request_number=number,
                    old_network_identity=dict(valid=True,transport="Legacy",wire_id=str(self.server["player_ids"][peer]*10+number),local_role=3),
                    native_reset_class="/Script/LyraGame.LyraGameplayAbility_Reset",native_reset_existing_specs=1,native_reset_callback_delta=1))
        self.server["join_reset_stress"]=dict(enabled=True,completed=True,callback_replay=False,health_or_asc_written=False,
            entry="SendGameplayEventToActor(GameplayEvent.RequestReset)",requests_per_owner=2,requests=requests)
    def test_complete_model(self): self.assertEqual(validate(self.server,self.clients)["native_reset_requests"],8)
    def test_actual_bounded_join_input_model(self): self.add_join_stress();validate(self.server,self.clients)
    def test_join_input_not_simply_enabled_without_exercising(self): self.add_join_stress();self.server["join_reset_stress"]["completed"]=False;self.reject()
    def test_join_input_exact_budget_required(self): self.add_join_stress();self.server["join_reset_stress"]["requests"].pop();self.reject()
    def test_join_input_native_callback_required(self): self.add_join_stress();self.server["join_reset_stress"]["requests"][0]["native_reset_callback_delta"]=0;self.reject()
    def test_join_input_existing_native_spec_required(self): self.add_join_stress();self.server["join_reset_stress"]["requests"][1]["native_reset_existing_specs"]=0;self.reject()
    def test_join_input_native_class_not_python_callback(self): self.add_join_stress();self.server["join_reset_stress"]["requests"][0]["native_reset_class"]="fake";self.reject()
    def test_join_input_not_state_repair(self): self.add_join_stress();self.server["join_reset_stress"]["health_or_asc_written"]=True;self.reject()
    def test_join_input_never_client_authority(self): self.add_join_stress();self.server["join_reset_stress"]["requests"][0]["old_network_identity"]["local_role"]=2;self.reject()
    def test_wire_ids_match_across_different_local_actor_paths(self): self.add_wire_identity();validate(self.server,self.clients)
    def test_same_player_and_health_do_not_replace_wire_identity_proof(self):
        self.add_wire_identity();self.clients["B0"]["cases"][0]["waves"][0]["network_identity"]["wire_id"]="999";self.sync_wire_acks();self.reject()
    def test_wire_namespace_transport_matches(self):
        self.add_wire_identity();self.clients["A"]["cases"][0]["waves"][0]["network_identity"]["transport"]="Iris";self.sync_wire_acks();self.reject()
    def test_no_float_wire_identity(self):
        self.add_wire_identity();self.clients["A"]["cases"][0]["waves"][0]["network_identity"]["wire_id"]=18446744073709550000.;self.sync_wire_acks();self.reject()
    def test_no_unassigned_wire_identity(self):
        self.add_wire_identity();self.clients["B0"]["cases"][1]["waves"][0]["network_identity"]["valid"]=False;self.sync_wire_acks();self.reject()
    def test_partial_wire_treatment_rejected(self):
        self.add_wire_identity();self.clients["A"]["network_identity_required"]=False;self.reject()
    def test_native_null_id_not_fabricated(self):
        self.add_wire_identity();self.server["native_identity_null_probe"]=dict(valid=True,transport="Legacy",wire_id="1");self.reject()
    def test_native_role_not_a_local_name_assumption(self):
        self.add_wire_identity();self.clients["B0"]["cases"][0]["waves"][0]["network_identity"]["local_role"]=2;self.sync_wire_acks();self.reject()
    def test_two_reset_waves_are_two_real_network_actors(self):
        self.add_wire_identity();self.server["cases"][0]["waves"][1]["network_identity"]=copy.deepcopy(self.server["cases"][0]["waves"][0]["network_identity"]);self.reject()
    def test_lazy_observer_must_have_really_installed(self):
        self.server["lazy_lifecycle_observation"]=dict(installed=False,restored=True,preloaded=False,cdo_written=False,event_files=["event.json"]);self.reject()
    def test_lazy_observer_never_preloads(self):
        self.clients["A"]["lazy_lifecycle_observation"]=dict(installed=True,restored=True,preloaded=True,cdo_written=False,event_files=["event.json"]);self.reject()
    def test_lazy_observer_must_restore_after_close(self):
        self.clients["B0"]["lazy_lifecycle_observation"]=dict(installed=True,restored=False,preloaded=False,cdo_written=False,event_files=["event.json"]);self.reject()
    def test_one_client_missing(self): self.clients.pop("B0");self.reject()
    def test_not_dedicated(self): self.server["native_mode"]="Standalone";self.reject()
    def test_same_actual_owner(self): self.server["player_ids"]["B0"]=256;self.reject()
    def test_wrong_native_client_role(self): self.clients["A"]["native_role"]=3;self.reject()
    def test_client_never_grants_native_spec(self): self.clients["A"]["client_native_give_clear_called"]=True;self.reject()
    def test_native_authority_not_local_player(self): self.server["cases"][1]["native_locally_controlled"]=True;self.reject()
    def test_server_does_not_register_client_ui(self): self.server["cases"][1]["native_callbacks"][-1]["counts"]["registrations"]=1;self.reject()
    def test_native_nonlocal_callback_state(self): self.server["cases"][1]["native_callbacks"][0]["after"]["valid"]=True;self.reject()
    def test_foreign_ui_never_duplicated(self): self.clients["B0"]["cases"][0]["waves"][0]["widgets"].append("foreign");self.reject()
    def test_foreign_pawn_is_real_simulated_proxy(self): self.clients["B0"]["cases"][0]["waves"][0]["source_role"]=2;self.reject()
    def test_canonical_bound_foreign_asc_required(self): self.clients["B0"]["cases"][0]["waves"][0]["canonical_bound_asc"]=False;self.reject()
    def test_health_zero_not_accepted_as_ready(self): self.clients["A"]["cases"][0]["waves"][0]["health"]=0.;self.reject()
    def test_native_pawn_must_change(self):
        wave=self.clients["A"]["cases"][0]["waves"][0];wave["pawn"]=wave["old_pawn"];self.reject()
    def test_server_waits_actual_process_exits(self): self.server["server_waited_for_client_process_exit"]=False;self.reject()
    def test_client_quiet_interval(self): self.clients["A"]["cases"][0]["quiet_ticks"]=19;self.reject()
    def test_native_removal_callback_not_optional(self): self.clients["A"]["cases"][1]["native_callbacks"].pop();self.reject()
    def test_correct_event_owner_context(self): self.clients["B0"]["cases"][3]["native_callbacks"][0]["owner"]="pawn";self.reject()
    def test_no_pool_state_write(self): self.clients["A"]["native_ui_pool_written"]=True;self.reject()
    def test_observer_restore_required(self): self.server["observers_restored"]=False;self.reject()
    def test_native_ack_matches_actual_client(self): self.server["cases"][0]["viewers"]["A"]["quiet_ticks"]=21;self.reject()
    def test_both_original_and_python_required(self): self.server["cases"].pop();self.reject()
    def test_live_pre_release_spec_snapshot_required(self): self.server["native_pre_release_specs"]["A"]["native_asc_alive"]=False;self.reject()
    def test_pre_release_clone_handle_absent(self): self.server["native_pre_release_specs"]["B0"]["current_handles"].append(99);self.reject()
    def test_pre_release_original_classes_restored(self): self.server["native_pre_release_specs"]["A"]["original_specs_restored"]=False;self.reject()
    def test_client_has_no_native_authority_writes(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_widget_network_validation.py").read_text(encoding="utf-8")
        client_text=text.split("class Client",1)[1].split("class Server",1)[0]
        for value in ('call_function("K2_GiveAbility"','call_function("ClearAbility"','call_function("SendGameplayEventToActor"'):
            self.assertNotIn(value,client_text)
        self.assertIn('value["exit_code"]==0',text);self.assertIn('readiness.snapshot(pawn,health)',text)
    def test_client_does_not_wait_for_server_only_auto_respawn_activation(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_widget_network_validation.py").read_text(encoding="utf-8")
        self.assertIn('self.require_auto_active=False',text.split("class Server",1)[0])
