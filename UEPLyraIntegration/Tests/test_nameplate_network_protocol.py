"""Reject fake nameplate network claims; real four-process run is separate."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_nameplate_protocol import validate_nameplate, validate_scopes, validate_comparator_roots


class NameplateNetworkGate(unittest.TestCase):
    def setUp(self):
        self.ack = {"player": {"controller_path": "controller", "pawn_path": "pawn", "world_token": "world"}}
        visual = {"name": "One", "visibility": 1, "resource": "/Red", "progress": 1.0}
        descriptor = {"pawn": "pawn", "scene": "capsule"}
        self.value = {"controller": "controller", "pawn": "pawn", "world_token": "world", "production_local_manager": "manager",
            "manager_profile": "Python", "manager_same_class": True, "map_removals_observed": 1, "world_epochs": 2,
            "bp_baseline_epoch_policy": "BP comparator Bind in production native Bind callback; no production replay or value copying",
            "native_bind_pairs": 1,
            "comparator_roots": {"created": 4, "released": 2, "active": 2, "pair_count": 1, "mounts_for_native_construct": True},
            "synthetic_messages": False, "native_state_written": False, "projection_parity_tested": False, "production_lifecycle_replayed": False,
            "descriptors": [{"pawn": "pawn", "native_membership": True, "native_source": True, "python": descriptor, "blueprint": dict(descriptor)}],
            "widgets": [{"widget": "widget", "pawn": "pawn", "profile": "Python", "class": "W_Nameplate_C", "same_class": True,
                         "automatic_native_binding": True, "same_native_bind_comparator": True,
                         "native_health": {"available": True, "maximum": 100.0, "normalized": 1.0, "unavailable_reason": None},
                         "python": visual, "blueprint": dict(visual)}]}
        scope = {"active_count": 0, "errors": [], "scopes_created": 3, "scopes_closed": 3, "helpers_rooted": 3, "helpers_unrooted": 3}
        self.final = {kind: dict(scope) for kind in ("sources", "managers", "widgets")}
        self.final["sources"].update(adds=3, removes=3)
        self.final["widgets"].update(team_proxies_created=3, team_proxies_cancelled=3, init_bound=3, init_unbound=2, init_owner_released=1)
        self.final["native_placement"] = {"asset": "/ShooterCore/Experiences/LAS_ShooterGame_StandardComponents.LAS_ShooterGame_StandardComponents",
            "native_asset_read": True, "asset_modified": False, "rows": {kind: {
                "class": "/Game/UI/Indicators/"+name+"."+name+"_C", "client": True, "server": False}
                for kind, name in (("source", "NameplateSource"), ("manager", "NameplateManagerComponent"))}}

    def test_native_bounded_checkpoint_and_shutdown_pass(self):
        validate_nameplate(self.value, self.ack)
        validate_scopes(self.final, "A")

    def test_cross_owner_or_missing_own_pawn_rejected(self):
        for mutation in (lambda v: v.update(controller="foreign"), lambda v: v.update(world_token="old"),
                         lambda v: v["descriptors"].clear()):
            value = copy.deepcopy(self.value)
            mutation(value)
            with self.assertRaises(RuntimeError):
                validate_nameplate(value, self.ack)

    def test_bp_native_membership_class_and_ui_differences_rejected(self):
        for mutation in (lambda v: v["descriptors"][0].update(native_membership=False),
                         lambda v: v["widgets"][0].update(same_class=False),
                         lambda v: v["widgets"][0]["python"].update(progress=.5)):
            value = copy.deepcopy(self.value)
            mutation(value)
            with self.assertRaises(RuntimeError):
                validate_nameplate(value, self.ack)

    def test_manual_lifecycle_or_state_write_is_not_native_proof(self):
        for flag in ("production_lifecycle_replayed", "native_state_written", "synthetic_messages", "projection_parity_tested"):
            value = copy.deepcopy(self.value)
            value[flag] = True
            with self.assertRaises(RuntimeError):
                validate_nameplate(value, self.ack)

    def test_root_scope_team_and_init_leaks_rejected(self):
        for mutation in (lambda v: v["sources"].update(helpers_unrooted=2), lambda v: v["managers"].update(active_count=1),
                         lambda v: v["widgets"].update(init_unbound=0), lambda v: v["widgets"].update(team_proxies_cancelled=0)):
            final = copy.deepcopy(self.final)
            mutation(final)
            with self.assertRaises(RuntimeError):
                validate_scopes(final, "A")

    def test_dedicated_server_cannot_have_local_ui_scopes(self):
        with self.assertRaises(RuntimeError):
            validate_scopes(self.final, "server")

    def test_dedicated_server_zero_components_requires_real_client_only_policy(self):
        for kind in ("sources", "managers", "widgets"):
            self.final[kind] = {key: ([] if isinstance(value, list) else 0) for key, value in self.final[kind].items()}
        validate_scopes(self.final, "server")
        self.final["native_placement"]["rows"]["source"]["server"] = True
        with self.assertRaises(RuntimeError):
            validate_scopes(self.final, "server")

    def test_uninitialized_native_health_is_explicit_not_fake_live_parity(self):
        unavailable = copy.deepcopy(self.value["widgets"][0])
        unavailable["native_health"] = {"available": False, "maximum": 0.0, "normalized": None,
            "unavailable_reason": "native-attribute-set-not-initialized"}
        self.value["widgets"].append(unavailable)
        validate_nameplate(self.value, self.ack)
        self.value["widgets"] = [unavailable]
        with self.assertRaises(RuntimeError):
            validate_nameplate(self.value, self.ack)  # An all-uninitialized run is not native health proof.

    def test_available_health_difference_is_rejected(self):
        self.value["widgets"][0]["native_health"]["normalized"] = .5
        with self.assertRaises(RuntimeError):
            validate_nameplate(self.value, self.ack)

    def test_comparator_roots_are_accounted_and_must_close(self):
        value = self.value["comparator_roots"]
        validate_comparator_roots(value)
        with self.assertRaises(RuntimeError):
            validate_comparator_roots(value, final=True)
        value.update(released=4, active=0, pair_count=0)
        validate_comparator_roots(value, final=True)
        value["released"] = 3
        with self.assertRaises(RuntimeError):
            validate_comparator_roots(value, final=True)
