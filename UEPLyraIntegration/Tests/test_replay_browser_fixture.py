"""Catch unresolved globals in replay migration scripts before native runs."""
import builtins
from pathlib import Path
import symtable
import unittest
class ReplayBrowserFixtureTests(unittest.TestCase):
    def test_replay_scripts_resolve_referenced_globals(self):
        root=Path(__file__).resolve().parents[1];files=[root/'Tools'/n for n in ('audit_replay_ui.py','generate_replay_browser_assets.py')]+[root/'Overlay/Content/Scripts/uep_lyra_hud'/n for n in ('replay_browser_mixin.py','replay_entry_mixin.py','replay_browser_validation.py','replay_browser_contract.py')]
        for path in files:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for s in scope.get_symbols():
                    if s.is_referenced() and s.is_global() and s.get_name() not in known:missing.add(s.get_name())
                for child in scope.get_children():check(child)
            check(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
