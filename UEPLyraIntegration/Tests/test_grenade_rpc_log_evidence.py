"""Native actor/GUID/RPC log correlation cannot be replaced by a body marker."""
import json
import unittest
from uep_lyra_weapons.grenade_rpc_log_evidence import parse

ACTOR = "/ShooterMaps/Maps/L_Expanse.L_Expanse:PersistentLevel.B_Grenade_C_0"
MARKER = "LogPython: UEP_GRENADE_FLIGHT_BODY "+json.dumps(dict(actor=ACTOR, wire_id="18446744073709551600", position=0))
HEADER = "LogNetTraffic:       Actor B_Grenade_C "+ACTOR+":"
RECEIVE = "LogRepTraffic:       Received RPC: Detonate"
CLOSE = "LogNetTraffic: UActorChannel::CleanUp (ChIndex: 13): B_Grenade_C "+ACTOR+" | NetGuid: 18446744073709551600 | Reason: Destroyed"
SEND = "LogNetTraffic:       Sent RPC: B_Grenade_C "+ACTOR+"::Detonate [4.0 bytes]"


class TestGrenadeRPCLogEvidence(unittest.TestCase):
    def test_native_receive_before_body(self):
        row = parse("\n".join((HEADER, RECEIVE, MARKER, CLOSE)))["18446744073709551600"]
        self.assertTrue(row["rpc_before_body"])
        self.assertEqual(row["received_lines"], [2])
    def test_local_body_first_still_requires_actual_later_receive(self):
        row = parse("\n".join((MARKER, HEADER, RECEIVE, CLOSE)))["18446744073709551600"]
        self.assertFalse(row["rpc_before_body"])
    def test_body_marker_alone_is_not_network_proof(self):
        with self.assertRaises(RuntimeError): parse("\n".join((HEADER, MARKER, CLOSE)))
    def test_wrong_actor_context_cannot_claim_receive(self):
        with self.assertRaises(RuntimeError): parse("\n".join((HEADER.replace("B_Grenade_C ", "OtherActor "), RECEIVE, MARKER, CLOSE)))
    def test_wrong_native_guid_cannot_claim_destruction(self):
        with self.assertRaises(RuntimeError): parse("\n".join((HEADER, RECEIVE, MARKER, CLOSE.replace("18446744073709551600", "12"))))
    def test_duplicate_rpc_rejected(self):
        with self.assertRaises(RuntimeError): parse("\n".join((HEADER, RECEIVE, RECEIVE, MARKER, CLOSE)))
    def test_relevancy_close_is_not_server_destruction(self):
        with self.assertRaises(RuntimeError): parse("\n".join((HEADER, RECEIVE, MARKER, CLOSE.replace("Destroyed", "Relevancy"))))
    def test_two_actual_native_sends(self): self.assertEqual(len(parse("\n".join((SEND, SEND, MARKER)), server=True)["18446744073709551600"]["sent_lines"]), 2)
    def test_one_send_is_not_two_clients(self):
        with self.assertRaises(RuntimeError): parse("\n".join((SEND, MARKER)), server=True)
