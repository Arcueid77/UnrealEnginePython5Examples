"""Server/owner/foreign death report models; never native acceptance."""
import copy
import unittest
from test_character_lifecycle_network_contract import reports as lifecycle_reports
from test_character_death_started_contract import entry, upgrade
from test_character_ragdoll_contract import counts as ragdoll_counts
from test_character_equipment_hide_contract import counts as hide_counts
from uep_lyra_characters import death_replication_contract as gate


def observed(profile, role, player_id):
    actor = "actual-actor"; server = role == 3
    return dict(actor=actor, native_class=gate.CLASS, profile=profile, player_id=player_id, native_role=role,
        health_before=100., actor_was_not_rooted=True, old_actor_invalid=True, quiet_after_destroy=True,
        quiet_game_seconds=3., profile_restored_or_actor_destroyed=True, evidence_after_destroy_is_pod=True,
        fixture_replayed_callback=False, fixture_changed_animation_physics=False,
        senses_before=[gate.SIGHT, "Hearing"], configured_montages=["montage-A", "montage-B"], perception_systems=["server-system"] if server else [],
        observer=dict(created=1, closed=1, active=0), observer_errors=[],
        signals=[dict(owning_actor=actor, native_health=0., native_death_state=1, montage="montage-A", senses=["Hearing"] if server else [gate.SIGHT, "Hearing"])],
        death=entry(profile), ragdoll=ragdoll_counts(profile), hide=hide_counts(profile == "Python"), maximum_world_delta=.02,
        body=dict(physical=dict(mesh="mesh", bone="Pelvis", collision_profile="Ragdoll", simulating=True, velocity=[1., 2., 3.]),
            equipment_instances=1, weapon_paths=["pistol"], weapon_hidden=[True]))


def reports():
    values = lifecycle_reports()
    for peer, value in values.items():
        upgrade(value); value.update(network_death_receiver_ingress_tested=True, foreign_dying_replica_observed=True, ragdoll_physics_replication_tested=False,
            authority_pawns_relocated_for_native_relevancy=True)
        if peer == "server": value["native_relevancy_teleports"] = [dict(peer=key, actor=key, position=0, native_api="K2_TeleportTo", succeeded=True, actual_location=[0., 0., 0.]) for key in ("A", "B0")]
        for row in value["cases"]:
            row["death_replication"] = observed(row["profile"], 3 if peer == "server" else 2, values["server"]["player_ids"][row["target"]])
        for row in value.get("foreign_cases", []):
            server = next(item for item in values["server"]["cases"] if item["position"] == row["position"])
            row["death_replication"] = observed(server["profile"], 1, values["server"]["player_ids"][server["target"]])
        total = len(value["cases"])+len(value.get("foreign_cases", []))
        value["death_replication_fixture_shutdown"] = dict(created=total, closed=total, active=0)
    for row in values["server"]["cases"]:
        other = "B0" if row["target"] == "A" else "A"
        row["owner_ack"]["row"] = copy.deepcopy(next(item for item in values[row["target"]]["cases"] if item["position"] == row["position"]))
        row["foreign_ack"]["row"] = copy.deepcopy(next(item for item in values[other]["foreign_cases"] if item["position"] == row["position"]))
    return values


class DeathReplicationModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): gate.validate(self.reports)
    def row(self): return self.reports["A"]["cases"][1]["death_replication"]
    def test_complete_shape_is_only_model(self): self.assertEqual(gate.validate(self.reports)["actual_death_receiver_observations"], 36)
    def test_no_physics_replication_claim(self): self.reports["server"]["ragdoll_physics_replication_tested"] = True; self.reject()
    def test_real_signal_required(self): self.row()["signals"] = []; self.reject()
    def test_no_duplicate_signal(self): self.row()["signals"] *= 2; self.reject()
    def test_no_callback_replay(self): self.row()["fixture_replayed_callback"] = True; self.reject()
    def test_no_actor_rooting(self): self.row()["actor_was_not_rooted"] = False; self.reject()
    def test_no_late_work_after_destroy(self): self.row()["quiet_after_destroy"] = False; self.reject()
    def test_quiet_window_exceeds_native_delay(self): self.row()["quiet_game_seconds"] = .1; self.reject()
    def test_native_delay_must_really_resume(self): self.row()["death"]["resumes"] = 0; self.reject()
    def test_no_native_delay_early_resume(self): self.row()["death"]["last_resume"]["game_seconds"] = 1.01; self.reject()
    def test_current_montage_not_just_counter(self): self.row()["signals"][0]["montage"] = "hit-react"; self.reject()
    def test_actual_signal_actor_identity(self): self.row()["signals"][0]["owning_actor"] = "other"; self.reject()
    def test_actual_owner_replica_role(self): self.row()["native_role"] = 3; self.reject()
    def test_actual_foreign_replica_role(self): self.reports["B0"]["foreign_cases"][0]["death_replication"]["native_role"] = 2; self.reject()
    def test_native_physical_body_not_only_route_count(self): self.row()["body"]["physical"]["simulating"] = False; self.reject()
    def test_actual_hidden_weapon_required(self): self.row()["body"]["weapon_hidden"] = [False]; self.reject()
    def test_other_native_sense_preserved(self): self.row()["signals"][0]["senses"] = []; self.reject()
    def test_death_observer_leak_rejected(self): self.reports["A"]["death_replication_fixture_shutdown"]["active"] = 1; self.reject()
    def test_foreign_target_identity_required(self): self.reports["B0"]["foreign_cases"][0]["death_replication"]["player_id"] = -1; self.reject()
    def test_existing_real_inventory_lifecycle_regression_remains_required(self): self.reports["A"]["cases"][0]["character_inventory"]["counters"]["items_removed"] = 1; self.reject()
    def test_native_relevancy_fixture_must_be_declared(self): self.reports["server"]["authority_pawns_relocated_for_native_relevancy"] = False; self.reject()
    def test_actual_native_relevancy_teleport_result_required(self): self.reports["server"]["native_relevancy_teleports"][0]["succeeded"] = False; self.reject()
