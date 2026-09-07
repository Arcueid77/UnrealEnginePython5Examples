"""Final shutdown evidence, including real CPython exit without Unreal."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_hud_presenter import SCRIPTS_ROOT  # installs the shared fake UE module
from uep_lyra_hud import shutdown_validation as shutdown


def pending_report():
    return {
        "schema_version": 5,
        "status": "awaiting_shutdown",
        "gameplay_slice": {"enabled": True},
        "error": None,
        "hud": {
            "active_widget_count": 1,
            "active_widgets": ["fixture"],
            "live_widget_reference_count": 1,
            "construct_count": 3,
            "destruct_count": 2,
            "teardown_count": 2,
            "controller_bind_count": 3,
            "controller_unbind_count": 2,
            "health_bind_count": 4,
            "health_unbind_count": 3,
            "errors": [],
        },
    }


def clean_final_hud():
    result = pending_report()["hud"]
    result.update(
        active_widget_count=0,
        active_widgets=[],
        live_widget_reference_count=0,
        controller_unbind_count=3,
        health_unbind_count=4,
        destruct_count=3,
        teardown_count=3,
    )
    return result


class HUDShutdownTests(unittest.TestCase):
    def assert_failed(self, final, fragment):
        result = shutdown.finalized_report(pending_report(), final)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["shutdown"]["status"], "failed")
        self.assertIn(fragment, result["error"])

    def test_clean_shutdown_preserves_pre_quit_evidence(self):
        pending = pending_report()
        before = copy.deepcopy(pending)
        result = shutdown.finalized_report(pending, clean_final_hud())
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["shutdown"]["phase"], "python_atexit")
        self.assertEqual(result["hud"]["active_widget_count"], 1)
        self.assertEqual(result["shutdown"]["hud"]["active_widget_count"], 0)
        self.assertEqual(pending, before)

    def test_outstanding_presenter_is_rejected(self):
        self.assert_failed(pending_report()["hud"], "retained a presenter")

    def test_live_python_widget_reference_is_rejected(self):
        final = clean_final_hud()
        final["live_widget_reference_count"] = 1
        self.assert_failed(final, "widget reference")

    def test_controller_and_health_leaks_are_rejected(self):
        for prefix in ("controller", "health"):
            with self.subTest(prefix=prefix):
                final = clean_final_hud()
                final[prefix + "_unbind_count"] -= 1
                self.assert_failed(final, "retained " + prefix + " callbacks")

    def test_resetting_counters_does_not_hide_leaks(self):
        final = clean_final_hud()
        final["health_bind_count"] = final["health_unbind_count"] = 0
        self.assert_failed(final, "lost prior evidence")

    def test_presenter_error_blocks_final_success(self):
        final = clean_final_hud()
        final["errors"] = [{"operation": "unbind_health"}]
        self.assert_failed(final, "presenter errors")

    def test_missing_or_invalid_counters_fail_closed(self):
        for value in (None, -1, "0", False):
            with self.subTest(value=value):
                final = clean_final_hud()
                final["active_widget_count"] = value
                self.assert_failed(final, "invalid final HUD counter")
        final = clean_final_hud()
        del final["health_bind_count"]
        self.assert_failed(final, "invalid final HUD counter")

    def test_failed_gameplay_report_cannot_be_promoted(self):
        pending = pending_report()
        pending["status"] = "failed"
        result = shutdown.finalized_report(pending, clean_final_hud())
        self.assertEqual(result["status"], "failed")
        self.assertIn("not awaiting shutdown", result["error"])

    def test_arming_defers_pass_and_freezes_snapshot(self):
        report = pending_report()
        report["status"] = "passed"
        with patch.object(shutdown.atexit, "register") as register:
            shutdown.defer_until_shutdown(report, "fixture.json")
        self.assertEqual(report["status"], "awaiting_shutdown")
        self.assertEqual(report["shutdown"]["status"], "pending")
        captured = register.call_args.args[2]
        report["hud"]["controller_bind_count"] += 1
        self.assertEqual(captured["hud"]["controller_bind_count"], 3)

    def test_real_python_exit_requires_finalizer_and_cleanup(self):
        # Exercise actual atexit ordering. This child never imports the engine.
        code = r'''
import atexit, json, os, sys, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
ue = types.ModuleType("unreal_engine")
ue.log = print
ue.log_error = print
sys.modules["unreal_engine"] = ue
from uep_lyra_hud import state, shutdown_validation
path, exit_mode = Path(sys.argv[2]), sys.argv[3]
report = json.loads(sys.argv[4])
state._state.update(report["hud"])
state._live_widgets["fixture"] = object()
shutdown_validation.defer_until_shutdown(report, path)
path.write_text(json.dumps(report), encoding="utf-8")
def cleanup():
    state._live_widgets.clear()
    state._state["active_widgets"] = []
    state._state["controller_unbind_count"] = 3
    state._state["health_unbind_count"] = 4 if exit_mode == "clean" else 3
    state._state["destruct_count"] = 3
    state._state["teardown_count"] = 3
atexit.register(cleanup)
if exit_mode == "skip_finalizer":
    os._exit(0)
'''
        with tempfile.TemporaryDirectory(prefix="uep-hud-shutdown-") as temporary:
            for mode, expected in (
                ("clean", "passed"),
                ("leak", "failed"),
                ("skip_finalizer", "awaiting_shutdown"),
            ):
                with self.subTest(mode=mode):
                    path = Path(temporary) / (mode + ".json")
                    completed = subprocess.run(
                        [sys.executable, "-B", "-c", code, str(SCRIPTS_ROOT),
                         str(path), mode, json.dumps(pending_report())],
                        capture_output=True, text=True, timeout=15, check=True,
                    )
                    self.assertEqual(json.loads(path.read_text())["status"], expected)
                    self.assertEqual(
                        "UEP_LYRA_HUD_SHUTDOWN_PASSED" in completed.stdout,
                        mode == "clean",
                    )


if __name__ == "__main__":
    unittest.main()
