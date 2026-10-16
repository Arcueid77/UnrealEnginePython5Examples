"""Check the actual peer-reader method without bootstrapping an Unreal probe."""
import ast
from pathlib import Path
import types
import unittest
from unittest.mock import Mock


class FrameSnapshotTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_network.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "NetworkProbe")
        reader = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "_peer_status")
        self.read = Mock()
        def require(value, message):
            if not value:
                raise RuntimeError(message)
        scope = {"read_json": self.read, "require": require}
        exec(compile(ast.Module(body=[reader], type_ignores=[]), str(source), "exec"), scope)
        self.reader = scope["_peer_status"]
        self.probe = types.SimpleNamespace(root=Path("evidence"), run_id="run", peer_frame_snapshots={})

    def test_multiple_decisions_get_same_current_frame_object(self):
        before = {"run_id": "run", "peer": "A", "player": "old"}
        after = {"run_id": "run", "peer": "A", "player": "new"}
        self.read.side_effect = [before, after]
        self.assertIs(self.reader(self.probe, "A"), before)
        self.assertIs(self.reader(self.probe, "A"), before)
        self.assertEqual(self.read.call_count, 1)
        self.probe.peer_frame_snapshots = {}
        self.assertIs(self.reader(self.probe, "A"), after)

    def test_missing_snapshot_never_uses_previous_frame(self):
        self.read.side_effect = [{"run_id": "run", "peer": "A"}, None]
        self.reader(self.probe, "A")
        self.probe.peer_frame_snapshots = {}
        self.assertIsNone(self.reader(self.probe, "A"))
        self.assertIsNone(self.reader(self.probe, "A"))
        self.assertEqual(self.read.call_count, 2)

    def test_foreign_snapshot_rejected_before_caching(self):
        self.read.return_value = {"run_id": "foreign", "peer": "A"}
        with self.assertRaises(RuntimeError):
            self.reader(self.probe, "A")
        self.assertEqual(self.probe.peer_frame_snapshots, {})

    def test_each_peer_has_separate_current_frame_snapshot(self):
        self.read.side_effect = [{"run_id": "run", "peer": "A"}, {"run_id": "run", "peer": "B0"}]
        self.assertEqual(self.reader(self.probe, "A")["peer"], "A")
        self.assertEqual(self.reader(self.probe, "B0")["peer"], "B0")
        self.assertEqual(self.read.call_count, 2)


if __name__ == "__main__":
    unittest.main()
