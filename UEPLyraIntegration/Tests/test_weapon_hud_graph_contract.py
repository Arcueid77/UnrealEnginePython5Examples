"""Reject node/member/edge/default drift while allowing only the Mixin interface."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('weapon_hud_graph_contract',Path(__file__).resolve().parents[1]/'Tools/weapon_hud_graph_contract.py');contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)


def fixture():
    original=dict(blueprints=[]);current=dict(assets={})
    for k in ('hud','pistol','rifle','shotgun'):
        pin=dict(id='p',name='then',direction=1,category='exec',sub_category_object=None,default_value='',default_object=None,links=[]);node=dict(id='node',name='Call',**{'class':'K2Node_CallFunction'},properties=dict(FunctionReference=dict(MemberName='Correct',MemberParent='/Script/Test.Class')),pins=[pin]);original['blueprints'].append(dict(path=k,graphs=[dict(name='EventGraph',nodes=[node])]))
        current['assets'][k]=dict(package=k,graphs=dict(EventGraph=[dict(node='Call',cls='K2Node_CallFunction',function=dict(name='Correct',owner='/Script/Test.Class'),pins=[dict(name='then',direction=1,category='exec',object=None,default='',default_object=None,links=[])])],GetPythonMixinSet=[{},{}],GetPythonMixinProfile=[{},{},{}]))
    return original,current


class WeaponHUDGraphContractTests(unittest.TestCase):
    def test_interface_only_migration_passes(self):self.assertEqual(contract.compare(*fixture())['status'],'passed')
    def test_function_reference_cannot_change_behind_identical_pins(self):
        a,b=fixture();b['assets']['hud']['graphs']['EventGraph'][0]['function']['name']='Wrong';self.assertEqual(contract.compare(a,b)['status'],'failed')
    def test_extra_business_graph_is_not_an_interface(self):
        a,b=fixture();b['assets']['hud']['graphs']['Extra']=[{}];self.assertEqual(contract.compare(a,b)['status'],'failed')
    def test_default_object_type_and_link_changes_are_rejected(self):
        for field,value in (('default','different'),('default_object','asset'),('object','different-class'),('links',['Other.then'])):
            a,b=fixture();b['assets']['hud']['graphs']['EventGraph'][0]['pins'][0][field]=value
            with self.subTest(field=field):self.assertEqual(contract.compare(a,b)['status'],'failed')
    def test_missing_nodes_or_wrong_interface_footprint_rejected(self):
        a,b=fixture();b['assets']['hud']['graphs']['EventGraph']=[];self.assertEqual(contract.compare(a,b)['status'],'failed');a,b=fixture();b['assets']['hud']['graphs']['GetPythonMixinProfile']=[];self.assertEqual(contract.compare(a,b)['status'],'failed')
