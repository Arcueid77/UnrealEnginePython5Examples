"""Original activation/options/press/rearm/end order and native fallback routing."""
import types,unittest
from uep_lyra_abilities import explorer_interact_mixin as policy
def ability():
    calls=[];obj=types.SimpleNamespace(call_function=lambda name,*args:calls.append((name,*args)),call_mixin_original=lambda name,*args:calls.append(('original',name,*args)));return obj,calls
class ExplorerInteractPolicyTests(unittest.TestCase):
    def test_activation_prints_then_scans_then_waits(self):
        a,calls=ability();policy.activate(a);self.assertEqual(calls,[(policy.AVAILABLE,),('LookForInteractables',),('InteractPressScan',)])
    def test_scan_and_wait_only_start_original_native_factories(self):
        a,calls=ability();policy.scan(a);policy.wait(a);self.assertEqual(calls,[(policy.SCAN,),(policy.WAIT,)])
    def test_options_array_is_forwarded_without_rebuilding_interface_structs(self):
        a,calls=ability();options=[object()];self.assertFalse(policy.options(a,options));self.assertIs(calls[0][1],options);self.assertEqual(calls[0][0],'UpdateInteractions')
    def test_empty_options_are_forwarded_to_native_clear(self):
        a,calls=ability();policy.options(a,[]);self.assertEqual(calls,[('UpdateInteractions',[])])
    def test_press_prints_triggers_then_rearms(self):
        a,calls=ability();self.assertFalse(policy.press(a));self.assertEqual(calls,[(policy.PRESSED,),('TriggerInteraction',),('InteractPressScan',)])
    def test_end_only_keeps_original_unavailable_print(self):
        for cancelled in (True,False):
            a,calls=ability();policy.end(a,cancelled);self.assertEqual(calls,[(policy.UNAVAILABLE,)]);self.assertIs(policy.evidence(a)['last_cancelled'],cancelled)
    def test_fallback_uses_original_functions_and_callback_branches(self):
        a,calls=ability();cls=policy.LyraExplorerInteractBlueprintFallbackProfile;cls.K2_ActivateAbility(a);cls.LookForInteractables(a);cls.InteractPressScan(a);cls.K2_OnEndAbility(a,True);self.assertTrue(cls.OptionsChanged(a,[]));self.assertTrue(cls.Pressed(a));self.assertEqual(calls,[('original','K2_ActivateAbility'),('original','LookForInteractables'),('original','InteractPressScan'),('original','K2_OnEndAbility',True)])
    def test_six_own_methods_in_both_profiles(self):
        for cls in (policy.LyraExplorerInteractPythonProfile,policy.LyraExplorerInteractBlueprintFallbackProfile):self.assertEqual(sum(callable(v) for v in vars(cls).values()),6)
