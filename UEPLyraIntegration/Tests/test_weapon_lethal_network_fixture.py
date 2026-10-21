import ast
import builtins
from pathlib import Path
import symtable
import unittest

ROOT=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons'


class WeaponLethalNetworkFixtureTests(unittest.TestCase):
    def test_native_weapon_observer_globals_resolve(self):
        for name in ('weapon_lethal_network_validation.py','weapon_lethal_network_contract.py'):
            file=ROOT/name;table=symtable.symtable(file.read_text(encoding='utf-8'),str(file),'exec')
            known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for symbol in scope.get_symbols():
                    if symbol.is_global() and symbol.is_referenced() and symbol.get_name() not in known:missing.add(symbol.get_name())
                for child in scope.get_children():check(child)
            check(table);self.assertFalse(missing,sorted(missing))

    def test_weapon_damage_is_not_manufactured_by_fixture(self):
        tree=ast.parse((ROOT/'weapon_lethal_network_validation.py').read_text(encoding='utf-8'))
        methods=[n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='call_function' and n.args and isinstance(n.args[0],ast.Constant)]
        for forbidden in ('BP_ApplyGameplayEffectSpecToTarget','BP_ApplyGameplayEffectSpecToSelf','AssignTagSetByCallerMagnitude','HandleGameplayEvent','BroadcastVerb','HandleVictory','StartPhase','OnRangedWeaponTargetDataReady','K2_ActivateAbility'):
            self.assertNotIn(forbidden,methods)
        self.assertTrue(any(isinstance(n,ast.Attribute) and n.attr=='inject_enhanced_input_for_action' for n in ast.walk(tree)))

    def test_existing_weapon_contract_keys_are_valid(self):
        from uep_lyra_weapons.weapon_ability_fire_contract import WEAPONS
        tree=ast.parse((ROOT/'weapon_lethal_network_validation.py').read_text(encoding='utf-8'))
        keys=[n.slice.value for n in ast.walk(tree) if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='WEAPONS' and isinstance(n.slice,ast.Constant)]
        self.assertTrue(keys)
        self.assertTrue(all(key in WEAPONS for key in keys))

    def test_relay_based_probe_uses_resolved_source_pawn(self):
        tree=ast.parse((ROOT/'weapon_lethal_network_validation.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='self' and n.attr=='pawn' for n in ast.walk(tree)))
