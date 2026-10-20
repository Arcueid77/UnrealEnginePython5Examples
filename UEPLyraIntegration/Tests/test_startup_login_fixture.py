"""Catch missing globals before the startup/login native lane."""
import builtins
from pathlib import Path
import symtable
import unittest


class StartupLoginGlobalsTests(unittest.TestCase):
    def test_new_startup_login_scripts_have_no_unbound_globals(self):
        root=Path(__file__).resolve().parents[1];files=[root/'Overlay/Content/Scripts/uep_lyra_hud'/n for n in ('startup_login_mixin.py','startup_login_validation.py','startup_login_contract.py')]+[root/'Tools/generate_startup_login_assets.py',root/'Tools/audit_startup_login.py']
        for path in files:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for s in scope.get_symbols():
                    if s.is_referenced() and s.is_global() and s.get_name() not in known:missing.add(s.get_name())
                for child in scope.get_children():check(child)
            check(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
