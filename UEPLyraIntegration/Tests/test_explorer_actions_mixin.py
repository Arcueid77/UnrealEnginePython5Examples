"""Authority/cast/pickup/client-message ordering after the original native prep."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('_explorer_actions_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_abilities/explorer_actions_mixin.py');policy=importlib.util.module_from_spec(spec);world=types.ModuleType('uep_lyra_world.effect_pad_mixin');world.valid=lambda v:v is not None
with patch.dict(sys.modules,{'unreal_engine':types.SimpleNamespace(find_class=lambda n:n),'uep_lyra_world.effect_pad_mixin':world}):spec.loader.exec_module(policy)
def ability(authority=True,pawn=True):
    calls=[];instigator=types.SimpleNamespace(is_a=lambda cls:pawn and cls=='Pawn');data=types.SimpleNamespace(Instigator=instigator,Target='target');a=types.SimpleNamespace(call_function=lambda name,*args:calls.append((name,*args)) or (authority if name=='K2_HasAuthority' else None),call_mixin_original=lambda name,*args:calls.append(('original',name,*args)));return a,data,calls
class ExplorerActionsPolicyTests(unittest.TestCase):
    def test_authority_collect_prep_pickup_then_montage(self):
        a,data,calls=ability();policy.activate(a,'collect',data);self.assertEqual(calls,[(policy.PREP,data),('K2_HasAuthority',),(policy.PICKUP,data.Instigator,'target'),(policy.MONTAGE,)])
    def test_authority_sit_has_no_inventory_lookup_or_pickup(self):
        a,data,calls=ability();policy.activate(a,'sit',data);self.assertEqual(calls,[(policy.PREP,data),('K2_HasAuthority',),(policy.MONTAGE,)])
    def test_client_branch_does_not_cast_and_messages_before_montage(self):
        for kind in ('collect','sit'):
            a,data,calls=ability(False,False);policy.activate(a,kind,data);self.assertEqual(calls,[(policy.PREP,data),('K2_HasAuthority',),(policy.DURATION,data.Instigator),(policy.MONTAGE,)])
    def test_authority_failed_cast_ends_after_prep_without_montage(self):
        a,data,calls=ability(True,False);policy.activate(a,'collect',data);self.assertEqual(calls,[(policy.PREP,data),('K2_HasAuthority',),('K2_EndAbility',)])
    def test_null_instigator_keeps_prep_before_end(self):
        a,data,calls=ability();data.Instigator=None;policy.activate(a,'sit',data);self.assertEqual(calls[-1],('K2_EndAbility',));self.assertEqual(calls[0],(policy.PREP,data))
    def test_native_montage_callback_ends_once_and_stops_bp_fallthrough(self):
        a,_,calls=ability();self.assertFalse(policy.ended(a));self.assertEqual(calls,[('K2_EndAbility',)])
    def test_fallback_profiles_use_original_event_and_end_gate(self):
        for kind in ('Collect','Sit'):
            a,data,calls=ability();cls=getattr(policy,'LyraExplorer'+kind+'BlueprintFallbackProfile');cls.K2_ActivateAbilityFromEvent(a,data);self.assertTrue(cls.MontageEnded(a));self.assertEqual(calls,[('original','K2_ActivateAbilityFromEvent',data)])
    def test_two_methods_per_action_profile(self):
        for kind in ('Collect','Sit'):
            for profile in ('Python','BlueprintFallback'):self.assertEqual(sum(callable(v) for v in vars(getattr(policy,'LyraExplorer'+kind+profile+'Profile')).values()),2)
