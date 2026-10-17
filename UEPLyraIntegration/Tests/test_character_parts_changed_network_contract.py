"""Native replication boundary, concurrent mixed profiles and scheduler capture."""
import ast
import copy
from pathlib import Path
import time
import types
import unittest
from test_character_parts_changed_contract import report as local
from uep_lyra_characters import parts_changed_network_contract as gate
from uep_lyra_hud.startup import validation_module


def reports():
    values = {}
    for peer in ("server", "A", "B0"):
        value = dict(status="passed", error=None, peer=peer, run_id="test", player_ids=dict(A=1, B0=2),
            native_net_mode="DedicatedServer" if peer == "server" else "Client", player_id=2 if peer == "B0" else 1,
            network_acceptance=True, native_world_net_mode_observed=True,
            native_part_fastarray_replication=True, local_part_producer_called=peer == "server", cases=[],
            natural_startup_python_dispatch={target: dict(python_calls=0 if peer == "server" else 2, fallback_calls=0) for target in ("A", "B0")},
            **{key: False for key in ("gameplay_state_delivered_by_files", "component_delegate_broadcast_by_fixture", "callback_replayed", "parts_properties_written",
                "all_parts_removed_by_fixture", "pixels_verified", "hardware_output_tested", "whole_character_migrated", "full_acceptance")})
        for index, (name, operation, profiles) in enumerate(gate.PLAN):
            rows = {}
            for target in ("A", "B0"):
                profile = profiles[target]; py = profile == "Python"; own = target == peer
                active = peer != "server" and operation != "remove-again"; size = int(active and own)
                query = dict(part_of_team=True, team_id=1 if target == "A" else 2, display_asset="display-"+target)
                stats = dict(python_calls=int(active and py), fallback_calls=int(active and not py), team_queries=int(active and py),
                    team_updates=int(active and py), no_team_noops=0)
                rows[target] = dict(profile=profile, native_operation_called=True, native_callback_count=int(active), native_delegate_payload_matches=True,
                    counters=stats, team_counters=dict(python_calls=int(active and py), fallback_calls=int(active and not py)), last_query=query if active and py else None,
                    native_team_query=query, platform_user_valid=own, native_role=3 if peer == "server" else 2 if own else 1, locally_controlled=own,
                    retained_class=gate.CLASS, part_entries=1+int(operation == "add"), original_part_entries=1,
                    temporary_actors=int(peer != "server" and operation == "add"), visual=dict(target=target, native="visual"),
                    native_device_properties_created=size, native_scheduler_removed_owned_properties=True,
                    native_device_properties=copy.deepcopy(local()["cases"][0]["operations"][0]["native_device_properties"]) if size else [])
            value["cases"].append(dict(position=index, actors=rows))
        events, markers, roots = (0, 0, 0) if peer == "server" else (12, 30, 36)
        value["cleanup"] = dict(original_parts_and_visual_profiles_restored=dict(A=True, B0=True), original_inventory_restored=True, cdo_profile_restored=True,
            owned_temporary_actors_destroyed=True, delegate_fixture_shutdown=dict(created=1, closed=1, bindings_created=2, bindings_closed=2, active=0, deliveries=events, errors=[]),
            native_observation_markers=markers, native_observation_markers_removed=True, device_roots_created=roots, device_roots_released=roots)
        values[peer] = value
    values["server"].update(native_playing_gate=dict(native_playing_phase=True), server_waited_for_client_process_exit=True, all_cleanup_frozen_before_release=True)
    return values


class CharacterPartsNetworkModels(unittest.TestCase):
    def test_native_fastarray_two_mixed_bp_instances_and_twentyfour_callbacks(self):
        value = gate.validate(reports()); self.assertEqual((value["native_authority_part_operations"], value["native_client_actor_observations"], value["native_replicated_part_callback_entries"]), (18, 36, 24))

    def test_headless_server_must_not_fabricate_rendered_parts_or_callbacks(self):
        for fields in (dict(temporary_actors=1), dict(native_callback_count=1)):
            value = reports(); value["server"]["cases"][0]["actors"]["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_replica_data_and_both_actual_local_and_foreign_roles_required(self):
        for fields in (dict(part_entries=1), dict(native_role=3), dict(platform_user_valid=False), dict(locally_controlled=False)):
            value = reports(); value["A"]["cases"][0]["actors"]["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_concurrent_same_type_instances_cannot_share_the_wrong_profile(self):
        value = reports(); value["A"]["cases"][0]["actors"]["B0"]["profile"] = "BlueprintFallback"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_original_vs_python_native_visual_and_device_values_are_compared(self):
        value = reports(); value["A"]["cases"][3]["actors"]["A"]["visual"] = dict(native="wrong")
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_only_authority_calls_the_native_producer_and_files_are_not_gameplay_transport(self):
        for fields in (dict(local_part_producer_called=True), dict(gameplay_state_delivered_by_files=True), dict(callback_replayed=True)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_all_observer_roots_original_state_and_exit_barriers_required(self):
        for fields in (dict(device_roots_released=0), dict(cdo_profile_restored=False), dict(owned_temporary_actors_destroyed=False)):
            value = reports(); value["A"]["cleanup"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["server_waited_for_client_process_exit"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_device_object_is_captured_inside_real_multicast_not_later_polling(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/parts_changed_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Context")
        namespace = {}; exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        context = namespace["Context"].__new__(namespace["Context"]); context.tracking = True
        context.names, context.properties, context.marker = {"native-component-owner": "A"}, {"A": []}, "before"
        calls = []; context.devices = types.SimpleNamespace(collect=lambda marker: calls.append(marker) or ["actual-property"], markers=["after"])
        context.delivered("native-component-owner")
        self.assertEqual((calls, context.properties, context.marker), (["before"], {"A": ["actual-property"]}, "after"))

    def test_post_release_server_only_reads_exit_pod(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/parts_changed_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Server")
        namespace = dict(Peer=object, time=time, PEERS=("A", "B0"), require=gate.require, token=lambda *args: dict(exit_code=0), traceback=types.SimpleNamespace(format_exc=lambda: "unexpected native access"))
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        server = namespace["Server"].__new__(namespace["Server"]); calls = []
        server.finished, server.phase, server.started, server.root, server.run = False, "exits", time.monotonic(), "root", "run"
        server.report, server.exit_native, server.status = {}, lambda error=None: calls.append(error), lambda: None
        server.tick(.1); self.assertEqual(calls, [None]); self.assertTrue(server.report["server_waited_for_client_process_exit"])

    def test_explicit_network_selector_is_disabled_for_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterPartsNetworkResult=x"]), "uep_lyra_characters.parts_changed_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterPartsNetworkResult=x"]))

    def test_cleanup_has_live_validity_import_and_becomes_pod_only_after_closing(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/parts_changed_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Context")
        self.assertTrue(any(isinstance(n, ast.ImportFrom) and n.module == "uep_lyra_world.effect_pad_mixin" and any(value.name == "valid" for value in n.names) for n in tree.body))
        calls = []; engine = types.SimpleNamespace(get_mixin_profile=lambda obj: "Python")
        namespace = dict(ue=engine, valid=lambda obj: False, parts=lambda actor: [], part_actors=lambda actor: [], path=str,
            inventory_state=lambda controller: {}, traceback=types.SimpleNamespace(format_exc=lambda: "unexpected cleanup failure"))
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        context = namespace["Context"].__new__(namespace["Context"])
        context.closed, context.server, context.actors, context.controllers = False, False, {"A": "live"}, {}
        context.states = {"A": types.SimpleNamespace(restore=lambda: calls.append("restore"))}
        context.original_parts, context.original_actors, context.cdo, context.cdo_profile = {"A": []}, {"A": []}, "cdo", "Python"
        context.spawned = ["destroyed-actor"]
        context.delegates = types.SimpleNamespace(close=lambda: calls.append("unbind"), snapshot=lambda: {})
        context.devices = types.SimpleNamespace(markers_removed=lambda: True, close=lambda: calls.append("unroot"), markers=[], roots_created=0, roots_released=0)
        first = context.cleanup(); self.assertTrue(first["owned_temporary_actors_destroyed"])
        def dead(*args): raise AssertionError("native objects are gone after one-way release")
        engine.get_mixin_profile = dead
        self.assertIs(context.cleanup(), first); self.assertEqual(calls, ["restore", "unbind", "unroot"])
