"""Prime the staged Lyra asset registry before multi-process runtime tests."""

import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue


RESULT_PREFIX = "-UEPLyraAssetRegistryPrimeResult="


def command_line_value(prefix):
    for argument in sys.argv:
        if argument.startswith(prefix):
            return argument[len(prefix) :].strip('"')
    return None


result_value = command_line_value(RESULT_PREFIX)
if not result_value:
    raise RuntimeError(RESULT_PREFIX + "<path> is required")

result_path = Path(result_value)
started_at = time.monotonic()
try:
    ue.wait_for_assets()
    if ue.is_loading_assets():
        raise RuntimeError("asset registry still reports an active initial scan")
    report = {
        "schema_version": 1,
        "status": "passed",
        "engine_version": [ue.ENGINE_MAJOR_VERSION, ue.ENGINE_MINOR_VERSION],
        "loading_after_wait": False,
        "duration_seconds": round(time.monotonic() - started_at, 3),
    }
    ue.log("UEP_LYRA_ASSET_REGISTRY_PRIME_PASSED")
except Exception:
    report = {
        "schema_version": 1,
        "status": "failed",
        "error": traceback.format_exc(),
    }
    ue.log_error("UEP_LYRA_ASSET_REGISTRY_PRIME_FAILED")

result_path.parent.mkdir(parents=True, exist_ok=True)
result_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["status"] != "passed":
    raise RuntimeError(report["error"])
