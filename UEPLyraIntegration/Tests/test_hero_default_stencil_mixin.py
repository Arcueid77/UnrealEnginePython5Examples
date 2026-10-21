"""Parent declares only the already-audited stencil method and unique selector."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
fake=types.ModuleType('uep_lyra_characters.stencil_mixin')
def python_stencil(self,TeamId):pass
def fallback_stencil(self,TeamId):pass
fake.LyraCharacterStencilPythonProfile=type('OldPython',(),{'UpdateCustomStencilFromTeamID':python_stencil,'UnrelatedChildMethod':lambda self:None});fake.LyraCharacterStencilBlueprintFallbackProfile=type('OldFallback',(),{'UpdateCustomStencilFromTeamID':fallback_stencil,'UnrelatedChildMethod':lambda self:None})
spec=importlib.util.spec_from_file_location('uep_lyra_characters._parent_stencil_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/hero_default_stencil_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_characters.stencil_mixin':fake}):spec.loader.exec_module(policy)
class HeroDefaultStencilProfileTests(unittest.TestCase):
    def test_parent_reuses_exact_audited_policy(self):self.assertIs(policy.LyraHeroDefaultStencilPythonProfile.UpdateCustomStencilFromTeamID,python_stencil);self.assertIs(policy.LyraHeroDefaultStencilBlueprintFallbackProfile.UpdateCustomStencilFromTeamID,fallback_stencil)
    def test_parent_does_not_copy_unrelated_child_helpers(self):
        for cls in (policy.LyraHeroDefaultStencilPythonProfile,policy.LyraHeroDefaultStencilBlueprintFallbackProfile):self.assertEqual([n for n,v in vars(cls).items() if callable(v)],['UpdateCustomStencilFromTeamID'])
    def test_parent_selector_does_not_shadow_child_owned_name(self):self.assertEqual(policy.SELECTOR,'UEPHeroDefaultMixinProfile');self.assertNotEqual(policy.SELECTOR,'PythonMixinProfile')
