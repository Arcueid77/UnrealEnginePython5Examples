"""Extracted native fixture ownership models; not real equipment evidence."""
import ast
from pathlib import Path
import types
import unittest
from uep_lyra_abilities.reload_magazine_contract import require


def extracted(file, name, namespace):
    path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities"/file
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(nodes) == 1, "select one native fixture method")
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(path), "exec"), namespace)
    return namespace[name]


class ReloadWeaponFixture(unittest.TestCase):
    def setUp(self):
        self.calls, self.slots, self.items, self.role = [], ["pistol", "owned", None], ["pistol", "owned"], 3
        def inventory(name, *args):
            self.calls.append((name, args))
            if name == "GetAllItems": return list(self.items)
            if name == "RemoveItemInstance": self.items.remove(args[0])
        def quickbar(name, *args):
            self.calls.append((name, args))
            if name == "GetSlots": return list(self.slots)
            if name == "RemoveItemFromSlot": self.slots[args[0]] = None
        self.controller = types.SimpleNamespace(call_function=lambda name: self.role)
        self.restore = extracted("reload_weapon_fixture.py", "restore", dict(require=require, valid=lambda value: value is not None,
            path=lambda value: value, services=lambda owner: (types.SimpleNamespace(call_function=inventory), types.SimpleNamespace(call_function=quickbar)),
            restored=lambda owner, state: self.items == ["pistol"] and self.slots == ["pistol", None, None]))
        self.state = dict(original_inventory=dict(active=0), slot=1, owned_item="owned")

    def test_restores_only_owned_temporary_item_and_keeps_original_identity(self):
        self.restore(self.controller, self.state)
        self.assertEqual(self.items, ["pistol"]); self.assertEqual(self.slots, ["pistol", None, None])
        self.assertIn(("SetActiveSlotIndex", (0,)), self.calls)

    def test_client_never_writes_authority_inventory(self):
        self.role = 2
        with self.assertRaises(RuntimeError): self.restore(self.controller, self.state)
        self.assertEqual(self.calls, [])

    def test_foreign_slot_replacement_is_not_deleted(self):
        self.slots[1] = "foreign"
        with self.assertRaises(RuntimeError): self.restore(self.controller, self.state)
        self.assertEqual(self.slots[1], "foreign"); self.assertEqual(self.items, ["pistol", "owned"])

    def test_foreign_inventory_addition_is_preserved_and_restore_rejected(self):
        self.items.append("foreign")
        with self.assertRaises(RuntimeError): self.restore(self.controller, self.state)
        self.assertEqual(self.items, ["pistol", "foreign"])

    def test_restore_is_idempotent_after_owned_item_removed(self):
        self.restore(self.controller, self.state); self.restore(self.controller, self.state)
        self.assertEqual(sum(name == "RemoveItemInstance" for name, args in self.calls), 1)

    def test_initial_ammo_respects_original_small_magazine_capacity(self):
        initial = extracted("reload_magazine_validation.py", "initial_ammo", {})
        owner = types.SimpleNamespace(name="partial-limited-spare", capacity=4)
        self.assertEqual(initial(owner), (3, 4, 3))
        owner.name = "repeat-partial"; self.assertEqual(initial(owner), (2, 4, 8))
        owner.name, owner.capacity = "partial-limited-spare", 12; self.assertEqual(initial(owner), (5, 12, 3))
        owner.capacity = 1; self.assertEqual(initial(owner), (0, 1, 3))
        owner.name = "repeat-partial"; self.assertEqual(initial(owner), (0, 1, 2))
        owner.name = "no-spare-refused"; self.assertEqual(initial(owner), (0, 1, 0))

    def test_family_server_uses_verified_pawn_world_not_partition_world_inventory(self):
        import copy
        calls, writes, world = [], [], object()
        pawn = types.SimpleNamespace(get_world=lambda: world)
        native = types.SimpleNamespace(find_object=lambda path: pawn, find_class=lambda name: "native-controller-class")
        owner = types.SimpleNamespace(root=Path("fixture"), run="run", weapon="rifle", weapon_fixtures={"A": {}, "B0": {}},
            observe_equipment=False, equipment_observer=None,
            weapon_controllers={"A": "controller-a", "B0": "controller-b"}, report=dict(native_playing_gate=dict(stable_authority_pawns=[[250, "actual-pawn"]])),
            statics=types.SimpleNamespace(call_function=lambda *args: calls.append(args) or ([],)))
        method = extracted("reload_magazine_network_validation.py", "prepare_weapons", dict(require=require, ue=native,
            valid=lambda value: value is not None, PEERS=("A", "B0"), copy=copy,
            read_json=lambda path: dict(run_id="run", player_id=250 if path.name.startswith("A-") else 251),
            capture=lambda controller: dict(definition="native-ID_Rifle"),
            weapons=types.SimpleNamespace(WEAPONS=dict(rifle=(None, None, "ID_Rifle"))), atomic_write=lambda *args: writes.append(args)))
        method(owner)
        self.assertIs(owner.world, world); self.assertIs(calls[0][1], world)
        self.assertTrue(owner.weapon_prepared); self.assertEqual(len(writes), 2)
