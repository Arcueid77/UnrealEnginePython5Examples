"""Reject local substitutes, incorrect wire identity, damage and exit claims."""
import copy
import unittest
from uep_lyra_weapons import grenade_detonate_network_contract as policy


def identity(number, role):
    return dict(valid=True, transport="Legacy", wire_id=str(number), local_role=role)


def reports():
    def shell(peer):
        value = dict(status="passed", error=None, peer=peer, native_mode="DedicatedServer" if peer == "server" else "Client",
            network_acceptance=True, observers_restored=True, remaining_projectiles=0, observation_errors=[], cases=[],
            original_actor_configuration=dict(bReplicates=True, bReplicateMovement=True, bNetLoadOnClient=False), actor_configuration_preserved=True, actor_selector_restored=True)
        value.update({name: False for name in policy.FALSE})
        return value
    server = shell("server")
    server.update(player_ids=dict(A=1, B0=2), server_waited_for_client_process_exit=True)
    clients = {peer: shell(peer) for peer in policy.PEERS}
    for peer in policy.PEERS: clients[peer]["player_id"] = server["player_ids"][peer]
    def body(profile, authority, number):
        py = profile == "Python"
        return dict(profile=profile, **{"class": policy.CLASS}, authority=authority, role=3 if authority else 1,
            identity=identity(number, 3 if authority else 1), age_at_body=2.01, rpc_flags_preserved=True,
            held_stationary_by_native_fixture=True, trail_before=not authority, actor_destroyed_after_body=authority,
            hidden_after=True, movement_active_after=False,
            stats=dict(python_bodies=int(py), fallback_bodies=int(not py), cues=int(py), hidden=int(py), movement_stops=int(py),
                       authority_queries=int(py), overlaps=int(py and authority), destroys=int(py and authority), trail_bindings=0, traces=0, effects=0))
    for index, (owner, name, profile) in enumerate(policy.PLAN):
        source, victim = (10, 20) if owner == "A" else (20, 10)
        row = dict(position=index, owner=owner, name=name, profile=profile, native_body_count=1, destroyed=True, other_health_unchanged=True,
            identity=identity(100+index, 3), body=body(profile, True, 100+index), source_identity=identity(source, 3), victim_identity=identity(victim, 3),
            victim_path="victim", native_target_overlap=["victim"] if name == "enemy-rpc" else [], team_comparison=1,
            health_before=100., health_after=50. if name == "enemy-rpc" else 100., native_fuse_trigger=name == "empty-fuse")
        server["cases"].append(row)
        for peer, client in clients.items():
            client["cases"].append(dict(position=index, owner=owner, name=name, profile=profile, native_body_count=1,
                replicated_actor_destroyed=True, quiet_ticks=8, identity=identity(100+index, 1), body=body(profile, False, 100+index),
                source_identity=identity(source, 2 if peer == owner else 1), victim_identity=identity(victim, 1 if peer == owner else 2),
                health_after=row["health_after"], other_health_unchanged=True, server_values_written_to_gameplay=False))
    return server, clients


class TestGrenadeDetonateNetworkContract(unittest.TestCase):
    def setUp(self): self.server, self.clients = reports()
    def rejected(self):
        with self.assertRaises(RuntimeError): policy.validate(self.server, self.clients)
    def test_complete_actual_peer_matrix(self): self.assertEqual(policy.validate(self.server, self.clients)["client_multicast_bodies"], 24)
    def test_missing_client(self): del self.clients["B0"]; self.rejected()
    def test_same_player_for_both_clients(self): self.server["player_ids"]["B0"] = 1; self.rejected()
    def test_no_actual_process_exit(self): self.server["server_waited_for_client_process_exit"] = False; self.rejected()
    def test_headless_actor_was_not_destroyed(self): self.server["cases"][0]["body"]["actor_destroyed_after_body"] = False; self.rejected()
    def test_fake_rendered_authority(self): self.server["cases"][0]["body"]["trail_before"] = True; self.rejected()
    def test_direct_local_callback_substitute(self): self.clients["A"]["body_callback_replayed"] = True; self.rejected()
    def test_client_attempts_damage(self): self.clients["A"]["cases"][1]["body"]["stats"]["effects"] = 1; self.rejected()
    def test_client_actor_has_authority(self): self.clients["A"]["cases"][1]["body"]["authority"] = True; self.rejected()
    def test_client_observed_other_projectile(self): self.clients["A"]["cases"][0]["identity"]["wire_id"] = "999"; self.rejected()
    def test_stale_replica_pawn(self): self.clients["B0"]["cases"][0]["victim_identity"]["wire_id"] = "999"; self.rejected()
    def test_native_health_not_replicated(self): self.clients["A"]["cases"][2]["health_after"] = 100.; self.rejected()
    def test_additional_native_pawn_in_blast(self): self.server["cases"][2]["native_target_overlap"].append("other"); self.rejected()
    def test_native_fuse_replaced(self): self.server["cases"][4]["native_fuse_trigger"] = False; self.rejected()
    def test_native_fuse_fired_early(self): self.server["cases"][4]["body"]["age_at_body"] = 1.; self.rejected()
    def test_duplicate_body_on_client(self): self.clients["B0"]["cases"][0]["native_body_count"] = 2; self.rejected()
    def test_replication_configuration_changed(self): self.server["actor_configuration_preserved"] = False; self.rejected()
    def test_profile_selector_not_restored(self): self.clients["A"]["actor_selector_restored"] = False; self.rejected()
    def test_command_deduplicated(self):
        self.assertFalse(policy.accept_command(dict(position=0, stage="prepare"), (0, "prepare"), -1))
        self.assertFalse(policy.accept_command(dict(position=0, stage="spawn"), (0, "done"), 0))
    def test_command_outside_plan(self):
        with self.assertRaises(RuntimeError): policy.accept_command(dict(position=-1, stage="spawn"), None, -1)
        with self.assertRaises(RuntimeError): policy.accept_command(dict(position=0, stage="complete"), None, -1)
