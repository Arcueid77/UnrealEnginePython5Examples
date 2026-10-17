"""Parse actual working-tree runtime/tools/tests before expensive native runs."""
from pathlib import Path
import unittest


class RuntimeSourceSyntaxModels(unittest.TestCase):
    def test_working_tree_python_syntax_without_importing_unreal(self):
        root = Path(__file__).resolve().parents[1]
        files = sorted(file for folder in ("Overlay/Content/Scripts", "Tools", "Tests") for file in (root/folder).rglob("*.py"))
        self.assertGreater(len(files), 100)
        for file in files:
            with self.subTest(path=str(file.relative_to(root))):
                compile(file.read_text(encoding="utf-8-sig"), str(file), "exec", dont_inherit=True)
