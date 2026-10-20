"""Explorer empty-loadout animation and original validity/order differences."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

shared=types.ModuleType('uep_lyra_characters.quickbar_input_mixin')
for name in ('LyraCharacterQuickbarPythonProfile','LyraCharacterQuickbarBlueprintFallbackProfile'):
    setattr(shared,name,type(name,(),{m:lambda self,*a:None for m in ('ClearInventory','GetEmoteAudioComponent','SetEmoteAudioComponent','ChangeQuickbarSlot')}))
inventory=types.ModuleType('uep_lyra_characters.inventory_clear_mixin');inventory.components=lambda c:(None,None);inventory.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_characters._explorer_helpers_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/explorer_helpers_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_characters.quickbar_input_mixin':shared,'uep_lyra_characters.inventory_clear_mixin':inventory}):spec.loader.exec_module(policy)

class ExplorerHelpersPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.authority=True;self.controller=object();self.definitions=[]
        self.quick=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append((f,*a)))
        self.manager=types.SimpleNamespace(call_function=self.add)
        self.actor=types.SimpleNamespace(call_function=self.call,call_mixin_original=lambda f:self.calls.append(('original',f)),get_property=lambda n:self.definitions)
        policy.components=lambda c:(self.quick,self.manager)
    def add(self,f,*a):self.calls.append((f,*a));return 'item'+str(len(self.calls))
    def call(self,f,*a):
        self.calls.append((f,*a))
        return self.authority if f=='HasAuthority' else self.controller if f=='GetController' else None
    def run_grant(self):policy.LyraExplorerHelpersPythonProfile.AddInitialInventory(self.actor)
    def test_empty_configuration_calls_original_native_unarmed_layer(self):
        self.run_grant();self.assertEqual(self.calls[-1],(policy.UNARMED,));self.assertFalse(any(c[0]=='SetActiveSlotIndex' for c in self.calls))
    def test_nonempty_configuration_grants_before_slot_and_activates_zero_last(self):
        self.definitions=['pistol','shotgun'];self.run_grant();self.assertEqual([c[0] for c in self.calls[2:]],['AddItemDefinition','AddItemToSlot','AddItemDefinition','AddItemToSlot','SetActiveSlotIndex']);self.assertEqual(self.calls[-1],('SetActiveSlotIndex',0))
    def test_duplicate_definitions_are_not_deduplicated(self):
        self.definitions=['pistol','pistol'];self.run_grant();self.assertEqual(sum(c[0]=='AddItemDefinition' for c in self.calls),2)
    def test_attempts_every_index_without_capacity_filter_or_rollback(self):
        self.definitions=['pistol']*4;self.run_grant();self.assertEqual([c[1] for c in self.calls if c[0]=='AddItemToSlot'],[0,1,2,3])
    def test_remote_authority_path_does_not_resolve_controller_or_grant(self):
        self.authority=False;self.run_grant();self.assertEqual(self.calls,[('HasAuthority',)])
    def test_missing_controller_is_noop(self):
        self.controller=None;self.run_grant();self.assertEqual(len(self.calls),2)
    def test_missing_inventory_does_not_link_unarmed(self):
        self.manager=None;self.run_grant();self.assertEqual(len(self.calls),2)
    def test_missing_quickbar_uses_native_original_including_null_receiver_diagnostics(self):
        self.quick=None;self.run_grant();self.assertEqual(self.calls[-1],('original','AddInitialInventory'));self.assertEqual(policy.evidence(self.actor)['null_quickbar_native_fallbacks'],1)
    def test_blueprint_profile_calls_exact_original(self):
        policy.LyraExplorerHelpersBlueprintFallbackProfile.AddInitialInventory(self.actor);self.assertEqual(self.calls,[('original','AddInitialInventory')])
    def test_exact_four_proven_shared_helpers_are_aliases(self):
        for name in policy.METHODS[:-1]:self.assertIs(vars(policy.LyraExplorerHelpersPythonProfile)[name],vars(shared.LyraCharacterQuickbarPythonProfile)[name])
