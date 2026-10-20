"""Read-only transport observer and server-only native producer boundaries."""
import ast
from pathlib import Path
import unittest
import types

SOURCE=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/notification_relays_network_validation.py'


class NetworkRelayFixtureTests(unittest.TestCase):
    def test_test_verb_producer_exists_only_in_guarded_server_method(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8-sig'));methods={n.name:n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
        senders=[name for name,fn in methods.items() if any(isinstance(n,ast.Constant) and n.value=='BroadcastVerb' for n in ast.walk(fn))]
        self.assertEqual(senders,['send']);send=ast.get_source_segment(SOURCE.read_text(encoding='utf-8-sig'),methods['send']);self.assertIn("self.peer=='server'",send)
    def test_no_rpc_implementation_or_begin_play_is_installed_by_fixture(self):
        source=SOURCE.read_text(encoding='utf-8-sig');self.assertNotIn('ClientBroadcastMessage_Implementation',source);self.assertNotIn('MulticastReliableMessageToClients_Implementation',source);self.assertNotIn("call_function('ReceiveBeginPlay'",source)
    def test_server_restores_live_player_state_before_releasing_clients(self):
        tree=ast.parse(SOURCE.read_text(encoding='utf-8-sig'));fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='server_tick');log=[]
        namespace=dict(PEERS=('A','B0'),atomic_write=lambda path,data:log.append(path.name));exec(compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec'),namespace)
        fixture=types.SimpleNamespace(stage='release',token=lambda name:{'run_id':'run'},cleanup=lambda:log.append('cleanup'),root=Path('/unused'),run='run')
        namespace['server_tick'](fixture);self.assertEqual(log,['cleanup','release.json']);self.assertEqual(fixture.stage,'exits')
