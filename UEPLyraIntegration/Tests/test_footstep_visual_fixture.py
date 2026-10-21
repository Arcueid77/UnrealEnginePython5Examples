import ast
import builtins
from pathlib import Path
import symtable
import unittest

ROOT = Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons'


class FootstepVisualFixtureTests(unittest.TestCase):
    def test_capture_globals_resolve(self):
        for name in ('footstep_visual_validation.py', 'footstep_visual_contract.py'):
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

    def test_render_capture_keeps_real_locomotion_entry(self):
        tree = ast.parse((ROOT/'footstep_visual_validation.py').read_text(encoding='utf-8'))
        methods = [node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == 'call_function'
            and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertIn('ExecuteConsoleCommand', methods)
        for forbidden in ('AnimMotionEffect', 'Notify', 'PlayAnimation', 'SetPosition', 'SetVariableFloat', 'SetVariableVec3'):
            self.assertNotIn(forbidden, methods)
