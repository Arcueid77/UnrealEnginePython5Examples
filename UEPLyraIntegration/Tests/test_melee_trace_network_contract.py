"""Native report counterexamples only; no network or damage is simulated here."""
import copy
from pathlib import Path
import unittest
from test_melee_trace_contract import example
from uep_lyra_abilities.melee_trace_network_contract import PLAN, PEERS, TOTAL, validate


def model():
    source = example(); rows = source["cases"]; ids = dict(A=256, B0=257)
    viewers = {}
    for peer in PEERS:
        report = dict(status="passed", error=None, peer=peer, native_role=2, native_net_mode="Client", player_id=ids[peer],
            requests=[dict(index=index, scenario=name, profile=profile, native_request_accepted=True, native_activation_observed=True,
                native_ability_authority=False, native_activation_mode=2,
                native_montage_observed=True, native_ended=True, native_tasks_after=0, trace_queries=0, trace_fallbacks=0) for index,(name,profile) in enumerate(PLAN)],
            views=[], observation_errors=[], native_control_restoration=dict(control_rotation=True),
            shutdown=dict(active_count=0, errors=[], scopes_created=5, scopes_closed=5))
        report.update({name:False for name in ("activation_event_replayed", "callback_replay", "health_properties_written", "ability_granted_by_fixture", "full_acceptance", "packaged_runtime", "physical_input_tested", "packet_loss_tested", "travel_rejoin_tested")})
        report.update({name:True for name in ("profile_restored", "specs_config_unchanged", "cue_observer_restored", "activation_observers_restored", "observer_scope_closed", "native_floor_archetype_observed")})
        for position in range(TOTAL):
            target = PEERS[position//len(PLAN)]; index = position%len(PLAN); name,profile = PLAN[index]; applied = name == "hostile"
            cues = [dict(source_player_id=ids[target], original="GameplayCue.Weapon.Melee.Hit", location=[0.,0.,0.], normal=[0.,0.,0.], source=None)] if applied and target != peer else []
            report["views"].append(dict(position=position, source_peer=target, source_player_id=ids[target], index=index, scenario=name, profile=profile,
                target_player_name="target" if name in ("friendly","occluded","hostile") else None, target_identity_unique=True,
                quiet_ticks=20, own_health_unchanged=True, foreign_ability_idle=True, observer_scope_closed=True,
                native_health_delta=100. if applied else 0., cues=cues, health_events=[dict(old=100., new=0.)] if applied else []))
        viewers[peer] = report
    server = dict(status="passed", error=None, native_net_mode="DedicatedServer", player_ids=ids, cases=[], observation_errors=[],
        shutdown=dict(active_count=0, errors=[], scopes_created=10, scopes_closed=10))
    server.update({name:True for name in ("server_waited_for_client_process_exit", "profiles_restored", "specs_config_unchanged", "activation_observers_restored", "fixtures_destroyed", "observer_scope_closed")})
    for position in range(TOTAL):
        peer = PEERS[position//len(PLAN)]; index = position%len(PLAN); name,profile = PLAN[index]; row = copy.deepcopy(rows[index]); applied = name == "hostile"
        row.update(position=position, source_peer=peer, scenario=name, profile=profile, native_activation_observed=True, native_montage_observed=True,
            target_player_name="target" if name in ("friendly","occluded","hostile") else None,
            target_immunity_count_at_activation=0 if name in ("friendly","occluded","hostile") else None,
            native_ended=True, foreign_owner_unchanged=True, specs_config_unchanged=True, observer_scope_closed=True,
            native_role=3, native_tasks_after=0, native_health_delta=100. if applied else 0.,
            health_events=[dict(old=100.,new=0.)] if applied else [], viewers={name:copy.deepcopy(value["views"][position]) for name,value in viewers.items()})
        server["cases"].append(row)
    return server,viewers


class TestMeleeTraceNetworkContract(unittest.TestCase):
    def setUp(self): self.server,self.clients = model()
    def reject(self):
        with self.assertRaises((AssertionError,RuntimeError)): validate(self.server,self.clients)
    def test_complete_model(self): self.assertEqual(validate(self.server,self.clients)["native_authority_trials"],20)
    def test_one_owner(self): self.clients.pop("B0"); self.reject()
    def test_same_native_owner(self): self.server["player_ids"]["B0"]=256; self.reject()
    def test_wrong_owner_id(self): self.clients["A"]["player_id"]=99; self.reject()
    def test_not_dedicated_server(self): self.server["native_net_mode"]="Standalone"; self.reject()
    def test_not_native_client(self): self.clients["A"]["native_net_mode"]="Standalone"; self.reject()
    def test_wrong_client_role(self): self.clients["A"]["native_role"]=3; self.reject()
    def test_missing_owner_request(self): self.clients["A"]["requests"].pop(); self.reject()
    def test_replayed_activation(self): self.clients["A"]["activation_event_replayed"]=True; self.reject()
    def test_raw_health_write(self): self.clients["A"]["health_properties_written"]=True; self.reject()
    def test_non_authority_trace(self): self.clients["A"]["requests"][0]["trace_queries"]=1; self.reject()
    def test_missing_authority_trial(self): self.server["cases"].pop(); self.reject()
    def test_missing_second_viewer_trial(self): self.clients["B0"]["views"].pop(); self.reject()
    def test_client_floor_missing(self): self.clients["A"]["native_floor_archetype_observed"]=False; self.reject()
    def test_native_server_scope_leak(self): self.server["shutdown"]["scopes_closed"]=9; self.reject()
    def test_native_client_scope_leak(self): self.clients["A"]["shutdown"]["scopes_closed"]=4; self.reject()
    def test_server_exits_before_clients(self): self.server["server_waited_for_client_process_exit"]=False; self.reject()
    def test_observer_not_restored(self): self.clients["A"]["activation_observers_restored"]=False; self.reject()
    def test_cue_observer_not_restored(self): self.clients["A"]["cue_observer_restored"]=False; self.reject()
    def test_no_native_hostile_health(self): self.server["cases"][8]["native_health_delta"]=0.; self.reject()
    def test_no_native_root_witness(self): self.server["cases"][8]["root_tasks"]=[]; self.reject()
    def test_wrong_native_root_formula(self): self.server["cases"][8]["root_tasks"][0]["strength"]=2200.; self.reject()
    def test_wrong_native_root_gravity(self): self.server["cases"][8]["root_tasks"][0]["gravity"]=False; self.reject()
    def test_native_health_delegate_missing(self): self.server["cases"][8]["health_events"]=[]; self.reject()
    def test_native_hit_context_changed(self): self.server["cases"][8]["stored_effect_context"]["hit_actor"]="target"; self.reject()
    def test_respawn_immune_target_not_damage_control(self): self.server["cases"][19]["target_immunity_count_at_activation"]=1; self.reject()
    def test_native_immunity_is_waited_not_removed(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/melee_trace_network_validation.py").read_text(encoding="utf-8")
        self.assertIn('native_immunity_count(ability_system(value[1])) == 0',text)
        self.assertIn('GetGameplayTagCount',text)
        self.assertNotIn('RemoveLooseGameplayTag',text)
    def test_friendly_hits(self): self.server["cases"][4]["native_health_delta"]=100.; self.reject()
    def test_occlusion_missing(self): self.server["cases"][6]["preflight"]["occluded"]=False; self.reject()
    def test_wrong_authority_role(self): self.server["cases"][0]["native_role"]=2; self.reject()
    def test_other_owner_changed(self): self.server["cases"][0]["foreign_owner_unchanged"]=False; self.reject()
    def test_missing_replicated_health(self): self.clients["A"]["views"][8]["native_health_delta"]=0.; self.reject()
    def test_ambiguous_bot_identity(self): self.clients["A"]["views"][8]["target_identity_unique"]=False; self.reject()
    def test_different_replicated_target(self): self.clients["A"]["views"][8]["target_player_name"]="another-bot"; self.reject()
    def test_target_lookup_not_nonunique_bot_player_id(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/melee_trace_network_validation.py").read_text(encoding="utf-8")
        self.assertIn('target = named_pawn(self.world, self.statics, command["target_player_name"])',text)
        self.assertIn('return values[0] if len(values) == 1 else None',text)
    def test_arming_waits_have_native_diagnostics(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/melee_trace_network_validation.py").read_text(encoding="utf-8")
        for name in ('"pending_arm"','"replicated-source-pose"','"unique-replicated-target-and-health"','"native_pawn_names"'):
            self.assertIn(name,text)
    def test_native_health_binding_diagnosed_not_assumed_dead(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/melee_trace_network_validation.py").read_text(encoding="utf-8")
        for name in ('"native_target_binding"','health.get_property("HealthSet")','health.get_property("AbilitySystemComponent")','player_state_pawn='):
            self.assertTrue(name in text,name)
    def test_missing_replicated_cue(self): self.clients["B0"]["views"][8]["cues"]=[]; self.reject()
    def test_foreign_cue_source(self): self.clients["B0"]["views"][8]["cues"][0]["source_player_id"]=99; self.reject()
    def test_owner_native_prediction_mode_missing(self): self.clients["A"]["requests"][0]["native_activation_mode"]=3; self.reject()
    def test_native_authority_on_predictor(self): self.clients["A"]["requests"][0]["native_ability_authority"]=True; self.reject()
    def test_local_cue_replay_is_not_original_parity(self):
        self.clients["A"]["views"][8]["cues"]=[dict(source_player_id=256, original="GameplayCue.Weapon.Melee.Hit", location=[0.,0.,0.], normal=[0.,0.,0.], source=None)]; self.reject()
    def test_ack_does_not_match_viewer(self): self.server["cases"][0]["viewers"]["A"]["quiet_ticks"]=19; self.reject()
    def test_activation_observer_calls_original_handler_once(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/melee_trace_network_observation.py").read_text(encoding="utf-8")
        self.assertEqual(text.count('handler(instance)'),1); self.assertIn('activate.override = "K2_ActivateAbility"',text)
    def test_private_floor_not_overlay_gameplay(self):
        text=(Path(__file__).resolve().parents[1]/"Tools/generate_melee_network_fixture.py").read_text(encoding="utf-8")
        self.assertIn('gameplay_business=False, stage_only=True',text); self.assertIn('ue.add_component_to_blueprint',text)


if __name__ == "__main__": unittest.main()
