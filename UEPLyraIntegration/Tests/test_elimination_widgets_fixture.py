"""Native list refresh reassigns an item and resets its original delegate timer."""
import ast
from pathlib import Path
import time
import types
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/elimination_widgets_validation.py'


class EliminationFixtureTests(unittest.TestCase):
    def test_expiry_measures_from_latest_assignment_of_same_widget_and_item(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8-sig'));fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='observe');namespace=dict(time=time,require=lambda ok,msg:None if ok else self.fail(msg),count=lambda *args:2)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec'),namespace)
        first,second,widget1,widget2=object(),object(),object(),object();feed=types.SimpleNamespace(get_property=lambda k:types.SimpleNamespace(call_function=lambda *a:1),call_function=lambda *a:None)
        fixture=types.SimpleNamespace(phase='expiry',phase_started=time.monotonic(),samples=lambda:None,items=lambda:[],row={},feed=feed,send=lambda *a:None,enter=lambda *a:None)
        fixture.assignments=[dict(widget=widget1,item=first,time=0.),dict(widget=widget2,item=second,time=0.),dict(widget=widget2,item=second,time=5.9)];fixture.expiries=[dict(widget=widget1,item=first,time=6.),dict(widget=widget2,item=second,time=11.9)]
        namespace['observe'](fixture);self.assertEqual(fixture.row['native_expiry_durations'],[6.,6.]);self.assertTrue(fixture.row['native_expiry_durations_match']);self.assertEqual(fixture.row['native_assignments_including_list_refresh'],3)
