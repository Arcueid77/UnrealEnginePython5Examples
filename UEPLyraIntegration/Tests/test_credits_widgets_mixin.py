"""Original string accumulation, timer routing, scroll reads and visibility rules."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._credits_widgets_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/credits_widgets_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)

class CreditsPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.offset=0.;self.visibility=1;self.data=dict(StudioPeopleString='',ScrollSpeed=1.,EndPointOffset=20.,CurrentPosition=99.);self.scroller=types.SimpleNamespace(call_function=self.scroll);self.bar=types.SimpleNamespace(call_function=self.bar_call);self.data.update(CreditsScroller=self.scroller,TapToggleActionBar=self.bar,BottomActionBar=self.bar);self.w=types.SimpleNamespace(get_property=self.data.get,set_property=self.set_property,call_function=self.call)
    def set_property(self,n,v):self.calls.append(('set',n,v));self.data[n]=v
    def call(self,f,*a):
        if f=='GetCurrentVisibility':return self.visibility!=1
        self.calls.append(('widget',f,*a))
    def scroll(self,f,*a):
        self.calls.append(('scroller',f,*a))
        if f=='GetScrollOffset':return self.offset
        if f=='SetScrollOffset':self.offset=a[0]
        if f=='GetDesiredSize':return types.SimpleNamespace(x=50.,y=321.)
    def bar_call(self,f,*a):
        if f=='GetVisibility':return self.visibility
        self.calls.append(('bar',f,*a))
        if f=='SetVisibility':self.visibility=a[0]
    def test_focus_returns_original_null(self):self.assertEqual(policy.invoke(self.w,'credits','focus'),dict(UseOriginal=False,ReturnValue=None))
    def test_timer_enable_and_disable_choose_only_original_native_adapters(self):
        policy.invoke(self.w,'credits','toggle',True);policy.invoke(self.w,'credits','toggle',False);self.assertEqual(self.calls,[('widget',policy.START),('widget',policy.STOP)])
    def test_activation_resets_before_original_native_delay(self):
        policy.invoke(self.w,'credits','activate');self.assertEqual(self.calls,[('widget','Reset'),('widget',policy.DELAY)])
    def test_reset_only_scrolls_to_zero_then_resets_bar(self):
        self.offset=77.;policy.invoke(self.w,'credits','reset');self.assertEqual(self.calls,[('scroller','SetScrollOffset',0.),('bar','ResetVisibility')]);self.assertEqual(self.data['CurrentPosition'],99.)
    def test_capture_uses_desired_size_height_not_scroll_end_offset(self):
        policy.invoke(self.w,'credits','capture');self.assertEqual(self.data['EndPointOffset'],321.)
    def test_scroll_stores_old_position_sets_new_then_rereads_for_branch(self):
        self.offset=4.;self.data['ScrollSpeed']=2.;policy.invoke(self.w,'credits','scroll');self.assertEqual(self.data['CurrentPosition'],4.);self.assertEqual(self.offset,6.);self.assertEqual([c[1] for c in self.calls],['GetScrollOffset','CurrentPosition','SetScrollOffset','GetScrollOffset'])
    def test_end_stops_timer_before_reset_without_rearming(self):
        self.offset=19.;self.data['ScrollSpeed']=1.;policy.invoke(self.w,'credits','scroll');self.assertEqual(self.calls[-2:],[('widget','ToggleScrollTimer',False),('widget','Reset')])
    def test_raw_negative_speed_is_not_normalized(self):
        self.offset=4.;self.data['ScrollSpeed']=-2.;policy.invoke(self.w,'credits','scroll');self.assertEqual(self.offset,2.)
    def test_construct_appends_one_through_hundred_with_original_crlf_template(self):
        policy.invoke(self.w,'credits','construct');text=self.data['StudioPeopleString'];self.assertEqual(text.count('Credit Person Name '),100);self.assertTrue(text.startswith(policy.PREFIX+'1'+policy.SUFFIX));self.assertTrue(text.endswith(policy.PREFIX+'100'+policy.SUFFIX));self.assertEqual(self.calls[-1],('widget',policy.WRITE))
    def test_reconstruct_keeps_source_append_instead_of_clearing_text(self):
        self.data['StudioPeopleString']='existing';policy.invoke(self.w,'credits','construct');self.assertTrue(self.data['StudioPeopleString'].startswith('existing'));self.assertEqual(len([c for c in self.calls if c[0]=='set']),100)
    def test_visibility_only_collapsed_is_false_even_hidden_counts_true(self):
        for value in range(5):self.visibility=value;self.assertEqual(policy.invoke(self.w,'bar','visible'),dict(UseOriginal=False,IsVisible=value!=1))
    def test_toggle_from_collapsed_shows_but_hidden_collapses(self):
        self.visibility=1;policy.invoke(self.w,'bar','click');self.assertEqual(self.visibility,0);self.visibility=2;policy.invoke(self.w,'bar','click');self.assertEqual(self.visibility,1)
    def test_bar_reset_is_always_collapsed(self):
        self.visibility=0;policy.invoke(self.w,'bar','reset');self.assertEqual(self.visibility,1)
    def test_profiles_do_not_add_deactivation_cleanup_or_new_timer_implementation(self):
        for k,methods in policy.METHODS.items():
            for p in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraCredits'+k.title()+p+'Profile');names={v.override for v in vars(cls).values() if callable(v) and hasattr(v,'override')};self.assertEqual(names,set(policy.GATES[k].values()));self.assertNotIn('BP_OnDeactivated',names)
