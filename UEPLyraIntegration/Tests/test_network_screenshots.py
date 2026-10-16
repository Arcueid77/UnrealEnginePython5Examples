import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_network_screenshots import FrameScreenshotQueue, validate_queue


class NativeScreenshotQueueTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.queue = FrameScreenshotQueue(lambda *args: self.calls.append(args))

    def test_simultaneous_dash_respawn_requests_are_serialized(self):
        self.queue.request("dash.png", "world", "controller")
        self.queue.request("respawn.png", "world", "controller")
        self.assertEqual(self.calls, [])
        self.queue.drain_one()
        self.assertEqual(self.calls, [("dash.png", "world", "controller")])
        self.assertEqual(self.queue.snapshot()["pending_count"], 1)
        self.queue.drain_one()
        self.assertEqual(len(self.calls), 2)
        validate_queue(self.queue.snapshot(), ["dash.png", "respawn.png"], "A")

    def test_duplicate_path_rejected_not_double_reported(self):
        self.queue.request("same.png")
        with self.assertRaises(RuntimeError):
            self.queue.request("same.png")
        self.assertEqual(self.queue.snapshot()["pending_count"], 1)

    def test_emit_failure_retains_pending_evidence(self):
        self.queue.request("failed.png")
        self.queue.emit = lambda *args: (_ for _ in ()).throw(RuntimeError("native screenshot error"))
        with self.assertRaisesRegex(RuntimeError, "native screenshot error"):
            self.queue.drain_one()
        self.assertEqual(self.queue.snapshot()["pending_count"], 1)
        self.assertEqual(self.queue.snapshot()["issued"], [])

    def test_missing_pending_or_false_rendering_claim_rejected(self):
        self.queue.request("one.png")
        with self.assertRaises(RuntimeError):
            validate_queue(self.queue.snapshot(), ["one.png"], "A")
        self.queue.drain_one()
        for key, value in (("rendered_files_verified", True), ("issued", []), ("pending_count", 1)):
            report = copy.deepcopy(self.queue.snapshot())
            report[key] = value
            with self.assertRaises(RuntimeError):
                validate_queue(report, ["one.png"], "A")

    def test_no_client_images_or_server_ui_rejected(self):
        validate_queue(self.queue.snapshot(), [], "server")
        with self.assertRaises(RuntimeError):
            validate_queue(self.queue.snapshot(), [], "B1")
        self.queue.request("one.png")
        self.queue.drain_one()
        with self.assertRaises(RuntimeError):
            validate_queue(self.queue.snapshot(), ["one.png"], "server")


if __name__ == "__main__":
    unittest.main()
