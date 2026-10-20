"""Explorer-specific cache field and unchanged helper/team/legacy dispatch."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

methods=('ClearInventory','GetEmoteAudioComponent','SetEmoteAudioComponent','ChangeQuickbarSlot','AddInitialInventory')
helpers=types.ModuleType('uep_lyra_characters.explorer_helpers_mixin');helpers.METHODS=methods
teams=types.ModuleType('uep_lyra_characters.team_cosmetics_mixin');legacy=types.ModuleType('uep_lyra_characters.legacy_player_info_mixin')
for module,names,members in ((helpers,('LyraExplorerHelpersPythonProfile','LyraExplorerHelpersBlueprintFallbackProfile'),methods),(teams,('LyraCharacterTeamPythonProfile','LyraCharacterTeamBlueprintFallbackProfile'),('OnTeamOrCosmeticsChanged',)),(legacy,('LyraCharacterLegacyPlayerInfoPythonProfile','LyraCharacterLegacyPlayerInfoBlueprintFallbackProfile'),('OnRep_PlayerInfo',))):
    for name in names:setattr(module,name,type(name,(),{m:lambda self,*a:None for m in members}))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda *a:None));native.load_object=lambda *a:'parent'
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
spec=importlib.util.spec_from_file_location('uep_lyra_characters._explorer_style_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/explorer_style_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_characters.explorer_helpers_mixin':helpers,'uep_lyra_characters.team_cosmetics_mixin':teams,'uep_lyra_characters.legacy_player_info_mixin':legacy}):spec.loader.exec_module(policy)

class ExplorerStylePolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.local=True;self.material=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append((f,*a)));self.props={policy.FIELD:None,'CameraComponent':types.SimpleNamespace(call_function=lambda f,*a:self.calls.append((f,*a)))}
        self.actor=types.SimpleNamespace(call_function=lambda f:self.local,get_property=lambda n:self.props[n],set_property=lambda n,v:self.props.__setitem__(n,v),call_mixin_original=lambda f,*a:self.calls.append(('original',f,*a)))
        policy.ue=native;native.find_class=lambda n:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.create));native.load_object=lambda *a:'parent'
    def create(self,f,*a):self.calls.append((f,*a));return self.material
    def run_outline(self):policy.LyraExplorerStylePythonProfile.CreateOrUpdateOutlineIfNeeded(self.actor,-3,(.1,.2,.3,1.))
    def test_uses_explorer_cache_name(self):self.assertEqual(policy.FIELD,'MPP_outlineMaterial_0');self.run_outline();self.assertIs(self.props[policy.FIELD],self.material)
    def test_nonlocal_guard_never_creates_or_mutates_material(self):self.local=False;self.run_outline();self.assertEqual(self.calls,[]);self.assertIsNone(self.props[policy.FIELD])
    def test_fresh_native_material_and_blend_precede_parameter_updates(self):
        self.run_outline();self.assertEqual([c[0] for c in self.calls],['CreateDynamicMaterialInstance','AddOrUpdateBlendable','SetScalarParameterValue','SetVectorParameterValue'])
    def test_existing_material_reused_without_adding_another_blend(self):
        self.props[policy.FIELD]=self.material;self.run_outline();self.assertEqual([c[0] for c in self.calls],['SetScalarParameterValue','SetVectorParameterValue'])
    def test_original_scalar_and_vector_names_and_signed_team_preserved(self):
        self.run_outline();self.assertEqual(self.calls[-2],('SetScalarParameterValue','TeamID',-3.));self.assertEqual(self.calls[-1],('SetVectorParameterValue','TeamColor',(.1,.2,.3,1.)))
    def test_blueprint_profile_dispatches_exact_original(self):
        policy.LyraExplorerStyleBlueprintFallbackProfile.CreateOrUpdateOutlineIfNeeded(self.actor,7,'color');self.assertEqual(self.calls,[('original','CreateOrUpdateOutlineIfNeeded',7,'color')])
    def test_exact_eight_methods_are_declared_locally(self):
        for cls in (policy.LyraExplorerStylePythonProfile,policy.LyraExplorerStyleBlueprintFallbackProfile):self.assertEqual({n for n,f in vars(cls).items() if not n.startswith('__') and callable(f)},set(policy.METHODS))
    def test_explorer_grant_and_shared_team_and_legacy_are_preserved(self):
        self.assertIs(vars(policy.LyraExplorerStylePythonProfile)['AddInitialInventory'],vars(helpers.LyraExplorerHelpersPythonProfile)['AddInitialInventory']);self.assertIs(vars(policy.LyraExplorerStylePythonProfile)['OnTeamOrCosmeticsChanged'],vars(teams.LyraCharacterTeamPythonProfile)['OnTeamOrCosmeticsChanged']);self.assertIs(vars(policy.LyraExplorerStylePythonProfile)['OnRep_PlayerInfo'],vars(legacy.LyraCharacterLegacyPlayerInfoPythonProfile)['OnRep_PlayerInfo'])
