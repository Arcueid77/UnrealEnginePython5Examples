"""Pure report gate negatives; native extension pool proof runs separately."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import widget_contract as contract


def report():
    result = dict(status="passed", error=None, native_gas_grant_remove=True, actual_extension_point_count=1,
        cdo_defaults_restored=True, original_ability_specs_restored=True, jump_observer_closed=True,
        policy_shutdown=dict(active_count=0, errors=[]), cases=[])
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested",
                  "ability_callbacks_replayed", "assets_saved", "native_ui_pool_written"): result[field] = False
    for name, count in contract.PLAN:
        for profile in ("BlueprintFallback", "Python"):
            result["cases"].append(dict(name=name, profile_at_grant=profile,
                profile_at_remove="Python" if profile == "BlueprintFallback" else "BlueprintFallback",
                native_type_preserved=True, specs_added=1, specs_restored=True, cdo_restored=True,
                entries_added=count, entries_unchanged_after_profile_switch=True, entries_restored_after_remove=True))
    return result


class AbilityWidgetContract(unittest.TestCase):
    def test_complete_native_lifecycle_matrix(self):
        self.assertEqual(contract.validate(report())["cases"], 8)

    def test_reject_missing_point_or_unrestored_state(self):
        for field, replacement in (("actual_extension_point_count", 0), ("cdo_defaults_restored", False),
                                   ("original_ability_specs_restored", False), ("native_gas_grant_remove", False)):
            value = report(); value[field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_deduplication_or_premature_cleanup(self):
        for field, replacement in (("entries_added", 1), ("entries_unchanged_after_profile_switch", False),
                                   ("entries_restored_after_remove", False)):
            value = report(); value["cases"][-1][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_missing_or_wrong_profile(self):
        for field, replacement in (("profile_at_grant", "none"), ("profile_at_remove", "Python"),
                                   ("specs_added", 2), ("native_type_preserved", False)):
            value = report(); value["cases"][-1][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
        value = report(); value["cases"].pop()
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_handler_replay_and_pool_writes(self):
        for field in ("ability_callbacks_replayed", "native_ui_pool_written", "assets_saved", "full_acceptance"):
            value = report(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_shutdown_leaks(self):
        for field, replacement in (("active_count", 1), ("errors", ["lost callback"])):
            value = report(); value["policy_shutdown"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
