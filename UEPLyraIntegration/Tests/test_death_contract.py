"""Native death report gate negatives; no simulated report is runtime proof."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import death_contract as contract


def report():
    result = dict(status="passed", error=None, real_lethal_gas_damage=True, cue_observer_restored=True,
        source_scopes_created=len(contract.PLAN)*2, source_scopes_closed=len(contract.PLAN)*2, cases=[],
        policy_shutdown=dict(active_count=0, scopes_created=len(contract.PLAN), scopes_closed=len(contract.PLAN), errors=[]))
    for name in ("full_acceptance", "network_acceptance", "packaged_runtime", "death_event_sent_by_probe", "activation_handler_replayed",
                 "task_callbacks_replayed", "health_properties_written", "death_duration_written", "animation_assets_modified"): result[name] = False
    for name in contract.PLAN:
        context = dict(instigator="player-state", causer=None, source=None)
        source = dict(magnitude=100., tag="GameplayEvent.Death", target="old-pawn", instigator="player-state", context=context,
            source_tags=[], target_tags=[])
        cue = dict(target="old-pawn", source="old-pawn", instigator="player-state", context=copy.deepcopy(context), source_tags=[], target_tags=[],
            raw=100., normalized=100., location=[0., 0., 0.], normal=[0., 0., 0.], causer=None, material=None, attach=None,
            effect_level=1, ability_level=1, replicate_location=False, matched="GameplayCue.Character.Death", original="GameplayCue.Character.Death")
        value = dict(health_before=100., health_after_damage=0., native_death_started=True, native_type_preserved=True, native_cancelable=False,
            death_camera_matched=True, old_pawn="old-pawn", new_pawn="new-pawn", respawn_health=100., respawn_input_ready=True,
            source_events=1, cue_deliveries=1, source_event=source, cue=cue, cancel_refused=name == "native-cancel-refused",
            profile_switched=name == "active-profile-switch", original_duration=8., native_elapsed=8.05 if name in
                ("native-timer", "native-cancel-refused") else (5.05 if name == "native-auto-respawn" else .35),
            original_respawn_delay=5., fixture_respawn_delay=9. if name in ("native-timer", "native-cancel-refused") else 5.,
            respawn_delay_restored=True, counters=dict(activations=1, cameras_set=1, cues_executed=1,
                    waits_created=1, scopes_created=1, scopes_closed=1, waits_finished=int(name in ("native-timer", "native-cancel-refused")),
                    native_ends=int(name != "active-profile-switch")))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(value), python=copy.deepcopy(value)))
    return result


class DeathContract(unittest.TestCase):
    def test_complete_native_matrix(self): self.assertEqual(contract.validate(report())["pairs"], 5)

    def test_reject_unrestored_fixture_or_unobserved_timer(self):
        for field, value in (("respawn_delay_restored", False), ("fixture_respawn_delay", 5.)):
            data = report(); data["cases"][1]["python"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(data)

    def test_reject_nonlethal_or_canceled_native_death(self):
        for field, replacement in (("health_after_damage", 1.), ("native_cancelable", True), ("native_type_preserved", False),
                                   ("death_camera_matched", False), ("source_events", 0), ("cue_deliveries", 2)):
            value = report(); value["cases"][0]["python"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_payload_loss(self):
        for field, replacement in (("raw", 0.), ("source", None), ("instigator", None), ("context", {}), ("source_tags", ["wrong"])):
            value = report(); value["cases"][0]["python"]["cue"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_wrong_delay_or_profile_intervention(self):
        value = report(); value["cases"][0]["python"]["native_elapsed"] = .1
        with self.assertRaises(RuntimeError): contract.validate(value)
        value = report(); value["cases"][-1]["python"]["profile_switched"] = False
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_replay_and_health_duration_writes(self):
        for field in ("death_event_sent_by_probe", "activation_handler_replayed", "task_callbacks_replayed", "health_properties_written", "death_duration_written"):
            value = report(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_scope_leaks(self):
        value = report(); value["source_scopes_closed"] = 7
        with self.assertRaises(RuntimeError): contract.validate(value)
        value = report(); value["policy_shutdown"]["active_count"] = 1
        with self.assertRaises(RuntimeError): contract.validate(value)
