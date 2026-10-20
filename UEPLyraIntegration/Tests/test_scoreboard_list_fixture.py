"""Destroyed UObject wrappers must not be touched before safe validity checks."""
import ast
from pathlib import Path
import types
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/scoreboard_list_validation.py'


class Destroyed:
    def __getattribute__(self,name):raise RuntimeError('invalid native wrapper')


class ScoreboardListFixtureTests(unittest.TestCase):
    def test_path_does_not_query_destroyed_native_wrapper(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8-sig'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='path');namespace={'policy':types.SimpleNamespace(valid=lambda o:False)};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec'),namespace);self.assertIsNone(namespace['path'](Destroyed()))
