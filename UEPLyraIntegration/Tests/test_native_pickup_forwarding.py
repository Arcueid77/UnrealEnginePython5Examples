"""Forwarding only: native existing-instance AddEntry remains unimplemented."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_native.inventory import InventoryPythonProfile


class RecordingInventory:
    def __init__(self):self.calls=[]
    def call_function(self,*args):self.calls.append(args)


class PickupForwarding(unittest.TestCase):
    def test_templates_precede_instances_and_keep_counts_and_identity(self):
        first,second=object(),object();one,two=object(),object();inventory=RecordingInventory()
        payload=SimpleNamespace(Templates=[SimpleNamespace(ItemDef=first,StackCount=3),SimpleNamespace(ItemDef=second,StackCount=1)],Instances=[SimpleNamespace(Item=one),SimpleNamespace(Item=two)])
        InventoryPythonProfile.UEPGrantPickup(inventory,payload)
        self.assertEqual(inventory.calls,[('AddItemDefinition',first,3),('AddItemDefinition',second,1),('AddItemInstance',one),('AddItemInstance',two)])

    def test_empty_pickup_does_not_call_native_mutators(self):
        inventory=RecordingInventory();InventoryPythonProfile.UEPGrantPickup(inventory,SimpleNamespace(Templates=[],Instances=[]))
        self.assertEqual(inventory.calls,[])
