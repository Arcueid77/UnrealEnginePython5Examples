"""3D list differs from frontend:ShowAll also appends hidden experiences."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.FVector=lambda *a:a
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
spec=importlib.util.spec_from_file_location('_editor_list_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/editor_experience_list_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)
def exp(name,shown,default):return types.SimpleNamespace(name=name,is_a=lambda c:c=='LyraUserFacingExperienceDefinition',get_property=lambda n:{'bShowInFrontEnd':shown,'bIsDefaultExperience':default}[n])
class EditorExperienceListPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.props=dict(AdditionalExperiencesToShow=['extra'],UserFacingExperienceList=[],ExperiencePortals=['old'],ShowAllExperiences=True,PortalSpacing=500.,DefaultSceneRoot=types.SimpleNamespace(call_function=lambda f:'transform'));self.actor=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call,get_actor_rotation=lambda:'rotation');policy.ue=native;policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.math(f,a))
    def set(self,k,v):self.props[k]=v;self.calls.append(('set',k,v))
    def call(self,f,*args):self.calls.append((f,*args));return 'portal'+str(len(self.calls)) if f==policy.NATIVE['spawn'] else None
    def math(self,f,args):self.calls.append((f,*args));return args[-1]
    def test_begin_replaces_catalog_with_additional_entries_without_clearing_portal_cache(self):policy.invoke(self.actor,'begin');self.assertEqual(self.props['UserFacingExperienceList'],['extra']);self.assertEqual(self.props['ExperiencePortals'],['old']);self.assertEqual(self.calls[-1],(policy.NATIVE['load'],))
    def test_visible_defaults_prepend_in_reverse_discovery_order(self):
        a,b=exp('a',True,True),exp('b',True,True);self.assertEqual(policy.filter_experiences([a,b],False,'LyraUserFacingExperienceDefinition'),[b,a])
    def test_showall_includes_hidden_default_and_nondefault_entries(self):
        a,b=exp('a',False,True),exp('b',False,False);self.assertEqual(policy.filter_experiences([a,b],True,'LyraUserFacingExperienceDefinition'),[a,b])
    def test_nonshowall_excludes_hidden_and_nondefault_entries(self):self.assertEqual(policy.filter_experiences([exp('a',False,True),exp('b',True,False)],False,'LyraUserFacingExperienceDefinition'),[])
    def test_invalid_loaded_items_are_ignored(self):self.assertEqual(policy.filter_experiences([None,types.SimpleNamespace(is_a=lambda c:False)],True,'LyraUserFacingExperienceDefinition'),[])
    def test_loaded_defaults_precede_existing_additional_entries_and_other_catalog_entries(self):
        a,b=exp('a',True,True),exp('b',False,False);self.props['UserFacingExperienceList']=['extra'];policy.invoke(self.actor,'loaded',[b,a]);self.assertEqual(self.props['UserFacingExperienceList'],[a,'extra',b])
    def test_three_portals_are_centered_at_minus_spacing_zero_plus_spacing(self):
        values=[exp(str(i),False,False) for i in range(3)];policy.invoke(self.actor,'loaded',values);self.assertEqual([c[-1][0] for c in self.calls if c[0]=='TransformLocation'],[-500.,0.,500.])
    def test_native_spawn_receives_experience_before_creation_and_original_actor_rotation(self):
        value=exp('a',True,True);policy.invoke(self.actor,'loaded',[value]);self.assertEqual(next(c for c in self.calls if c[0]==policy.NATIVE['spawn']),(policy.NATIVE['spawn'],value,(0.,0.,0.),'rotation'))
    def test_portal_cache_accumulates_and_does_not_replace_previous_actors(self):policy.invoke(self.actor,'loaded',[exp('a',True,True)]);self.assertEqual(self.props['ExperiencePortals'][0],'old');self.assertEqual(len(self.props['ExperiencePortals']),2)
