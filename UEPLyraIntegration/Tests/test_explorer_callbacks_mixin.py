"""Keep exact audited callback bodies and the whole twelve-method Profile family."""
import importlib.util
from pathlib import Path
import sys,types,unittest
from unittest.mock import patch

style=types.ModuleType('uep_lyra_characters.explorer_style_mixin');style.METHODS=('ClearInventory','GetEmoteAudioComponent','SetEmoteAudioComponent','ChangeQuickbarSlot','AddInitialInventory','CreateOrUpdateOutlineIfNeeded','OnTeamOrCosmeticsChanged','OnRep_PlayerInfo')
life=types.ModuleType('uep_lyra_characters.lifecycle_mixin');parts=types.ModuleType('uep_lyra_characters.parts_changed_mixin');health=types.ModuleType('uep_lyra_characters.health_changed_mixin');parts.BOUND_EVENT='PartsBound';health.BOUND_EVENT='HealthBound'
for module,names,members in ((style,('LyraExplorerStylePythonProfile','LyraExplorerStyleBlueprintFallbackProfile'),style.METHODS),(life,('LyraCharacterLifecyclePythonProfile','LyraCharacterLifecycleBlueprintFallbackProfile'),('K2_OnReset','K2_OnDeathFinished')),(parts,('LyraCharacterPartsChangedPythonProfile','LyraCharacterPartsChangedBlueprintFallbackProfile'),('PythonCharacterPartsChanged',)),(health,('LyraCharacterHealthChangedPythonProfile','LyraCharacterHealthChangedBlueprintFallbackProfile'),('PythonHealthChanged',))):
    for name in names:
        methods={}
        for method in members:
            def fn(self,*args):return args
            if module in (parts,health):fn.override=module.BOUND_EVENT
            methods[method]=fn
        setattr(module,name,type(name,(),methods))
spec=importlib.util.spec_from_file_location('uep_lyra_characters._explorer_callbacks_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/explorer_callbacks_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_characters.explorer_style_mixin':style,'uep_lyra_characters.lifecycle_mixin':life,'uep_lyra_characters.parts_changed_mixin':parts,'uep_lyra_characters.health_changed_mixin':health}):spec.loader.exec_module(policy)

class ExplorerCallbacksProfileTests(unittest.TestCase):
    def test_exact_twelve_native_targets_are_declared_on_each_own_class(self):
        for cls in (policy.LyraExplorerCallbacksPythonProfile,policy.LyraExplorerCallbacksBlueprintFallbackProfile):self.assertEqual({getattr(fn,'override',name) for name,fn in vars(cls).items() if callable(fn)},set(policy.METHODS))
    def test_prior_eight_helpers_are_preserved_without_rebinding(self):
        for name in style.METHODS:self.assertIs(vars(policy.LyraExplorerCallbacksPythonProfile)[name],vars(style.LyraExplorerStylePythonProfile)[name])
    def test_lifecycle_functions_are_exact_audited_implementations(self):
        for name in ('K2_OnReset','K2_OnDeathFinished'):self.assertIs(vars(policy.LyraExplorerCallbacksPythonProfile)[name],vars(life.LyraCharacterLifecyclePythonProfile)[name])
    def test_original_component_override_declarations_preserved(self):
        self.assertIs(vars(policy.LyraExplorerCallbacksPythonProfile)['PythonCharacterPartsChanged'],vars(parts.LyraCharacterPartsChangedPythonProfile)['PythonCharacterPartsChanged']);self.assertEqual(vars(policy.LyraExplorerCallbacksBlueprintFallbackProfile)['PythonHealthChanged'].override,'HealthBound')
