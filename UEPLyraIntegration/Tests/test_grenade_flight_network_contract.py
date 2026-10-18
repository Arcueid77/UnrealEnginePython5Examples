"""Reject stationary, manually triggered or locally simulated throw evidence."""
import unittest
from uep_lyra_weapons import grenade_flight_network_contract as policy


def identity(number, role): return dict(valid=True, transport="Legacy", wire_id=str(number), local_role=role, object_path="/World.Actor_"+str(number))


def reports():
    def shell(peer):
        data = dict(status="passed", error=None, peer=peer, native_mode="DedicatedServer" if peer == "server" else "Client",
            network_acceptance=True, observers_restored=True, ability_observers_restored=True, ability_profiles_restored=True,
            actor_selector_restored=True, actor_configuration_preserved=True, observation_errors=[], remaining_projectiles=0, cases=[],
            control_rotation_restored=True)
        data.update({name: False for name in policy.FALSE})
        return data
    server, clients = shell("server"), {peer: shell(peer) for peer in policy.PEERS}
    server.update(player_ids=dict(A=1, B0=2), server_waited_for_client_process_exit=True)
    for peer in policy.PEERS: clients[peer]["player_id"] = server["player_ids"][peer]
    def event(profile, authority, actor_id, source):
        return dict(**{"class": policy.CLASS}, profile=profile, authority=authority, role=3 if authority else 1,
            rpc_flags_preserved=True, identity=identity(actor_id, 3 if authority else 1), instigator_identity=source,
            fixture_held_stationary=False, stats=dict(python_bodies=int(profile == "Python"), fallback_bodies=int(profile == "BlueprintFallback"),
                overlaps=int(authority and profile == "Python"), traces=0, effects=0),
            trigger="native-fuse" if authority else "client-pending-fuse", actor_destroyed_after_body=authority,
            trail_before=not authority, fuse_remaining_before=-.01 if authority else .15, age_at_body=2.01 if authority else 1.85,
            fuse_exists_before=True, hidden_after=True, movement_active_after=False, hit_comparison=None)
    def activation(profile, authority):
        py = profile == "Python"
        return dict(profile=profile, authority=authority, mode=0 if authority else 2, source_role=3 if authority else 2,
            native_begin_delta=int(authority), active_after=False,
            stats=dict(python_calls=int(py), fallback_calls=int(not py), projectiles=int(py and authority), commits=int(py), native_ends=int(py)))
    def row(index, owner, profile, peer):
        authority, own = peer == "server", peer == owner
        source = identity(10 if owner == "A" else 20, 3 if authority else 2 if own else 1)
        return dict(position=index, owner=owner, profile=profile, source_identity=source, identity=identity(100+index, 3 if authority else 1),
            native_begin_count=1, native_body_count=1, destroyed=True, quiet_ticks=8, begin=dict(movement_active=True),
            trajectory=dict(samples=10, distinct_positions=10, active_movement_samples=10, max_displacement=500.),
            body=event(profile, authority, 100+index, source), native_aim_sync=True,
            activation_requests=int(own), native_request_accepted=own, activations=[activation(profile, authority)] if authority or own else [],
            player_health_after={name:dict(identity=identity(10 if name == "A" else 20, 3 if authority else 2 if name == peer else 1), health=100.) for name in policy.PEERS})
    for index, (owner, profile) in enumerate(policy.PLAN):
        server["cases"].append(row(index, owner, profile, "server"))
        for peer in policy.PEERS: clients[peer]["cases"].append(row(index, owner, profile, peer))
    return server, clients


def log_proof(server, clients):
    result = {}
    for peer, data in {"server": server, **clients}.items():
        result[peer] = {row["identity"]["wire_id"]: dict(actor=row["identity"]["object_path"], native_guid=row["identity"]["wire_id"],
            position=row["position"], sent_lines=[1, 2] if peer == "server" else [], received_lines=[] if peer == "server" else [1],
            cleanup_lines=[3] if peer != "server" else [], body_line=2, rpc_before_body=True) for row in data["cases"]}
    return result


class TestGrenadeFlightNetworkContract(unittest.TestCase):
    def setUp(self):
        self.server, self.clients = reports()
        self.logs = log_proof(self.server, self.clients)
    def rejected(self):
        with self.assertRaises(RuntimeError): policy.validate(self.server, self.clients, self.logs)
    def test_complete_natural_chain(self): self.assertEqual(policy.validate(self.server, self.clients, self.logs)["actual_predicted_client_throws"], 4)
    def test_fixture_spawned_projectile(self): self.server["projectile_spawned_by_fixture"] = True; self.rejected()
    def test_fixture_changed_movement(self): self.clients["A"]["projectile_movement_written_by_fixture"] = True; self.rejected()
    def test_fixture_called_detonate(self): self.server["detonate_requested_by_fixture"] = True; self.rejected()
    def test_fixture_destroyed_actor(self): self.server["projectile_destroyed_by_fixture"] = True; self.rejected()
    def test_stationary_actor(self): self.server["cases"][0]["trajectory"]["max_displacement"] = 0.; self.rejected()
    def test_pose_samples_are_duplicates(self): self.clients["B0"]["cases"][0]["trajectory"]["distinct_positions"] = 1; self.rejected()
    def test_movement_never_active(self): self.clients["A"]["cases"][0]["begin"]["movement_active"] = False; self.rejected()
    def test_client_spawned_predicted_projectile(self): self.clients["A"]["cases"][0]["activations"][0]["native_begin_delta"] = 1; self.rejected()
    def test_server_bypassed_client_request(self): self.server["cases"][0]["activation_requests"] = 1; self.rejected()
    def test_nonpredicted_client_mode(self): self.clients["A"]["cases"][0]["activations"][0]["mode"] = 0; self.rejected()
    def test_local_client_timer_without_native_receive(self):
        event = self.clients["A"]["cases"][0]["body"]
        event.update(trigger="client-fuse-due", fuse_remaining_before=0.)
        self.logs["A"]["100"]["received_lines"] = []
        self.rejected()
    def test_due_local_fuse_does_not_hide_real_received_rpc(self):
        self.clients["A"]["cases"][0]["body"].update(trigger="client-fuse-due", fuse_remaining_before=0.)
        self.assertEqual(policy.validate(self.server, self.clients, self.logs)["actual_native_explosions"], 4)
    def test_local_enemy_hit_instead_of_multicast(self): self.clients["B0"]["cases"][0]["body"]["trigger"] = "native-enemy-hit"; self.rejected()
    def test_unrelated_instigator(self): self.clients["A"]["cases"][0]["body"]["instigator_identity"] = identity(999, 2); self.rejected()
    def test_foreign_owner_activated(self): self.clients["B0"]["cases"][0]["activation_requests"] = 1; self.rejected()
    def test_client_health_not_replicated(self): self.clients["A"]["cases"][0]["player_health_after"]["B0"]["health"] = 90.; self.rejected()
    def test_control_not_restored(self): self.clients["A"]["control_rotation_restored"] = False; self.rejected()
    def test_actual_exit_missing(self): self.server["server_waited_for_client_process_exit"] = False; self.rejected()
    def test_stale_command_ignored(self): self.assertFalse(policy.accept_command(dict(position=0, stage="activate"), (0, "activate"), -1))
    def test_future_complete_rejected(self):
        with self.assertRaises(RuntimeError): policy.accept_command(dict(position=0, stage="complete"), None, -1)
    def test_prior_owner_self_damage_does_not_block_next_owner(self):
        self.assertEqual(policy.reset_peers("B0", dict(A=22.82447052001953, B0=100.)), ("A", "B0"))
    def test_healthy_foreign_player_does_not_need_reset(self):
        self.assertEqual(policy.reset_peers("A", dict(A=100., B0=100.)), ("A",))
    def test_native_receiver_guid_mismatch(self): self.logs["A"]["100"]["native_guid"] = "999"; self.rejected()
    def test_second_native_connection_send_missing(self): self.logs["server"]["100"]["sent_lines"] = [1]; self.rejected()
