"""Grenade UI policy models only; not native GAS/widget acceptance."""
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");structs=types.ModuleType("unreal_engine.structs")
structs.GameplayTag=object;structs.UIExtensionHandle=object
outputs=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");outputs.native_outputs=lambda *args:None
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location("uep_lyra_abilities._grenade_widget_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/grenade_widget_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.structs":structs,
    "uep_lyra_abilities.melee_trace_mixin":outputs,"uep_lyra_world.effect_pad_mixin":helpers}): spec.loader.exec_module(policy)


class Handle:
    def __init__(self,live=False): self.live=live;self.registered=live


class Ability:
    def __init__(self): self.handle=Handle();self.local=True;self.owner=object();self.calls=[];self.original=[]
    def get_property(self,name): return self.handle
    def set_property(self,name,value): self.calls.append(("set",name,value));self.handle=value
    def call_function(self,name):
        self.calls.append((name,))
        return self.local if name=="IsLocallyControlled" else self.owner
    def call_mixin_original(self,name): self.original.append(name)


class TestGrenadeWidgetMixin(unittest.TestCase):
    def setUp(self):
        self.ability=Ability();self.native=[];self.subsystem=types.SimpleNamespace(call_function=self.register)
        library=types.SimpleNamespace(call_function=self.handle_call)
        subsystems=types.SimpleNamespace(call_function=lambda name,*args:self.subsystem)
        native=types.SimpleNamespace(find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:library if name=="UIExtensionHandleFunctions" else subsystems),load_class=lambda name:name)
        for item in (patch.object(policy,"ue",native),patch.object(policy,"valid",lambda value:value is not None),
            patch.object(policy,"native_outputs",lambda cls,name,result:dict(ReturnValue=result[0],Handle=result[1])),
            patch.object(policy,"GameplayTag",lambda **values:types.SimpleNamespace(**values))):
            item.start();self.addCleanup(item.stop)
    def handle_call(self,name,handle):
        self.native.append((name,handle))
        if name=="IsValid": return handle.live,handle
        handle.registered=False;return (handle,)
    def register(self,name,*args): self.native.append((name,*args));return Handle(True)
    def avatar(self): policy.LyraGrenadeWidgetPythonProfile.K2_OnPawnAvatarSet(self.ability)
    def remove(self): policy.LyraGrenadeWidgetPythonProfile.K2_OnAbilityRemoved(self.ability)
    def test_actual_owner_context_tag_class_and_priority(self):
        self.avatar();call=self.native[-1]
        self.assertEqual(call[0],"K2_RegisterExtensionAsWidgetForContext");self.assertEqual(call[1].TagName,policy.TAG)
        self.assertEqual(call[2],policy.WIDGET);self.assertIs(call[3],self.ability.owner);self.assertEqual(call[4],-1)
        self.assertTrue(self.ability.handle.live);self.assertEqual(self.ability.original,[])
    def test_existing_handle_short_circuits_before_local_or_subsystem_reads(self):
        self.ability.handle.live=True;self.avatar()
        self.assertEqual(self.ability.calls,[]);self.assertEqual(len(self.native),1)
    def test_nonlocal_does_not_register_or_write_handle(self):
        before=self.ability.handle;self.ability.local=False;self.avatar()
        self.assertIs(self.ability.handle,before);self.assertEqual(len(self.native),1)
    def test_missing_subsystem_is_original_noop(self):
        self.subsystem=None;self.avatar();self.assertFalse(self.ability.handle.live)
        self.assertEqual(policy.evidence(self.ability)["missing_subsystem_noops"],1)
    def test_repeated_avatar_does_not_duplicate_registration(self):
        self.avatar();self.avatar()
        self.assertEqual(policy.evidence(self.ability)["registrations"],1)
    def test_removal_unregisters_even_invalid_handle_and_preserves_native_literal_semantics(self):
        before=self.ability.handle;self.remove()
        self.assertIs(self.native[0][1],before);self.assertEqual(self.native[0][0],"Unregister")
        self.assertIs(self.ability.handle,before);self.assertFalse(self.ability.handle.registered)
    def test_nonlocal_removal_not_guarded(self):
        self.ability.local=False;self.remove()
        self.assertEqual(self.native[0][0],"Unregister");self.assertFalse(any(call[0]=="IsLocallyControlled" for call in self.ability.calls))
    def test_register_remove_register_again(self):
        self.avatar();self.remove();self.avatar()
        # IsValid reports opaque pointer validity, not subsystem membership.
        # Original BP keeps its valid handle after Unregister as well.
        self.assertEqual(policy.evidence(self.ability)["registrations"],1)
        self.assertTrue(self.ability.handle.live);self.assertFalse(self.ability.handle.registered)
    def test_invalid_return_not_treated_as_truthy_tuple(self):
        with patch.object(policy,"native_outputs",lambda *args:dict(ReturnValue=(False,Handle()))):
            with self.assertRaisesRegex(RuntimeError,"bool"): self.avatar()
    def test_original_profile_forwards_exact_native_event_once(self):
        policy.LyraGrenadeWidgetBlueprintFallbackProfile.K2_OnPawnAvatarSet(self.ability)
        policy.LyraGrenadeWidgetBlueprintFallbackProfile.K2_OnAbilityRemoved(self.ability)
        self.assertEqual(self.ability.original,["K2_OnPawnAvatarSet","K2_OnAbilityRemoved"])
    def test_no_grenade_activation_damage_or_animation_in_this_slice(self):
        text=Path(policy.__file__).read_text(encoding="utf-8")
        for forbidden in ("ApplyGameplayEffect","TryActivateAbility","K2_ActivateAbility","PlayMontage","actor_spawn"):
            self.assertNotIn(forbidden,text)
