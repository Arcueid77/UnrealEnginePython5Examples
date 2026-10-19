"""Only one exact original Blueprint component-template ensure is admissible."""
import unittest
from uep_lyra_weapons.netshooter_actor_log_contract import validate_log


def raw():
    return "\n".join(("LogPython: UEP_NETSHOOTER_BASELINE_TEMPLATE_BEGIN actor","LogOutputDevice: Error: === Handled ensure: ===",
        "LogOutputDevice: Error: Ensure condition failed: Component->GetArchetype() == Component->GetClass()->GetDefaultObject() [File:F:/Engine/ActorReplication.cpp] [Line:676]",
        "LogOutputDevice: Error: Replicated component actor::NODE_AddStaticMeshComponent-0 was added dynamically outside the construction script. This is not well supported",
        "LogOutputDevice: Error: Stack:","LogOutputDevice: Error: [Callstack] AActor::AddComponentForReplication() py_ue_call_mixin_original()",
        "LogPython: UEP_NETSHOOTER_BASELINE_TEMPLATE_END actor","LogPython: SHUTDOWN_PASSED","Log file closed"))


class TestNetShooterActorLogContract(unittest.TestCase):
    def test_only_original_native_template_baseline(self):
        result,clean=validate_log(raw());self.assertEqual(result["original_blueprint_dynamic_replication_template_ensure"],1);self.assertNotIn("Error:",clean)
    def test_unrelated_error_outside_window_rejected(self):
        with self.assertRaises(RuntimeError):validate_log(raw()+"\nLogPython: Error: other")
    def test_unrelated_error_inside_window_rejected(self):
        with self.assertRaises(RuntimeError):validate_log(raw().replace("LogOutputDevice: Error: Stack:","LogOutputDevice: Error: another error"))
    def test_different_ensure_cannot_be_ignored(self):
        with self.assertRaises(RuntimeError):validate_log(raw().replace("Component->GetArchetype() == Component->GetClass()->GetDefaultObject()","OtherFailure"))
    def test_missing_original_blueprint_path_rejected(self):
        with self.assertRaises(RuntimeError):validate_log(raw().replace("py_ue_call_mixin_original()","PythonNativeHandler()"))
    def test_no_baseline_window_rejected(self):
        with self.assertRaises(RuntimeError):validate_log("Log file closed")
