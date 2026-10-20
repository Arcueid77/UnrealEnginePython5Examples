"""CDO subobject order may vary; actual property and array changes must not pass."""
import ast
from pathlib import Path
import unittest

source=Path(__file__).resolve().parents[1]/'Tools/generate_shooter_ai_assets.py';tree=ast.parse(source.read_text(encoding='utf-8-sig'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='defaults');namespace={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),namespace)


class AICdoCanonicalTests(unittest.TestCase):
    def value(self,text):namespace['snapshot']=lambda *a:text;return namespace['defaults'](None,'probe')
    def test_sibling_subobject_declaration_order_is_not_semantic(self):
        a='Begin Object Name="Root"\nBegin Object Name="A"\nX=1\nEnd Object\nBegin Object Name="B"\nY=2\nEnd Object\nEnd Object';b='Begin Object Name="Root"\nBegin Object Name="B"\nY=2\nEnd Object\nBegin Object Name="A"\nX=1\nEnd Object\nEnd Object';self.assertEqual(self.value(a),self.value(b))
    def test_nested_property_change_is_not_ignored(self):
        a='Begin Object Name="Root"\nBegin Object Name="A"\nX=1\nEnd Object\nEnd Object';self.assertNotEqual(self.value(a),self.value(a.replace('X=1','X=2')))
    def test_array_order_and_omitted_properties_do_not_match(self):
        a='Begin Object Name="Root"\nKeys(0)=A\nKeys(1)=B\nEnd Object';b='Begin Object Name="Root"\nKeys(0)=B\nKeys(1)=A\nEnd Object';self.assertNotEqual(self.value(a),self.value(b));self.assertNotEqual(self.value(a),self.value(a.replace('Keys(1)=B\n','')))
