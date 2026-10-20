"""Validate new EQS scripts have defined globals and const Blueprint gate intent."""
import builtins
from pathlib import Path
import symtable
import unittest


class EQSFixtureTests(unittest.TestCase):
    def test_new_eqs_scripts_have_no_unbound_globals(self):
        root=Path(__file__).resolve().parents[1];files=[root/'Overlay/Content/Scripts/uep_lyra_world'/n for n in ('shooter_eqs_mixin.py','shooter_eqs_validation.py','shooter_eqs_contract.py')]+[root/'Tools/generate_shooter_eqs_assets.py']
        for path in files:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def visit(scope):
                for s in scope.get_symbols():
                    if s.is_referenced() and s.is_global() and s.get_name() not in known:missing.add(s.get_name())
                for child in scope.get_children():visit(child)
            visit(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
