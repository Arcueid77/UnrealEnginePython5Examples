"""Authority, dedicated-server, cast, native team and opaque text/tag policy."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
output=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');output.native_outputs=lambda *a:a[-1]
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
spec=importlib.util.spec_from_file_location('_elimination_feed_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/elimination_feed_relay_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':output,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)


class RelayPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.authority=True;self.dedicated=False;self.valid_state=True;self.teams_valid=True;self.player_class_valid=True;self.tag_value=object();self.texts={}
        self.owner=types.SimpleNamespace(call_function=lambda f:self.authority)
        self.state=types.SimpleNamespace(is_a=lambda c:self.valid_state,call_function=lambda f,*a:self.calls.append(('state',f,*a)))
        self.teams=types.SimpleNamespace(call_function=self.find_team);self.actor=types.SimpleNamespace(call_function=self.actor_call);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.backend(n,f,a))
        self.attacker=self.player('a',1);self.attackee=self.player('b',2);self.payload=types.SimpleNamespace(Instigator=self.attacker,Target=self.attackee,InstigatorTags=self.tag_value)
    def player(self,name,team):return types.SimpleNamespace(is_a=lambda c:self.player_class_valid,call_function=lambda f:name if f=='GetPlayerName' else team)
    def actor_call(self,f,*a):
        if f=='GetOwner':return self.owner
        self.calls.append(('actor',f,*a))
    def find_team(self,f,pawn):self.calls.append(('team',pawn));return dict(bIsPartOfTeam=pawn is not None,TeamId=-1 if pawn is None else pawn)
    def backend(self,n,f,args):
        if f=='GetGameState':return self.state
        if f=='IsDedicatedServer':self.calls.append(('dedicated-query',));return self.dedicated
        if f=='GetWorldSubsystem':return self.teams if self.teams_valid else None
        if f=='Conv_StringToText':
            value=('native-text',args[0]);self.texts[args[0]]=value;return value
    def test_authority_multicasts_original_payload_before_native_team_queries_and_feed(self):
        self.assertIs(policy.received(self.actor,self.payload),False);self.assertEqual(self.calls[1],('state','MulticastReliableMessageToClients',self.payload));self.assertEqual(self.calls[2:4],[('team',1),('team',2)])
        self.assertEqual(self.calls[-1],('actor',policy.BROADCAST,self.texts['a'],self.texts['b'],1,2,self.tag_value))
    def test_remote_branch_bypasses_game_state_cast_and_cosmetic_macro(self):
        self.authority=False;self.valid_state=False;self.dedicated=True;policy.received(self.actor,self.payload);self.assertFalse(any(x[0] in ('state','dedicated-query') for x in self.calls));self.assertEqual(self.calls[-1][1],policy.BROADCAST)
    def test_dedicated_server_forwards_even_invalid_cosmetic_players_without_inspecting_them(self):
        self.dedicated=True;self.payload.Instigator=self.payload.Target=None;self.assertIs(policy.received(self.actor,self.payload),False);self.assertEqual(self.calls,[('dedicated-query',),('state','MulticastReliableMessageToClients',self.payload)])
    def test_failed_game_state_cast_stops_before_multicast_and_local_notification(self):
        self.valid_state=False;self.assertIs(policy.received(self.actor,self.payload),False);self.assertFalse(self.calls)
    def test_invalid_cosmetic_player_returns_to_original_before_any_multicast(self):
        self.payload.Instigator=None;self.assertIs(policy.received(self.actor,self.payload),True);self.assertFalse(any(x[0] in ('state','team','actor') for x in self.calls))
    def test_wrong_player_class_preserves_original_diagnostic_path(self):
        self.player_class_valid=False;self.assertIs(policy.received(self.actor,self.payload),True);self.assertEqual(policy.evidence(self.actor)['diagnostic_fallbacks'],1)
    def test_missing_team_subsystem_does_not_partially_duplicate_the_reliable_rpc(self):
        self.teams_valid=False;self.assertIs(policy.received(self.actor,self.payload),True);self.assertFalse(any(x[0]=='state' for x in self.calls))
    def test_missing_owner_returns_to_original_diagnostics(self):
        self.owner=None;self.assertIs(policy.received(self.actor,self.payload),True);self.assertFalse(self.calls)
    def test_valid_pawnless_players_still_emit_unassigned_team_ids(self):
        self.payload.Instigator=self.player('a',None);self.payload.Target=self.player('b',None);policy.received(self.actor,self.payload);self.assertEqual(self.calls[-1][-3:-1],(-1,-1))
    def test_same_player_is_not_filtered_as_an_invalid_elimination(self):
        self.payload.Target=self.attacker;policy.received(self.actor,self.payload);self.assertEqual(self.calls[-1][2:6],(self.texts['a'],self.texts['a'],1,1))
    def test_original_team_id_output_is_used_even_when_success_flag_is_false(self):
        self.teams.call_function=lambda f,pawn:dict(bIsPartOfTeam=False,TeamId=42);policy.received(self.actor,self.payload);self.assertEqual(self.calls[-1][-3:-1],(42,42))
    def test_fallback_uses_original_native_graph_without_side_effects(self):
        self.assertIs(policy.LyraEliminationFeedRelayBlueprintFallbackProfile.Received(self.actor,self.payload),True);self.assertFalse(self.calls)
