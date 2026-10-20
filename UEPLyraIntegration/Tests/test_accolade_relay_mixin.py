"""Independent Sequence outputs, native player resolution and payload identity."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n
structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw);structs.LyraNotificationMessage=lambda **kw:types.SimpleNamespace(PayloadMessage='',PayloadObject=None,**kw)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
spec=importlib.util.spec_from_file_location('_accolade_relay_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/accolade_relay_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)


class AccoladePolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.authority=True;self.dedicated=False;self.lyra=True;self.source=object();self.verb=object()
        self.owner=types.SimpleNamespace(call_function=lambda fn:self.authority);self.ps=types.SimpleNamespace(is_a=lambda cls:self.lyra,call_function=lambda f,*a:self.calls.append(('player',f,*a)));self.resolved=[self.ps,self.ps]
        self.actor=types.SimpleNamespace(call_function=self.actor_call);self.payload=types.SimpleNamespace(Instigator=self.source,Target=object(),Verb=self.verb,Magnitude=-999.)
        policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.backend(n,f,a))
    def actor_call(self,f,*a):
        if f=='GetOwner':return self.owner
        self.calls.append(('actor',f,*a))
    def backend(self,n,f,args):
        if f=='GetPlayerStateFromObject':self.calls.append(('resolve',args[0]));return self.resolved.pop(0)
        if f=='IsDedicatedServer':self.calls.append(('dedicated-query',));return self.dedicated
    def test_authority_resolves_for_client_rpc_then_independently_for_cosmetics(self):
        self.assertIs(policy.received(self.actor,self.payload),False);self.assertEqual([x[:2] for x in self.calls],[('resolve',self.source),('player','ClientBroadcastMessage'),('dedicated-query',),('resolve',self.source),('actor',policy.BROADCAST)]);self.assertIs(self.calls[1][-1],self.payload)
    def test_second_native_resolver_result_is_not_replaced_with_first_cached_player(self):
        other=object();self.resolved=[self.ps,other];policy.received(self.actor,self.payload);self.assertIs(self.calls[-1][-1].TargetPlayer,other)
    def test_dedicated_authority_only_forwards_original_payload(self):
        self.dedicated=True;policy.received(self.actor,self.payload);self.assertEqual([x[0] for x in self.calls],['resolve','player','dedicated-query']);self.assertIs(self.calls[1][-1],self.payload)
    def test_remote_cosmetics_resolve_once_without_client_rpc(self):
        self.authority=False;policy.received(self.actor,self.payload);self.assertEqual([x[0] for x in self.calls],['dedicated-query','resolve','actor'])
    def test_remote_still_obeys_cosmetic_macro_on_dedicated_world(self):
        self.authority=False;self.dedicated=True;policy.received(self.actor,self.payload);self.assertEqual(self.calls,[('dedicated-query',)])
    def test_failed_lyra_cast_still_emits_notification_to_valid_plain_player(self):
        self.lyra=False;policy.received(self.actor,self.payload);self.assertFalse(any(x[0]=='player' for x in self.calls));self.assertIs(self.calls[-1][-1].TargetPlayer,self.ps)
    def test_null_resolver_still_broadcasts_null_target(self):
        self.resolved=[None,None];policy.received(self.actor,self.payload);self.assertIsNone(self.calls[-1][-1].TargetPlayer);self.assertEqual(policy.evidence(self.actor)['diagnostic_fallbacks'],0)
    def test_notification_preserves_opaque_verb_and_original_empty_payload_defaults(self):
        policy.received(self.actor,self.payload);message=self.calls[-1][-1];self.assertIs(message.PayloadTag,self.verb);self.assertEqual(message.TargetChannel.TagName,policy.ROOT);self.assertEqual(message.PayloadMessage,'');self.assertIsNone(message.PayloadObject)
    def test_null_source_is_resolved_by_native_helper_without_prefilter(self):
        self.payload.Instigator=None;self.resolved=[None,None];policy.received(self.actor,self.payload);self.assertEqual([x for x in self.calls if x[0]=='resolve'],[('resolve',None),('resolve',None)])
    def test_missing_owner_returns_to_original_before_side_effects(self):
        self.owner=None;self.assertIs(policy.received(self.actor,self.payload),True);self.assertFalse(self.calls)
    def test_fallback_only_requests_original_graph(self):
        self.assertIs(policy.LyraAccoladeRelayBlueprintFallbackProfile.Received(self.actor,self.payload),True);self.assertFalse(self.calls)
