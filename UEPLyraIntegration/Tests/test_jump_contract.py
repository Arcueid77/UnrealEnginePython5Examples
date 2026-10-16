"""Reject report overclaims independently of a running Editor."""
import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/jump_contract.py"
spec = importlib.util.spec_from_file_location("jump_contract_test", file)
contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)


def report():
    result = dict(status="passed", error=None, enhanced_input_injection=True, native_gas_instance=True,
        player_restored=True, jump_observer_closed=True, cases=[],
        policy_shutdown=dict(active_count=0, scopes_created=7, scopes_closed=7, errors=[]),
        **{name: False for name in contract.FALSE_CLAIMS})
    for name in contract.PLAN:
        sides = {}
        for side, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
            if name == "active-profile-switch": profile = "Python" if side == "blueprint" else "BlueprintFallback"
            sides[side] = dict(active_while_held=True, native_type_preserved=True, landed=True, active_after=False,
                pressed_jump_after=False, peak_rise=70., jump_events=1, intervention=name, input_injections=15,
                profile_after=profile, native_state_stopped_jump=name == "native-state-end")
        result["cases"].append(dict(name=name, **sides, python_counters=dict(activations=1, states_created=1,
            releases_created=1, scopes_created=1, scopes_closed=1, native_ends=int(name != "active-profile-switch"),
            input_releases=int(name in ("release-fast", "release-held", "native-state-end", "repeat-release")),
            state_ended=int(name == "native-state-end"))))
    return result


class JumpContract(unittest.TestCase):
    def test_complete_bounded_matrix(self):
        self.assertEqual(contract.validate(report())["cases"], 7)

    def test_reject_each_unproven_claim(self):
        for claim in contract.FALSE_CLAIMS:
            value = report(); value[claim] = True
            with self.subTest(claim=claim), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_incomplete_or_reordered_matrix(self):
        for cases in (report()["cases"][:-1], list(reversed(report()["cases"]))):
            value = report(); value["cases"] = cases
            with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_no_native_physics_or_duplicate_jump(self):
        for field, replacement in (("peak_rise", float("nan")), ("peak_rise", 0.), ("jump_events", 2),
                                   ("active_while_held", False), ("native_type_preserved", False)):
            value = report(); value["cases"][0]["python"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
        value = report(); value["cases"][0]["python"]["peak_rise"] += 10.
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_early_end_or_profile_switch_not_exercised(self):
        for index, field, replacement in ((0, "intervention", None), (4, "profile_after", "Python"),
                                           (5, "native_state_stopped_jump", False)):
            value = report(); value["cases"][index]["python"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_task_replay_and_scope_leak(self):
        for field, replacement in (("activations", 0), ("releases_created", 2), ("scopes_closed", 0),
                                   ("native_ends", 0), ("input_releases", 2)):
            value = report(); value["cases"][0]["python_counters"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_shutdown_leak_and_unrestored_observer(self):
        for field, replacement in (("active_count", 1), ("scopes_closed", 6), ("errors", ["callback"] )):
            value = report(); value["policy_shutdown"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
        value = report(); value["jump_observer_closed"] = False
        with self.assertRaises(RuntimeError): contract.validate(value)
