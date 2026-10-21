import ast
import builtins
from pathlib import Path
import symtable
import unittest

ROOT = Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons'


class FootstepAnimationFixtureTests(unittest.TestCase):
    def test_observer_globals_resolve(self):
        for name in ('footstep_animation_validation.py', 'footstep_animation_contract.py'):
            file = ROOT/name
            table = symtable.symtable(file.read_text(encoding='utf-8'), str(file), 'exec')
            known = set(dir(builtins)) | {'__file__', '__name__', '__package__'} | {s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()}
            missing = set()
            def check(scope):
                for symbol in scope.get_symbols():
                    if symbol.is_global() and symbol.is_referenced() and symbol.get_name() not in known:
                        missing.add(symbol.get_name())
                for child in scope.get_children():
                    check(child)
            check(table)
            self.assertFalse(missing, sorted(missing))

    def test_no_notify_replay_motion_calls_or_timeline_seeks(self):
        tree = ast.parse((ROOT/'footstep_animation_validation.py').read_text(encoding='utf-8'))
        methods = [node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == 'call_function'
            and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertIn('PlayAnimation', methods)
        for forbidden in ('Notify', 'Received_Notify', 'AnimMotionEffect', 'CallMotion', 'SetPosition', 'SetPositionWithPreviousTime'):
            self.assertNotIn(forbidden, methods)
