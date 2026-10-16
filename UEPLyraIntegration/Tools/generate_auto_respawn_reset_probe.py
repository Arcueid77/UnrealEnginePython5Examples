"""Stage-only typed Reset observer transport; no broadcast or gameplay logic."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_auto_respawn_reset_probe.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import read_graph

PACKAGE = "/Game/UEPValidation/BP_AutoRespawnResetProbe"
RELATIVE = "Content/UEPValidation/BP_AutoRespawnResetProbe.uasset"


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    stage = require_authoring_stage(arg("UEPResetProbeStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    if (stage/RELATIVE).exists() or ue.find_asset(PACKAGE+".BP_AutoRespawnResetProbe") is not None:
        raise RuntimeError("fresh stage-only Reset probe required")
    ue.unregister_all_mixins()
    bp = ue.create_blueprint(ue.find_class("Object"), PACKAGE)
    graph = read_graph(bp, "Reset", ue.find_struct("LyraPlayerResetMessage"), ue.find_class("AsyncAction_ListenForGameplayMessage"))
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2 or [item.get_name() for item in bp.FunctionGraphs] != ["ReadReset"] or len(graph.Nodes) != 4:
        raise RuntimeError("typed Reset observer graph footprint differs")
    bp.save_package()
    return dict(status="passed", stage_only=True, runtime_acceptance=False, gameplay_logic=False, broadcast_graphs=0,
        typed_vm_reader=True, payload_type="LyraPlayerResetMessage", function="ReadReset", nodes=4,
        asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPResetProbeResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_RESET_PROBE_ASSETS_"+report["status"].upper())
if report["status"] != "passed": raise RuntimeError(report["error"])
