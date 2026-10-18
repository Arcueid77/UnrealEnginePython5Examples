"""Native invalid/non-world lookup only; no replication or gameplay acceptance."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities.network_identity import read,key

result=Path(next(value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPNetworkIdentityProbeResult=")))
stage=Path(next(value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPNetworkIdentityStage=")))
report=dict(status="failed",error=None,network_acceptance=False,full_acceptance=False,assets_saved=False,ids_created=False,gameplay_state_written=False)
try:
    if not (stage/".uep-lyra-full-stage.json").is_file(): raise RuntimeError("marked disposable stage required")
    invalid=read(None);report["native_null"]=invalid
    obj=ue.find_class("Object").get_cdo();worldless=read(obj)
    if key(invalid) is not None or invalid["transport"]!="InvalidObject" or invalid["wire_id"]: raise RuntimeError("native null identity was fabricated")
    if key(worldless) is not None or worldless["transport"]!="NoWorld" or worldless["wire_id"]: raise RuntimeError("native non-world identity was fabricated")
    report.update(status="passed",native_null=invalid,native_worldless=worldless,actual_native_calls=2)
except Exception: report["error"]=traceback.format_exc();ue.log_error(report["error"])
result.write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed": raise RuntimeError(report["error"])
ue.log("UEP_NETWORK_IDENTITY_INVALID_PROBE_PASSED")
