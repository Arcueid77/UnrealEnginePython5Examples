"""Reject missing/duplicate/wrong-owner native event/RPC evidence."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_auto_respawn_listeners_contract import report as listener_report, reports as listener_reports
from uep_lyra_abilities import auto_respawn_events_contract as gate


def messages(player_id=1, *, completion=True, duration=True, foreign=False):
    values = []
    if duration: values.append(dict(channel=gate.DURATION, player_id=player_id, owner_matches=not foreign, duration=5.))
    if completion: values.append(dict(channel=gate.COMPLETED, player_id=player_id, owner_matches=not foreign, verb=gate.COMPLETED,
        magnitude=1., target_is_null=True, instigator_tags=[], target_tags=[], context_tags=[]))
    return values


def stats(profile, final, *, authority=True, server=False, avatar=False):
    return dict(death_events=int(profile == "Python" and not avatar), fallback_death_events=int(profile == "BlueprintFallback" and not avatar),
        avatar_end_events=int(profile == "Python" and avatar), fallback_avatar_end_events=int(profile == "BlueprintFallback" and avatar),
        duration_messages=int(profile == "Python" and not avatar), long_delays_started=int(profile == "Python" and not avatar),
        long_continuations=int(final == "Python" and not avatar), fallback_long_continuations=int(final == "BlueprintFallback" and not avatar),
        short_delays_started=int(final == "Python"), short_continuations=int(final == "Python"), fallback_short_continuations=int(final == "BlueprintFallback"),
        native_restarts=int(final == "Python" and authority), native_completion_rpcs=int(final == "Python" and authority),
        cosmetic_completion_messages=int(final == "Python" and authority and not server))


def add_row(row, name, profile, *, player_id=1, server=False):
    final = "BlueprintFallback" if name == "profile-switch-during-death" and profile == "Python" else "Python" if name == "profile-switch-during-death" else profile
    for phase in ("living_query", "dead_query", "after_query"): row[phase]["should_finish_restart"] = phase == "dead_query"
    row.update(event_counters=stats(profile, final, authority=row["native_owner_role"] == 3, server=server),
        native_player_id=player_id, event_messages=messages(player_id, completion=not server), event_observer_closed=True)


def add_peer(report):
    report.update(death_listener_timer_restart_business_migrated=True, timer_restart_business_migrated=True,
        death_avatar_event_business_migrated=True, original_two_native_delay_nodes_reused=True,
        activation_reset_ui_removal_business_migrated=False, duration_completion_broadcast_by_fixture=False)
    count = len(report["cases"])*(1 if report["network_acceptance"] else 2)+len(report.get("foreign_cases", []))+len(report.get("avatar_endplay_cases", []))
    report["event_fixture_shutdown"] = dict(created=count, closed=count, active=0)
    count -= len(report.get("foreign_cases", []))
    report["listener_fixture_shutdown"] = dict(created=count, closed=count, active=0)


def avatar_row(profile):
    baseline = dict(classes=["stable", "/Game/Weapons/GA_Weapon_AutoReload.GA_Weapon_AutoReload_C",
        "/Game/Weapons/Pistol/GA_Weapon_Reload_Pistol.GA_Weapon_Reload_Pistol_C",
        "/ShooterCore/Weapons/Pistol/GA_Weapon_Fire_Pistol.GA_Weapon_Fire_Pistol_C"], persistent=[[1, "auto"]])
    return dict(profile=profile, native_type_preserved=True, native_auto_respawn_active=True, native_auto_respawn_still_active=True,
        native_owner_role=3, native_death_active_before=False, native_death_active_after=False, health_before=100., respawn_health=100.,
        old_pawn="old", new_pawn="new", native_elapsed=3., specs_unchanged=True, delay_unchanged=True, specs_before=baseline, specs_after=copy.deepcopy(baseline),
        specs_at_restart=dict(classes=["stable"], persistent=[[1, "auto"]]),
        native_quickbar_recovery=dict(required=True, slot_before=0, slot_after=0, slots_unchanged=True, calls=[1, 0]),
        listener_foreign_events=["endplay"], listener_observer_closed=True, event_observer_closed=True,
        after_query=dict(should_finish_restart=False, owner_matches=True, dead=False,
            listener_cache=dict(avatar_matches=True, health_matches=True, health_is_null=False)),
        event_counters=stats(profile, profile, avatar=True), event_messages=messages(duration=False), native_player_id=1)


def report():
    value = listener_report(); value.update(avatar_endplay_cases=[avatar_row(profile) for profile in ("BlueprintFallback", "Python")],
        native_avatar_destroy_called_by_fixture=True); add_peer(value)
    for case in value["cases"]:
        for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")): add_row(case[key], case["name"], profile)
    return value


def reports():
    value = listener_reports()
    for peer, data in value.items():
        add_peer(data)
        for row in data["cases"]: add_row(row, row["name"], row["profile"], player_id=value["server"]["player_ids"][row["target"]], server=peer == "server")
        for row in data.get("foreign_cases", []):
            row.update(event_observer_closed=True, event_messages=messages(value["server"]["player_ids"][row["target"]], duration=False, foreign=True))
    for row in value["server"]["cases"]:
        row["owner_ack"]["row"] = copy.deepcopy(value[row["target"]]["cases"][row["index"]])
        other = "B0" if row["target"] == "A" else "A"
        row["foreign_ack"]["row"] = copy.deepcopy(next(r for r in value[other]["foreign_cases"] if r["position"] == row["position"]))
    return value


class EventReportModels(unittest.TestCase):
    def test_bounded_death_and_actual_avatar_pair_shape(self): self.assertTrue(gate.validate(report())["forced_avatar_endplay_tested"])
    def test_bounded_two_owner_reliable_foreign_delivery_shape(self): self.assertTrue(gate.validate_network(reports())["foreign_reliable_completion_observed"])

    def test_missing_duplicate_wrong_owner_duration_completion_rejected(self):
        for change in (lambda row: row["event_messages"].pop(), lambda row: row["event_messages"].append(copy.deepcopy(row["event_messages"][-1])),
            lambda row: row["event_messages"][0].update(owner_matches=False), lambda row: row["event_messages"][0].update(duration=.1),
            lambda row: row["event_messages"][-1].update(magnitude=2.), lambda row: row["event_messages"][-1].update(target_is_null=False)):
            value = report(); change(value["cases"][0]["python"])
            with self.assertRaises(RuntimeError): gate.validate(value)

    def test_pending_restart_flag_and_both_native_continuations_required(self):
        for field in ("long_continuations", "short_continuations", "native_restarts", "native_completion_rpcs", "cosmetic_completion_messages"):
            value = report(); value["cases"][0]["python"]["event_counters"][field] = 0
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["python"]["dead_query"]["should_finish_restart"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_original_event_dispatch_not_replayed_or_bypassed(self):
        for field in ("death_events", "duration_messages", "long_delays_started"):
            value = report(); value["cases"][0]["python"]["event_counters"][field] = 0
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_forced_avatar_pair_cannot_be_substituted_with_death_path(self):
        for change in (lambda r: r["avatar_endplay_cases"].pop(), lambda r: r.update(native_avatar_destroy_called_by_fixture=False),
            lambda r: r["avatar_endplay_cases"][1]["event_counters"].update(death_events=1),
            lambda r: r["avatar_endplay_cases"][1].update(native_elapsed=8.),
            lambda r: r["avatar_endplay_cases"][1].update(specs_after={"changed": True})):
            value = report(); change(value)
            with self.assertRaises(RuntimeError): gate.validate(value)

    def test_client_cannot_restart_even_if_ability_guard_is_authority(self):
        value = reports(); value["A"]["cases"][1]["event_counters"]["native_restarts"] = 1
        value["server"]["cases"][1]["owner_ack"]["row"] = copy.deepcopy(value["A"]["cases"][1])
        with self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_avatar_equipment_gap_cannot_hide_non_equipment_loss_or_incomplete_cleanup(self):
        for change in (lambda row: row["specs_at_restart"].update(persistent=[]),
            lambda row: row["specs_at_restart"]["classes"].append("foreign"),
            lambda row: row["native_quickbar_recovery"].update(slots_unchanged=False),
            lambda row: row["native_quickbar_recovery"].update(slot_after=1),
            lambda row: row["native_quickbar_recovery"].update(calls=[])):
            value = report(); change(value["avatar_endplay_cases"][1])
            with self.assertRaises(RuntimeError): gate.validate(value)

    def test_foreign_reliable_payload_must_name_actual_other_player(self):
        value = reports(); row = value["B0"]["foreign_cases"][0]; row["event_messages"][0]["player_id"] = 2
        value["server"]["cases"][0]["foreign_ack"]["row"] = copy.deepcopy(row)
        with self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_dedicated_server_has_no_local_cosmetic_completion(self):
        value = reports(); row = value["server"]["cases"][1]; row["event_messages"].extend(messages(completion=True, duration=False))
        with self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_message_scope_cleanup_and_real_transport_required(self):
        for mutate in (lambda r: r.update(duration_completion_broadcast_by_fixture=True), lambda r: r.update(original_two_native_delay_nodes_reused=False),
            lambda r: r["event_fixture_shutdown"].update(active=1), lambda r: r.update(activation_reset_ui_removal_business_migrated=True)):
            value = report(); mutate(value)
            with self.assertRaises(RuntimeError): gate.validate(value)

    def test_listener_modules_cannot_start_a_duplicate_event_fixture(self):
        root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities"
        for name, flag in (("auto_respawn_listeners_validation.py", "-UEPAutoRespawnHelpersResult=x"),
            ("auto_respawn_listeners_network_validation.py", "-UEPAutoRespawnHelpersNetworkResult=x")):
            footer = ast.parse((root/name).read_text(encoding="utf-8")).body[-1]
            def unexpected(*args): raise AssertionError("duplicate inherited listener fixture")
            scope = dict(sys=types.SimpleNamespace(argv=[flag, "-UEPAutoRespawnListeners", "-UEPAutoRespawnEvents"]), result="x",
                Validation=unexpected, Server=unexpected, Client=unexpected, arg=unexpected)
            exec(compile(ast.Module(body=[footer], type_ignores=[]), str(root/name), "exec"), scope)
