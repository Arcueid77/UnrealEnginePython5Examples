"""Exact parent stencil retention plus existing audited hide method only."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
stencil=types.ModuleType('uep_lyra_characters.hero_default_stencil_mixin');stencil.CLASS='Parent';stencil.SELECTOR='UEPHeroDefaultMixinProfile';hiding=types.ModuleType('uep_lyra_characters.equipment_hide_mixin')
def py_stencil(self,TeamId):pass
def bp_stencil(self,TeamId):pass
def py_hide(self):pass
def bp_hide(self):pass
stencil.LyraHeroDefaultStencilPythonProfile=type('SP',(),{'UpdateCustomStencilFromTeamID':py_stencil});stencil.LyraHeroDefaultStencilBlueprintFallbackProfile=type('SB',(),{'UpdateCustomStencilFromTeamID':bp_stencil});hiding.LyraCharacterEquipmentHidePythonProfile=type('HP',(),{'HideEquippedWeapons':py_hide,'UnrelatedChild':lambda self:None});hiding.LyraCharacterEquipmentHideBlueprintFallbackProfile=type('HB',(),{'HideEquippedWeapons':bp_hide,'UnrelatedChild':lambda self:None});spec=importlib.util.spec_from_file_location('uep_lyra_characters._parent_hide_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/hero_default_equipment_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_characters.hero_default_stencil_mixin':stencil,'uep_lyra_characters.equipment_hide_mixin':hiding}):spec.loader.exec_module(policy)
class HeroDefaultEquipmentProfileTests(unittest.TestCase):
    def test_parent_reuses_exact_audited_hide_policy(self):self.assertIs(policy.LyraHeroDefaultEquipmentPythonProfile.HideEquippedWeapons,py_hide);self.assertIs(policy.LyraHeroDefaultEquipmentBlueprintFallbackProfile.HideEquippedWeapons,bp_hide)
    def test_stencil_method_and_unique_selector_remain(self):self.assertIs(policy.LyraHeroDefaultEquipmentPythonProfile.UpdateCustomStencilFromTeamID,py_stencil);self.assertEqual(policy.SELECTOR,'UEPHeroDefaultMixinProfile')
    def test_complete_two_method_families_without_unrelated_child_methods(self):
        for cls in (policy.LyraHeroDefaultEquipmentPythonProfile,policy.LyraHeroDefaultEquipmentBlueprintFallbackProfile):self.assertEqual([n for n,v in vars(cls).items() if callable(v)],['UpdateCustomStencilFromTeamID','HideEquippedWeapons'])
