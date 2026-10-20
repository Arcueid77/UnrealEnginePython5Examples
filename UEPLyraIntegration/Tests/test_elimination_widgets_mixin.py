"""Fixed palette, native hierarchy predicates, current-item expiry and outer."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.load_class=lambda p:p
structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw)
enums=types.ModuleType('unreal_engine.enums');enums.ESlateVisibility=types.SimpleNamespace(Visible=0,Collapsed=1);enums.EUMGSequencePlayMode=types.SimpleNamespace(Forward=0)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._elimination_widgets_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/elimination_widgets_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'unreal_engine.enums':enums,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)


class EliminationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.num=0;self.current=object();self.data={n:self.obj(n) for n in ('ToastListWidget','FeedVisibilityOvr','AttackerName','AttackeeName','AttackerGlow','AttackeeGlow','WeaponGlow','WeaponIconSwitcher',*policy.ICONS)};self.data.update(AttackerTeamId=1,AttackeeTeamId=2,IntroWithTimedOutro=object());self.widget=self.obj('widget',self.data);policy.lib=lambda n:types.SimpleNamespace(call_function=self.library)
        native.new_object=lambda cls,outer:self.new_item(outer)
    def obj(self,name,props=None):return types.SimpleNamespace(get_property=lambda k:(props or {}).get(k),set_property=lambda k,v:self.calls.append((name,'set',k,v)),call_function=lambda f,*a:self.call(name,f,a))
    def new_item(self,outer):self.outer=outer;self.item=self.obj('item');return self.item
    def call(self,n,f,args):
        self.calls.append((n,f,*args))
        if f=='GetNumItems':return self.num
        if f in ('GetDynamicMaterial','GetDynamicFontMaterial'):return self.obj(n+'-MID')
    def library(self,f,*a):
        if f=='HasTag':return any(t==a[1].TagName or t.startswith(a[1].TagName+'.') for t in a[0])
        if f=='GetListItemObject':return self.current
    def test_empty_and_nonempty_overlay_visibility_follow_list_count(self):
        policy.visibility(self.widget);self.assertEqual(self.calls[-1],('FeedVisibilityOvr','SetVisibility',1));self.num=2;policy.visibility(self.widget);self.assertEqual(self.calls[-1],('FeedVisibilityOvr','SetVisibility',0))
    def test_message_allocates_with_feed_outer_and_copies_exact_typed_payload(self):
        payload=object();policy.message(self.widget,payload);self.assertIs(self.outer,self.widget);self.assertEqual(self.calls,[('item','set','Message',payload),('ToastListWidget','AddItem',self.item),('widget','UpdateDisplayVisibility')])
    def test_remove_updates_visibility_after_native_remove(self):
        item=object();policy.remove(self.widget,item);self.assertEqual(self.calls,[('ToastListWidget','RemoveItem',item),('widget','UpdateDisplayVisibility')])
    def test_palette_is_fixed_team_one_active_not_local_team_relative(self):
        policy.colors(self.widget);sets=[x for x in self.calls if x[1]=='SetScalarParameterValue'];self.assertEqual(len(sets),11);self.assertTrue(all(x[-1]==(0. if x[0].startswith('Attackee') else 1.) for x in sets))
    def test_invalid_select_index_preserves_original_diagnostics_before_material_changes(self):
        self.data['AttackerTeamId']=-1;self.assertIs(policy.colors(self.widget),True);self.assertFalse(self.calls)
    def test_icon_priority_uses_native_hierarchical_has_tag(self):
        a,b=object(),object();policy.text(self.widget,a,b,['GameplayEffect.DamageType.Rifle','GameplayEffect.DamageType.Pistol.Child']);self.assertEqual(self.calls[-1],('WeaponIconSwitcher','SetActiveWidget',self.data['Pistol']));self.assertIs(self.calls[0][-1],a);self.assertIs(self.calls[1][-1],b)
    def test_unknown_or_self_destruct_tags_use_original_same_default_icon(self):
        policy.text(self.widget,object(),object(),['Gameplay.Damage.SelfDestruct']);self.assertEqual(self.calls[-1][-1],self.data['SelfElimination'])
    def test_assignment_native_animation_then_original_timer_entry(self):
        payload=types.SimpleNamespace(**{policy.FIELDS['AttackerTeamID']:1,policy.FIELDS['AttackeeTeamID']:2,policy.FIELDS['Attacker']:object(),policy.FIELDS['Attackee']:object(),policy.FIELDS['InstigatorTags']:object()});item=types.SimpleNamespace(get_property=lambda k:payload);policy.assign(self.widget,item)
        self.assertEqual(self.calls[-2],('widget','PlayAnimation',self.data['IntroWithTimedOutro'],0.,1,0,1.,False));self.assertEqual(self.calls[-1],('widget',policy.START))
    def test_expiry_reads_current_item_each_time_and_uses_native_delegate_bridge(self):
        first=self.current;policy.expire(self.widget);self.current=object();policy.expire(self.widget);self.assertEqual(self.calls,[('widget',policy.EMIT,first),('widget',policy.EMIT,self.current)])
    def test_missing_list_does_not_partially_allocate_message_item(self):
        self.data['ToastListWidget']=None;self.assertIs(policy.message(self.widget,object()),True);self.assertFalse(self.calls)
    def test_fallback_leaves_original_business_path_enabled(self):self.assertIs(policy.LyraEliminationEntryBlueprintFallbackProfile.Expire(self.widget),True);self.assertFalse(self.calls)
