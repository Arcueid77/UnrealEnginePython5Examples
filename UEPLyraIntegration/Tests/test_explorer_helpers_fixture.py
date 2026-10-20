"""Catch unresolved globals in the coupled Explorer helper scripts."""
import builtins
from pathlib import Path
import symtable
import unittest
class ExplorerHelpersFixtureTests(unittest.TestCase):
    def test_explorer_helper_scripts_resolve_globals(self):
        root=Path(__file__).resolve().parents[1]
        paths=[root/'Tools'/n for n in ('generate_explorer_character_assets.py','explorer_character_cdo.py','audit_explorer_characters.py')]+[root/'Overlay/Content/Scripts/uep_lyra_characters'/n for n in ('explorer_helpers_mixin.py','explorer_helpers_contract.py','explorer_helpers_validation.py')]
        for path in paths:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for s in scope.get_symbols():
                    if s.is_referenced() and s.is_global() and s.get_name() not in known:missing.add(s.get_name())
                for child in scope.get_children():check(child)
            check(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
