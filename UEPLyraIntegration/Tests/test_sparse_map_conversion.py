"""Source guard for the native sparse-map regression (not runtime proof)."""
from pathlib import Path
import re
import unittest


class SparseMapConversion(unittest.TestCase):
    def test_map_reader_traverses_sparse_slots_not_live_count(self):
        root = Path(__file__).resolve().parents[3]
        source = (root/"Source/UnrealEnginePython/Private/UEPyModule.cpp").read_text(encoding="utf-8-sig")
        reader = source.split("if (auto casted_prop = CastField<FMapProperty>(prop))", 1)[1].split("#endif", 1)[0]
        self.assertRegex(reader, r"i\s*<\s*map_helper\.GetMaxIndex\(\)")
        self.assertIn("map_helper.IsValidIndex(i)", reader)
        self.assertNotRegex(reader, r"i\s*<\s*map_helper\.Num\(\)")

    def test_native_fixture_uses_original_bp_and_independent_export(self):
        tool = Path(__file__).resolve().parents[1]/"Tools/validate_sparse_map_conversion.py"
        source = tool.read_text(encoding="utf-8")
        self.assertIn('call_mixin_original("UnregisterNameplateSource", pawns[index])', source)
        self.assertIn("native_present != set(expected)", source)
        self.assertNotIn("save_package", source)
        self.assertEqual(len(re.findall(r'\("(?:dense|remove-first|remove-middle|remove-last|multiple-holes|empty)"', source)), 6)
