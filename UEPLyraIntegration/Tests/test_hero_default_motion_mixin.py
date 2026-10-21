"""Parent server gate, deferred construction order and exact interface payload."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch

def load():
    native=types.ModuleType('unreal_engine');enums=types.ModuleType('unreal_engine.enums');enums.ESpawnActorScaleMethod=types.SimpleNamespace(OverrideRootScale=1);enums.ESpawnActorCollisionHandlingMethod=types.SimpleNamespace(Undefined=0);enums.EAttachmentRule=types.SimpleNamespace(KeepRelative=0);native.FVector=lambda *a:a;native.FRotator=lambda:();native.load_class=lambda p:p
    prior=types.ModuleType('uep_lyra_characters.hero_default_death_mixin');prior.CLASS='Parent';prior.SELECTOR='UEPHeroDefaultMixinProfile';methods={n:(lambda self:None) for n in ('UpdateCustomStencilFromTeamID','HideEquippedWeapons','Ragdoll','PythonDeathStarted','PythonAfterDeathDelay')}
    for suffix in ('Python','BlueprintFallback'):setattr(prior,'LyraHeroDefaultDeath'+suffix+'Profile',type('Prior',(),methods))
    validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda a:a is not None;spec=importlib.util.spec_from_file_location('uep_lyra_characters._motion_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/hero_default_motion_mixin.py');module=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.enums':enums,'uep_lyra_characters.hero_default_death_mixin':prior,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(module)
    return module,methods

class HeroDefaultMotionTests(unittest.TestCase):
    def setUp(self):
        self.policy,self.methods=load();self.calls=[];self.server=False;self.data={'FootStep':None,'Mesh':'stored-mesh'};self.foot=types.SimpleNamespace(set_property=lambda k,v:self.calls.append(('set-foot',k,v)),call_function=lambda *a:self.calls.append(('foot',*a)))
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=lambda k,v:self.data.__setitem__(k,v));self.args=tuple(object() for _ in range(12))
        def call(name,*a):
            self.calls.append(('native',name,*a))
            return self.server if name=='IsServer' else self.foot if name=='BeginDeferredActorSpawnFromClass' else 'identity' if name=='MakeTransform' else None
        self.policy.lib=lambda name:types.SimpleNamespace(call_function=call)
    def test_server_does_not_read_or_spawn_footstep(self):
        self.server=True;self.policy.LyraHeroDefaultMotionPythonProfile.AnimMotionEffect(self.actor,*self.args);self.assertEqual([c[1] for c in self.calls],['IsServer']);self.assertIsNone(self.data['FootStep'])
    def test_client_sets_exposed_properties_before_finish_then_reuses(self):
        for _ in range(2):self.policy.LyraHeroDefaultMotionPythonProfile.AnimMotionEffect(self.actor,*self.args)
        names=[c[1] for c in self.calls];self.assertLess(names.index('Skeletal Mesh Component'),names.index('FinishSpawningActor'));self.assertLess(names.index('FootStepRightFootBone'),names.index('FinishSpawningActor'));self.assertEqual(names.count('BeginDeferredActorSpawnFromClass'),1);self.assertEqual(names.count('K2_AttachToComponent'),1);self.assertEqual([c[2:] for c in self.calls if c[:2]==('foot','AnimMotionEffect')],[self.args,self.args]);self.assertIs(self.data['FootStep'],self.foot)
    def test_retains_exact_five_prior_methods(self):
        for cls in (self.policy.LyraHeroDefaultMotionPythonProfile,self.policy.LyraHeroDefaultMotionBlueprintFallbackProfile):
            for name,fn in self.methods.items():self.assertIs(getattr(cls,name),fn)
