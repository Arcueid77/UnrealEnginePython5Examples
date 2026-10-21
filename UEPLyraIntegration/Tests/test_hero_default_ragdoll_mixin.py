"""Parent profile includes only exact audited parent/child function references."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch

class HeroDefaultRagdollProfileTests(unittest.TestCase):
    def test_exact_three_methods_without_unrelated_child_helpers(self):
        equipment=types.ModuleType('uep_lyra_characters.hero_default_equipment_mixin');equipment.CLASS='Parent';equipment.SELECTOR='UEPHeroDefaultMixinProfile';ragdoll=types.ModuleType('uep_lyra_characters.ragdoll_mixin');expected={}
        for suffix in ('Python','BlueprintFallback'):
            methods={name:(lambda self:None) for name in ('UpdateCustomStencilFromTeamID','HideEquippedWeapons','Ragdoll')};expected[suffix]=methods
            setattr(equipment,'LyraHeroDefaultEquipment'+suffix+'Profile',type('Equipment',(),{n:methods[n] for n in methods if n!='Ragdoll'}));setattr(ragdoll,'LyraCharacterRagdoll'+suffix+'Profile',type('Ragdoll',(),{'Ragdoll':methods['Ragdoll'],'UnrelatedChild':lambda self:None}))
        spec=importlib.util.spec_from_file_location('uep_lyra_characters._parent_ragdoll_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/hero_default_ragdoll_mixin.py');module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'uep_lyra_characters.hero_default_equipment_mixin':equipment,'uep_lyra_characters.ragdoll_mixin':ragdoll}):spec.loader.exec_module(module)
        self.assertEqual(module.SELECTOR,'UEPHeroDefaultMixinProfile')
        for suffix,methods in expected.items():
            actual={k:v for k,v in vars(getattr(module,'LyraHeroDefaultRagdoll'+suffix+'Profile')).items() if callable(v)};self.assertEqual(actual,methods)
