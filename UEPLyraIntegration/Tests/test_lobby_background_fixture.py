"""Catch unresolved globals in lobby actor scripts."""
import builtins
from pathlib import Path
import symtable
import unittest
class LobbyBackgroundFixtureTests(unittest.TestCase):
    def test_lobby_scripts_resolve_globals(self):
        root=Path(__file__).resolve().parents[1]
        for path in [root/'Tools/generate_lobby_background_assets.py',root/'Tools/audit_lobby_default_map.py']+[root/'Overlay/Content/Scripts/uep_lyra_hud'/n for n in ('lobby_background_mixin.py','lobby_background_validation.py','lobby_background_contract.py')]:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for s in scope.get_symbols():
                    if s.is_referenced() and s.is_global() and s.get_name() not in known:missing.add(s.get_name())
                for child in scope.get_children():check(child)
            check(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
