"""Finalize probe evidence at Python exit, after UEP's Mixin teardown.

No UObject calls are allowed here. The external driver must still wait for a
clean process exit and closed log before accepting this final report.
"""

import atexit
import copy
import json
from pathlib import Path

import unreal_engine as ue

from . import state


COUNTERS = (
    "construct_count",
    "destruct_count",
    "teardown_count",
    "controller_bind_count",
    "controller_unbind_count",
    "health_bind_count",
    "health_unbind_count",
)


def checked_counter(hud, name):
    value = hud.get(name)
    if type(value) is not int or value < 0:
        raise RuntimeError("invalid final HUD counter: " + name)
    return value


def validate_shutdown_snapshot(before, final):
    if final.get("errors") != []:
        raise RuntimeError("HUD shutdown contains presenter errors")
    if (
        checked_counter(final, "active_widget_count") != 0
        or final.get("active_widgets") != []
        or checked_counter(final, "live_widget_reference_count") != 0
    ):
        raise RuntimeError("HUD shutdown retained a presenter or widget reference")
    for name in COUNTERS:
        if checked_counter(final, name) < checked_counter(before, name):
            raise RuntimeError("HUD shutdown lost prior evidence: " + name)
    for prefix in ("controller", "health"):
        if final[prefix + "_bind_count"] != final[prefix + "_unbind_count"]:
            raise RuntimeError("HUD shutdown retained " + prefix + " callbacks")


def finalized_report(pending_report, final_hud):
    """Pure transformation so negative cases need neither Unreal nor a file."""
    result = copy.deepcopy(pending_report)
    result["shutdown"] = {
        "phase": "python_atexit",
        "status": "failed",
        "hud": copy.deepcopy(final_hud),
    }
    try:
        if pending_report.get("status") != "awaiting_shutdown":
            raise RuntimeError("HUD report was not awaiting shutdown")
        validate_shutdown_snapshot(result["hud"], final_hud)
    except Exception as error:
        result["status"] = "failed"
        result["error"] = str(error)
    else:
        result["status"] = "passed"
        result["shutdown"]["status"] = "passed"
    return result


def _finalize(result_path, pending_report):
    # UEP unregisters routers in OnEnginePreExit before Py_Finalize calls atexit.
    # Captured state contains only metadata; this path never queries dead UObjects.
    report = finalized_report(pending_report, state.snapshot())
    Path(result_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] == "passed":
        if report["gameplay_slice"]["enabled"]:
            ue.log("UEP_LYRA_GAMEPLAY_SLICE_PASSED")
        ue.log("UEP_LYRA_PYTHON_HUD_PASSED")
        ue.log("UEP_LYRA_HUD_SHUTDOWN_PASSED")
        ue.log("UEP_LYRA_SMOKE_PASSED")
    else:
        ue.log_error("UEP_LYRA_HUD_SHUTDOWN_FAILED " + report["error"])


def defer_until_shutdown(report, result_path):
    """Arm only the automation probe, not ordinary interactive play."""
    report["status"] = "awaiting_shutdown"
    report["shutdown"] = {"status": "pending", "phase": "python_atexit"}
    # Freeze the pre-quit proof: later callbacks must not rewrite its counters.
    atexit.register(_finalize, str(result_path), copy.deepcopy(report))
