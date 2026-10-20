"""Source filter/order, cached widget lifetime, native RNG and opaque IO order."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud'
native=types.ModuleType('unreal_engine');native.find_class=lambda name:name;native.load_class=lambda name:name;native.find_struct=lambda name:lambda:object()
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None
def load(file):
    spec=importlib.util.spec_from_file_location('_test_'+file,ROOT/(file+'.py'));module=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(module)
    return module
policy=load('experience_list_mixin');entry=load('experience_entry_mixin')
def experience(name,default=False,show=True,typed=True):return types.SimpleNamespace(name=name,is_a=lambda cls:typed,get_property=lambda field:{'bIsDefaultExperience':default,'bShowInFrontEnd':show}[field])

class ExperienceListPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.children=[];self.props=dict(ShowAllExperiences=False,ExperienceWidgets=['cached'],UserFacingExperienceList=['old']);self.row=types.SimpleNamespace(call_function=self.row_call);self.props['ExperienceRowBox']=self.row;self.w=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call);policy.ue=native;entry.ue=native;policy.lib=lambda name:types.SimpleNamespace(call_function=lambda fn,*args:self.library(name,fn,args))
    def set(self,name,value):self.props[name]=value;self.calls.append(('set',name,value))
    def call(self,name,*args):
        if name=='GetOwningPlayer':return 'controller'
        self.calls.append(('widget',name,*args))
        if name==policy.NATIVE['focus']:return 'native reply'
    def row_call(self,name,*args):
        self.calls.append(('row',name,*args))
        if name=='ClearChildren':self.children.clear()
        if name=='AddChildToHorizontalBox':self.children.append(args[0])
        if name=='GetChildrenCount':return len(self.children)
    def library(self,owner,name,args):
        if name=='RandomInteger':self.calls.append(('rng',args[0]));return 2
        if name=='Create':return types.SimpleNamespace(call_function=lambda fn,*a:self.calls.append(('tile',fn,*a)))
        raise AssertionError((owner,name,args))
    def test_default_items_prepend_in_reverse_discovery_order(self):
        a,b=experience('a',True),experience('b',True);extra=experience('extra');self.assertEqual(policy.filter_experiences([a,extra,b],False,'class'),[b,a])
    def test_show_all_keeps_nondefault_order_and_hidden_default_remains_hidden(self):
        a,b=experience('a'),experience('b');default=experience('default',True);hidden=experience('hidden',True,False);self.assertEqual(policy.filter_experiences([a,hidden,default,b],True,'class'),[default,a,b])
    def test_invalid_and_wrong_native_class_items_are_skipped(self):self.assertEqual(policy.filter_experiences([None,experience('wrong',typed=False)],True,'class'),[])
    def test_construct_clears_rows_and_experience_list_but_keeps_widget_cache(self):
        policy.invoke(self.w,'construct');self.assertEqual(self.props['ExperienceWidgets'],['cached']);self.assertEqual(self.props['UserFacingExperienceList'],[]);self.assertEqual(self.calls[-1],('widget',policy.NATIVE['load']))
    def test_loaded_appends_cache_before_native_binding_and_focuses_only_first_current_child(self):
        a,b=experience('a',True),experience('b',True);policy.invoke(self.w,'loaded',[a,b]);self.assertEqual(self.props['UserFacingExperienceList'],[b,a]);self.assertEqual(len(self.props['ExperienceWidgets']),3);self.assertEqual(len([c for c in self.calls if c[:2]==('tile','SetUserFocus')]),1);self.assertEqual(self.calls[-1],('widget',policy.NATIVE['complete']));set_index=next(i for i,c in enumerate(self.calls) if c[:2]==('set','ExperienceWidgets'));bind_index=next(i for i,c in enumerate(self.calls) if c[:2]==('widget',policy.NATIVE['bind']));self.assertLess(set_index,bind_index)
    def test_first_uses_original_native_array_access_even_when_empty(self):
        self.props['ExperienceWidgets']=[];policy.invoke(self.w,'first');self.assertEqual(self.calls,[('widget',policy.NATIVE['select'],0)])
    def test_random_uses_native_rng_with_full_accumulated_cache_length(self):
        self.props['ExperienceWidgets']=['old1','old2','new'];policy.invoke(self.w,'random');self.assertEqual(self.calls,[('rng',3),('widget',policy.NATIVE['select'],2)])
    def test_tile_click_forwards_exact_object_through_native_dispatcher(self):
        obj=object();policy.invoke(self.w,'click',obj);self.assertEqual(self.calls,[('widget',policy.NATIVE['notify'],obj)])
    def test_focus_preserves_opaque_native_reply(self):self.assertEqual(policy.invoke(self.w,'focus'),dict(UseOriginal=False,ReturnValue='native reply'))
    def test_entry_stores_definition_before_native_text_art_adapter(self):
        obj=object();entry.invoke(self.w,'set',obj);self.assertEqual(self.calls,[('set','MyUserFacingExperience',obj),('widget',entry.NATIVE['appearance'])])
    def test_entry_click_keeps_native_broadcast(self):
        entry.invoke(self.w,'click');self.assertEqual(self.calls,[('widget',entry.NATIVE['notify'])])
    def test_all_profiles_declare_exact_own_methods(self):
        for module,prefix in ((policy,'LyraExperienceList'),(entry,'LyraExperienceEntry')):
            for p in ('Python','BlueprintFallback'):
                cls=getattr(module,prefix+p+'Profile');self.assertEqual({v.override for v in vars(cls).values() if callable(v)},set(module.GATES.values()))
