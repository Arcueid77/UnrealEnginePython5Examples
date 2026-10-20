"""Resolve globals in the coupled StateTree migration and runtime fixture."""
import builtins
from pathlib import Path
import symtable
import unittest

class ExplorerStateFixtureTests(unittest.TestCase):
    def test_explorer_scripts_resolve_globals(self):
        root=Path(__file__).resolve().parents[1]
        for path in [root/'Tools/generate_explorer_state_assets.py']+[root/'Overlay/Content/Scripts/uep_lyra_world'/n for n in ('explorer_state_mixin.py','explorer_state_validation.py','explorer_state_contract.py')]:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for symbol in scope.get_symbols():
                    if symbol.is_referenced() and symbol.is_global() and symbol.get_name() not in known:missing.add(symbol.get_name())
                for child in scope.get_children():check(child)
            check(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
