"""Catch unresolved globals in coupled default-map migration scripts."""
import builtins
from pathlib import Path
import symtable
import unittest
class EditorExperienceFixtureTests(unittest.TestCase):
    def test_editor_experience_scripts_resolve_globals(self):
        root=Path(__file__).resolve().parents[1]
        for path in [root/'Tools/generate_editor_experience_assets.py']+[root/'Overlay/Content/Scripts/uep_lyra_hud'/n for n in ('editor_experience_list_mixin.py','editor_experience_portal_mixin.py','editor_experience_validation.py','editor_experience_contract.py')]:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for s in scope.get_symbols():
                    if s.is_referenced() and s.is_global() and s.get_name() not in known:missing.add(s.get_name())
                for child in scope.get_children():check(child)
            check(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
