"""BP argument-expression ordering models plus guard on the C++ fix location."""
from pathlib import Path
import unittest


def decode(properties, expressions, skip_return_before_step=True):
    remaining, outputs = list(expressions), []
    for name, kind in properties:
        if not remaining: break
        if skip_return_before_step and kind == "return": continue
        expression = remaining.pop(0)
        if kind == "out": outputs.append((name, expression))
    return remaining, outputs


class ReturnBeforeOutFrame(unittest.TestCase):
    def test_return_before_out_does_not_consume_its_expression(self):
        properties = [("input", "in"), ("ReturnValue", "return"), ("CallParent", "out")]
        expressions = ["user-argument", "caller-bool-address"]
        self.assertEqual(decode(properties, expressions), ([], [("CallParent", "caller-bool-address")]))
        self.assertEqual(decode(properties, expressions, False), ([], []))

    def test_existing_native_return_last_and_scalar_only_call_unchanged(self):
        self.assertEqual(decode([("input", "in"), ("out", "out"), ("return", "return")], ["value", "address"]), ([], [("out", "address")]))
        self.assertEqual(decode([("input", "in"), ("return", "return")], ["value"]), ([], []))

    def test_multiple_outputs_after_return_keep_native_caller_addresses(self):
        self.assertEqual(decode([("return", "return"), ("a", "out"), ("b", "out")], ["first", "second"]),
            ([], [("a", "first"), ("b", "second")]))

    def test_cpp_return_slot_is_skipped_before_vm_step(self):
        source = Path(__file__).resolve().parents[3]/"Source/UnrealEnginePython/Private/PythonFunction.cpp"
        if not source.is_file(): self.skipTest("standalone Examples checkout has no UEP core source")
        text = source.read_text(encoding="utf-8")
        vm = text[text.index('//UE_LOG(LogPython, Warning, TEXT("BLUEPRINT CALL"));'):]
        self.assertLess(vm.index("if (prop->PropertyFlags & CPF_ReturnParm)"), vm.index("Stack.Step("))
