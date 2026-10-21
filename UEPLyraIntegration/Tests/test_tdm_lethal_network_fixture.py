import ast
import builtins
from pathlib import Path
import symtable
import unittest

ROOT = Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons'


class TDMLethalNetworkFixtureTests(unittest.TestCase):
    def test_native_producer_globals_resolve(self):
        for name in ('tdm_lethal_network_validation.py', 'tdm_lethal_network_contract.py'):
            file = ROOT/name;table = symtable.symtable(file.read_text(encoding='utf-8'), str(file), 'exec')
            known = set(dir(builtins)) | {'__file__', '__name__', '__package__'} | {s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()}
            missing = set()
            def check(scope):
                for symbol in scope.get_symbols():
                    if symbol.is_global() and symbol.is_referenced() and symbol.get_name() not in known:
                        missing.add(symbol.get_name())
                for child in scope.get_children():
                    check(child)
            check(table);self.assertFalse(missing, sorted(missing))

    def test_game_native_damage_does_not_replay_elimination_phase_or_rpc(self):
        tree = ast.parse((ROOT/'tdm_lethal_network_validation.py').read_text(encoding='utf-8'))
        methods = [node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == 'call_function'
            and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertIn('BP_ApplyGameplayEffectSpecToTarget', methods)
        for forbidden in ('BroadcastVerb', 'BroadcastMessage', 'HandleVictory', 'StartPhase', 'ForceGameOver', 'HandleGameplayEvent', 'DamageSelfDestruct'):
            self.assertNotIn(forbidden, methods)
