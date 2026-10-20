"""Keep the reflected brush dimension type; settle before short UMG playback."""
import ast
from pathlib import Path
import types
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/scoreboard_style_validation.py'


class NativeSize:
    X=0.
    Y=0.


class Brush:
    def __init__(self):self._size=NativeSize()
    @property
    def ImageSize(self):return self._size
    @ImageSize.setter
    def ImageSize(self,value):
        if not isinstance(value,NativeSize):raise ValueError('wrong reflected struct type')
        self._size=value


class ScoreboardStyleFixtureTests(unittest.TestCase):
    def test_seed_preserves_original_reflected_image_size_structure(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8-sig'));fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='seed');namespace=dict(ue=types.SimpleNamespace(find_struct=lambda name:lambda **kw:types.SimpleNamespace(**kw)));exec(compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec'),namespace)
        brush=Brush();initial=brush.ImageSize;widget=types.SimpleNamespace(get_property=lambda name:types.SimpleNamespace(call_function=lambda *args:None));fixture=types.SimpleNamespace(brush_state=lambda *args:brush)
        namespace['seed'](fixture,widget,'TeamIcon',False);self.assertIs(brush.ImageSize,initial);self.assertEqual((initial.X,initial.Y),(137.,43.))
    def test_short_activation_checks_use_native_animation_position(self):
        source=SOURCE.read_text(encoding='utf-8-sig');self.assertIn("self.enter('settle-activation')",source);self.assertIn("self.animation_state()['position']<.05",source)
