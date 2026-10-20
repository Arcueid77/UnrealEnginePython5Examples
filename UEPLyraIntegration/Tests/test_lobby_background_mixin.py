"""Lobby catalog/random/task/delegate continuation order and native messages."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
native=types.ModuleType('unreal_engine');native.find_struct=lambda n:lambda **kw:(n,kw)
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
spec=importlib.util.spec_from_file_location('_lobby_background_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/lobby_background_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)
class LobbyBackgroundPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.load=True;self.choice=1;self.task=object();self.props=dict(EditorOnlyBox=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('box',f,*a))),BoxExtents='extents');self.actor=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=lambda f,*a:self.calls.append(('actor',f,*a)));policy.ue=native;policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.call(n,f,a))
    def set(self,n,v):self.props[n]=v;self.calls.append(('set',n,v))
    def call(self,n,f,args):
        self.calls.append((n,f,*args))
        if f=='ShouldLoadCosmeticBackgrounds':return self.load
        if f=='RandomIntegerInRange':return self.choice
        if f=='CreateLoadingScreenProcessTask':return self.task
    def test_construction_updates_original_editor_box_without_overlap_refresh(self):policy.invoke(self.actor,'construct');self.assertEqual(self.calls,[('box','SetBoxExtent','extents',False)])
    def test_skip_cosmetic_backgrounds_does_not_query_catalog(self):self.load=False;policy.invoke(self.actor,'begin');self.assertEqual(len(self.calls),1)
    def test_enabled_begin_queries_original_catalog_adapter(self):policy.invoke(self.actor,'begin');self.assertEqual(self.calls[-1],('actor',policy.NATIVE['catalog']))
    def test_empty_catalog_prints_only_original_diagnostic(self):policy.invoke(self.actor,'catalog',[]);self.assertEqual(self.calls[0][0:2],('KismetSystemLibrary','PrintString'));self.assertEqual(self.calls[0][3],'No lobby backgrounds found');self.assertFalse(any(c[0]=='actor' for c in self.calls))
    def test_catalog_uses_same_native_inclusive_random_range(self):policy.invoke(self.actor,'catalog',['a','b','c']);self.assertEqual(self.calls[0],('KismetMathLibrary','RandomIntegerInRange',0,2))
    def test_selected_id_stored_before_loading_task_and_native_primary_request(self):policy.invoke(self.actor,'catalog',['a','b']);self.assertEqual(self.calls[-3:],[('set','BackgroundToLoad','b'),('actor','ShowLoadingScreen'),('actor',policy.NATIVE['asset'])])
    def test_loaded_asset_uses_original_native_soft_world_and_actor_transform(self):policy.invoke(self.actor,'asset_ready',object());self.assertEqual(self.calls,[('actor',policy.NATIVE['level'])])
    def test_success_binds_original_loaded_then_shown_delegates(self):policy.invoke(self.actor,'instance_result',True,object());self.assertEqual(self.calls,[('actor',policy.NATIVE['bind'])])
    def test_instance_failure_logs_then_schedules_original_hide(self):policy.invoke(self.actor,'instance_result',False,None);self.assertEqual(self.calls[0][3],'Level instance load failed');self.assertEqual(self.calls[-1],('actor','HideLoadingScreen'))
    def test_shown_logs_before_hide_and_loaded_does_not_hide(self):policy.invoke(self.actor,'loaded');self.assertEqual(self.calls[-1][3],'Lobby background loaded');self.calls=[];policy.invoke(self.actor,'shown');self.assertEqual(self.calls[0][3],'Lobby background shown');self.assertEqual(self.calls[-1],('actor','HideLoadingScreen'))
    def test_show_creates_native_loading_task_with_exact_reason_and_stores_identity(self):policy.invoke(self.actor,'show');self.assertEqual(self.calls,[('LoadingProcessTask','CreateLoadingScreenProcessTask',self.actor,'Loading Cosmetic Background'),('set','LoadingScreenTask',self.task)])
    def test_hide_and_release_use_original_native_delay_and_current_task_unregister(self):policy.invoke(self.actor,'hide');policy.invoke(self.actor,'release');self.assertEqual(self.calls,[('actor',policy.NATIVE['delay']),('actor',policy.NATIVE['unregister'])])
    def test_complete_profiles_own_all_typed_gate_methods(self):
        for p in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraLobbyBackground'+p+'Profile');self.assertEqual({f.override for f in vars(cls).values() if callable(f)},set(policy.GATES.values()))
