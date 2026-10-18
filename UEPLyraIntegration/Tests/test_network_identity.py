"""Lossless cross-peer identity models only; no native networking here."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location("_network_identity_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/network_identity.py")
identity=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":types.ModuleType("unreal_engine")}): spec.loader.exec_module(identity)


class TestNetworkIdentity(unittest.TestCase):
    def value(self,wire="18446744073709551614",transport="Legacy",**extra): return dict(valid=True,wire_id=wire,transport=transport,**extra)
    def test_64_bit_wire_id_lossless(self): self.assertEqual(identity.key(self.value())[1],"18446744073709551614")
    def test_peer_local_names_and_clocks_are_not_identity(self):
        self.assertTrue(identity.same(self.value(object_path="server-pawn",world_seconds=99.),self.value(object_path="client-pawn",world_seconds=2.)))
    def test_same_name_different_wire_is_not_same_actor(self): self.assertFalse(identity.same(self.value("2",object_path="pawn"),self.value("4",object_path="pawn")))
    def test_transport_is_part_of_wire_namespace(self): self.assertFalse(identity.same(self.value("2","Legacy"),self.value("2","Iris")))
    def test_two_invalid_identities_do_not_match(self): self.assertFalse(identity.same(dict(valid=False),dict(valid=False)))
    def test_unassigned_not_promoted_to_a_key(self): self.assertIsNone(identity.key(dict(valid=False,wire_id="2",transport="Legacy")))
    def test_float_id_rejected(self):
        with self.assertRaises(ValueError): identity.key(self.value(18446744073709551614.))
    def test_zero_valid_id_rejected(self):
        with self.assertRaises(ValueError): identity.key(self.value("0"))
    def test_missing_transport_rejected(self):
        with self.assertRaises(ValueError): identity.key(self.value("2",None))
    def test_native_dto_read_only_conversion(self):
        data=types.SimpleNamespace(bValid=True,Transport="Iris",WireId="18446744073709551614",ObjectPath="object",WorldPath="world",DriverPath="driver",LocalRole=1,WorldSeconds=2.,ActorAgeSeconds=1.)
        with patch.dict(sys.modules,{"unreal_engine":types.SimpleNamespace(find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda name,value:data)))}):
            self.assertEqual(identity.key(identity.read(object())),("Iris","18446744073709551614"))
    def test_missing_compiled_module_not_silently_accepted(self):
        with patch.dict(sys.modules,{"unreal_engine":types.SimpleNamespace(find_class=lambda name:None)}):
            with self.assertRaisesRegex(RuntimeError,"compiled"): identity.read(None)
