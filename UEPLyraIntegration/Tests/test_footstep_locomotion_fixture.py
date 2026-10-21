import ast
import builtins
from pathlib import Path
import symtable
import unittest

ROOT = Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons'


class FootstepLocomotionFixtureTests(unittest.TestCase):
    def test_input_observer_globals_resolve(self):
        for name in ('footstep_locomotion_validation.py', 'footstep_locomotion_contract.py'):
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

    def test_actual_input_does_not_manufacture_animation_or_movement_callbacks(self):
        tree = ast.parse((ROOT/'footstep_locomotion_validation.py').read_text(encoding='utf-8'))
        methods = [node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == 'call_function'
            and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertIn('InjectInputVectorForAction', methods)
        for forbidden in ('PlayAnimation', 'SetAnimationMode', 'SetPosition', 'AnimMotionEffect', 'Notify',
                          'AddMovementInput', 'Input_Move', 'SetMovementMode', 'SetVelocity', 'K2_SetActorLocation'):
            self.assertNotIn(forbidden, methods)
