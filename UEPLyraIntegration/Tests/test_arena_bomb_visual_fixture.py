import builtins
from pathlib import Path
import symtable
import unittest


class ArenaBombVisualFixtureTests(unittest.TestCase):
    def test_authoring_and_runtime_globals_resolve(self):
        root = Path(__file__).resolve().parents[1]
        files = [root/'Tools'/name for name in ('generate_arena_bomb_visual_assets.py', 'generate_arena_bomb_visual_probe.py')]
        files += [root/'Overlay/Content/Scripts/uep_lyra_world'/('arena_bomb_visual_'+name+'.py') for name in ('mixin', 'validation', 'contract')]
        for file in files:
            table = symtable.symtable(file.read_text(encoding='utf-8'), str(file), 'exec')
            known = set(dir(builtins)) | {'__file__', '__name__', '__package__'} | {s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()}
            missing = set()
            def check(scope):
                for symbol in scope.get_symbols():
                    if symbol.is_global() and symbol.is_referenced() and symbol.get_name() not in known:
                        missing.add(symbol.get_name())
                for child in scope.get_children():
                    check(child)
            check(table)
            with self.subTest(file=file.name):
                self.assertFalse(missing, sorted(missing))
