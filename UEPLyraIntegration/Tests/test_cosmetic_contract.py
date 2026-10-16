"""Negative report models, not real cosmetic/actor evidence."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_characters import cosmetic_contract as contract


def trial(cls, profile, kind="selection"):
    return dict(kind=kind, profile=profile, chosen_class=cls, native_actor_count=2, pawn="pawn", native_type_preserved=True,
        native_beginplay_observed=True, native_owner_preserved=True, native_cleanup_restored_original_ids=True,
        profile_roundtrip_preserved_part=True, native_part=dict(cls=cls, actor_class=cls, actor="native-body", child="native-child",
            collision_mode=0, actor_collision=False, attached_pawn="pawn"),
        counters=dict(selections=int(profile == "Python" and kind == "selection"), random_selections=int(profile == "Python" and kind == "random")))


def report():
    value = dict(status="passed", error=None, cases=[], random_trials=[], policy_shutdown=dict(errors=[]), original_player_restored=True)
    value.update({key: False for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "animation_assets_modified",
        "part_actors_spawned_by_python", "part_arrays_written", "beginplay_handler_replayed", "rng_seed_or_result_written")})
    for name, parts in contract.PLAN:
        value["cases"].append(dict(name=name, blueprint=trial(parts[2 % len(parts)], "BlueprintFallback"), python=trial(parts[2 % len(parts)], "Python")))
    for index in range(16): value["random_trials"].append(trial((contract.MANNY, contract.QUINN)[index//2 % 2],
        ("BlueprintFallback", "Python")[index % 2], "random"))
    return value


class CosmeticGate(unittest.TestCase):
    def test_full_model(self): self.assertEqual(contract.validate(report())["deterministic_pairs"], 4)

    def test_reject_wrong_mapping_or_native_class(self):
        for field, replacement in (("chosen_class", "wrong"), ("native_type_preserved", False), ("native_owner_preserved", False)):
            value = report(); value["cases"][0]["python"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_body_spawn_collision_or_attachment_loss(self):
        for field, replacement in (("actor", None), ("actor_collision", True), ("collision_mode", 1), ("attached_pawn", "foreign")):
            value = report(); value["cases"][0]["python"]["native_part"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_unrestored_ids_or_profile_replay(self):
        for field in ("native_cleanup_restored_original_ids", "profile_roundtrip_preserved_part"):
            value = report(); value["cases"][0]["python"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_unexercised_random_branch_and_direct_spawn(self):
        value = report()
        for row in value["random_trials"]:
            row["chosen_class"] = contract.MANNY
        with self.assertRaises(RuntimeError): contract.validate(value)
        value = report(); value["part_actors_spawned_by_python"] = True
        with self.assertRaises(RuntimeError): contract.validate(value)
