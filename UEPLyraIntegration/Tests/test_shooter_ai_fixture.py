"""Catch unresolved globals in the new runtime/authoring files before native boot."""
import builtins
from pathlib import Path
import symtable
import unittest


class ShooterFixtureGlobalsTests(unittest.TestCase):
    def test_new_ai_scripts_have_no_unbound_global_references(self):
        root=Path(__file__).resolve().parents[1]
        files=[root/'Overlay/Content/Scripts/uep_lyra_world'/n for n in ('shooter_ai_mixin.py','shooter_ai_validation.py','shooter_ai_contract.py')]+[root/'Tools'/n for n in ('generate_shooter_ai_assets.py','audit_shooter_ai.py')]
        for path in files:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for symbol in scope.get_symbols():
                    if symbol.is_referenced() and symbol.is_global() and symbol.get_name() not in known:missing.add(symbol.get_name())
                for child in scope.get_children():check(child)
            check(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
