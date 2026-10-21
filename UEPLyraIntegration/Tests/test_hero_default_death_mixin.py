"""Parent continuation name stays separate from the existing Shooter child."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch

class HeroDefaultDeathProfileTests(unittest.TestCase):
    def test_retains_three_audited_methods_and_unique_native_continuation(self):
        parent=types.ModuleType('uep_lyra_characters.hero_default_ragdoll_mixin');parent.CLASS='Parent';parent.SELECTOR='UEPHeroDefaultMixinProfile';death=types.ModuleType('uep_lyra_characters.death_started_mixin');death.BOUND_EVENT='HealthBoundEvent'
        for name in ('evidence','trace','stamp','resume'):setattr(death,name,lambda *a:None)
        expected={}
        for suffix in ('Python','BlueprintFallback'):
            methods={n:(lambda self:None) for n in ('UpdateCustomStencilFromTeamID','HideEquippedWeapons','Ragdoll')};expected[suffix]=methods;setattr(parent,'LyraHeroDefaultRagdoll'+suffix+'Profile',type('Parent',(),methods))
        ue=types.ModuleType('unreal_engine');classes=types.ModuleType('unreal_engine.classes');classes.Actor=type('Actor',(),{});structs=types.ModuleType('unreal_engine.structs');structs.LatentActionInfo=type('LatentActionInfo',(),{});valid=types.ModuleType('uep_lyra_world.effect_pad_mixin');valid.valid=lambda a:True
        spec=importlib.util.spec_from_file_location('uep_lyra_characters._parent_death_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/hero_default_death_mixin.py');module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'unreal_engine':ue,'unreal_engine.classes':classes,'unreal_engine.structs':structs,'uep_lyra_characters.hero_default_ragdoll_mixin':parent,'uep_lyra_characters.death_started_mixin':death,'uep_lyra_world.effect_pad_mixin':valid}):spec.loader.exec_module(module)
        self.assertEqual(module.RESUME,'UEPHeroDefaultAfterDeathDelay')
        for suffix,methods in expected.items():
            cls=getattr(module,'LyraHeroDefaultDeath'+suffix+'Profile');self.assertEqual(len([v for v in vars(cls).values() if callable(v)]),5)
            for name,method in methods.items():self.assertIs(getattr(cls,name),method)
            self.assertEqual(cls.PythonDeathStarted.override,'HealthBoundEvent');self.assertEqual(cls.PythonAfterDeathDelay.override,module.RESUME)
