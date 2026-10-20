"""Resolve globals in Explorer behavior/construction production and fixtures."""
import builtins
from pathlib import Path
import symtable,unittest
class ExplorerBehaviorFixtureTests(unittest.TestCase):
    def test_behavior_scripts_resolve_globals(self):
        root=Path(__file__).resolve().parents[1]
        for path in [root/'Tools/generate_explorer_behavior_assets.py']+[root/'Overlay/Content/Scripts/uep_lyra_characters'/n for n in ('explorer_behavior_mixin.py','explorer_behavior_contract.py','explorer_behavior_validation.py')]:
            table=symtable.symtable(path.read_text(encoding='utf-8-sig'),str(path),'exec');known=set(dir(builtins))|{'__file__','__name__','__package__'}|{s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()};missing=set()
            def check(scope):
                for symbol in scope.get_symbols():
                    if symbol.is_referenced() and symbol.is_global() and symbol.get_name() not in known:missing.add(symbol.get_name())
                for child in scope.get_children():check(child)
            check(table)
            with self.subTest(file=path.name):self.assertFalse(missing,sorted(missing))
