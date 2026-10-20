"""New closure scripts must have defined globals before native boot."""
import builtins
from pathlib import Path
import symtable
import unittest


class MacroFixtureGlobalsTests(unittest.TestCase):
    def test_closure_scripts_have_no_unbound_global_references(self):
        root=Path(__file__).resolve().parents[1];files=[root/'Overlay/Content/Scripts/uep_lyra_weapons'/n for n in ('macro_policies.py','macro_closure_validation.py','macro_closure_contract.py')]+[root/'Tools/generate_macro_closure_probe.py']
        for path in files:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def visit(scope):
                for s in scope.get_symbols():
                    if s.is_referenced() and s.is_global() and s.get_name() not in known:missing.add(s.get_name())
                for child in scope.get_children():visit(child)
            visit(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
