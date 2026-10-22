"""Modeled negative gates; real native travel evidence is collected separately."""
import copy
import unittest
from uep_lyra_weapons import integrated_profile_contract as gate


def report(profile="Python", peer="A"):
    stats = dict(active_count=0, scopes_created=3, scopes_closed=3, errors=[], activations=3, authority_reloads=2)
    value = dict(selected_profile=profile, peer=peer, selectors_restored=True, owned_roots_released=True,
        gameplay_state_written=False, class_families={name: [name+"-class"] for name in gate.FAMILIES}, observations=[],
        shutdown={name: copy.deepcopy(stats) for name in ("reload", "autoreload", "quickslot")})
    for index in range(1 if peer == "B1" else 3):
        for family in gate.FAMILIES:
            row = dict(world_token="world"+str(index), pawn="pawn"+str(index), controller="controller", ability=family+str(index),
                native_class=family+"-class", family=family, profile=profile, authority=peer == "server")
            if family == "fire": row["fire_counts"] = dict(activations=int(profile == "Python")*3, fallback_activations=int(profile == "BlueprintFallback")*3)
            value["observations"].append(row)
    return value


class IntegratedProfileGate(unittest.TestCase):
    def test_original_python_and_rejoined_owner(self):
        for profile in gate.PROFILES:
            for peer in ("server", "A", "B0", "B1"):
                with self.subTest(profile=profile, peer=peer): self.assertEqual(gate.validate(report(profile, peer), profile)["status"], "passed")

    def test_reject_wrong_selector_mixed_instance_and_authority(self):
        for key, replacement in (("profile", "BlueprintFallback"), ("authority", True), ("world_token", ""), ("ability", "")):
            value = report(); value["observations"][0][key] = replacement
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value, "Python")
        with self.assertRaises(RuntimeError): gate.validate(report(), "BlueprintFallback")

    def test_reject_missing_travel_family_and_unreleased_owned_roots(self):
        for key in ("selectors_restored", "owned_roots_released"):
            value = report(); value[key] = False
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value, "Python")
        value = report(); value["observations"] = value["observations"][:4]
        with self.assertRaises(RuntimeError): gate.validate(value, "Python")
        value = report(); value["observations"] = [row for row in value["observations"] if row["family"] != "quickslot"]
        with self.assertRaises(RuntimeError): gate.validate(value, "Python")

    def test_reject_bypassed_policy_or_implicit_original_firing(self):
        for counts in (dict(activations=0, fallback_activations=0), dict(activations=3, fallback_activations=1)):
            value = report()
            for row in value["observations"]:
                if row["family"] == "fire": row["fire_counts"] = counts
            with self.subTest(counts=counts), self.assertRaises(RuntimeError): gate.validate(value, "Python")

    def test_reject_gameplay_write_and_task_shutdown_leaks(self):
        value = report(); value["gameplay_state_written"] = True
        with self.assertRaises(RuntimeError): gate.validate(value, "Python")
        for family in ("reload", "autoreload", "quickslot"):
            for key, replacement in (("active_count", 1), ("scopes_closed", 2), ("errors", ["late callback"])):
                value = report(); value["shutdown"][family][key] = replacement
                with self.subTest(family=family, key=key), self.assertRaises(RuntimeError): gate.validate(value, "Python")
