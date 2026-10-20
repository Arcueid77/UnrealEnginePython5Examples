"""Check globals in shared policy and three-consumer authoring."""
import builtins
from pathlib import Path
import symtable
import unittest
class UIExperiencePreparationFixtureTests(unittest.TestCase):
    def test_new_scripts_resolve_referenced_globals(self):
        root=Path(__file__).resolve().parents[1]
        for path in [root/'Tools'/n for n in ('generate_ui_experience_preparation_assets.py','generate_ui_preparation_probe.py')]+[root/'Overlay/Content/Scripts/uep_lyra_hud'/n for n in ('experience_preparation_policy.py','ui_preparation_probe_validation.py','ui_preparation_probe_contract.py')]:
            tree=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for s in scope.get_symbols():
                    if s.is_referenced() and s.is_global() and s.get_name() not in known:missing.add(s.get_name())
                for child in scope.get_children():check(child)
            check(tree)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
