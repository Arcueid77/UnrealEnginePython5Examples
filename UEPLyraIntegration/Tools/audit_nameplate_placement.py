"""Read-only marked-stage proof of original nameplate client/server settings."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_nameplate_placement.py")
sys.path.insert(0, str(Path(script).resolve().parent))
sys.path.insert(0, str(Path(script).resolve().parents[1]/"Overlay/Content/Scripts"))
from stage_safety import require_authoring_stage
from uep_lyra_nameplate_placement import read_placement

def argument(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))

stage = require_authoring_stage(argument("UEPPlacementStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
relative = Path("Plugins/GameFeatures/ShooterCore/Content/Experiences/LAS_ShooterGame_StandardComponents.uasset")
before = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (stage, reference)}
if len(set(before.values())) != 1:
    raise RuntimeError("native component placement differs from official Lyra")
report = {"status": "passed", "placement": read_placement(), "reference_hashes": before, "runtime_acceptance": False}
for path, digest in before.items():
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
        raise RuntimeError("component placement changed during read-only audit")
Path(argument("UEPPlacementResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_NAMEPLATE_PLACEMENT_AUDIT_PASSED")
