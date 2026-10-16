"""Asset authoring must not be redirected into the official project."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
from stage_safety import require_authoring_stage


class StageSafetyTests(unittest.TestCase):
    def test_missing_root_fails(self):
        with self.assertRaisesRegex(RuntimeError, "explicit"):
            require_authoring_stage(None, "Content")

    def test_unmarked_project_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "marked"):
                require_authoring_stage(directory, Path(directory) / "Content")

    def test_marker_for_another_project_is_not_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "Stage"
            stage.mkdir()
            (stage / ".uep-lyra-full-stage.json").touch()
            with self.assertRaisesRegex(RuntimeError, "differs"):
                require_authoring_stage(stage, Path(directory) / "Official" / "Content")

    def test_current_marked_project_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".uep-lyra-full-stage.json").touch()
            self.assertEqual(require_authoring_stage(directory, Path(directory) / "Content"),
                             Path(directory).resolve())
