"""A disposable replicated native-collision floor, no gameplay logic or overlay."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_melee_network_fixture.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

PACKAGE = "/Game/UEPValidation/BP_MeleeNetworkFloor"
RELATIVE = "Content/UEPValidation/BP_MeleeNetworkFloor.uasset"


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    stage = require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    if (stage/RELATIVE).exists(): raise RuntimeError("fresh private floor asset required")
    bp = ue.create_blueprint(ue.find_class("Actor"), PACKAGE)
    component = ue.add_component_to_blueprint(bp, ue.find_class("BoxComponent"), "UEPReplicatedMeleeFloor")
    vector = ue.find_class("KismetMathLibrary").get_cdo().call_function("MakeVector", 5000., 5000., 20.)
    component.call_function("SetBoxExtent", vector, False)
    component.call_function("SetCollisionProfileName", "BlockAll", False)
    component.call_function("SetCollisionObjectType", 0); component.call_function("SetCollisionEnabled", 3)
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    for name in ("bReplicates", "bAlwaysRelevant", "bReplicateMovement"): cdo.set_property(name, True)
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("private replicated floor compile failed")
    cdo = bp.GeneratedClass.get_cdo()
    if not all(cdo.get_property(name) for name in ("bReplicates", "bAlwaysRelevant", "bReplicateMovement")): raise RuntimeError("private floor replication defaults lost")
    if any(node.get_class().get_name() == "K2Node_CallFunction" for graph in ue.blueprint_get_all_graphs(bp) for node in graph.Nodes):
        raise RuntimeError("private collision floor must have no gameplay calls")
    extent = component.call_function("GetUnscaledBoxExtent")
    if [extent.x, extent.y, extent.z] != [5000., 5000., 20.] or int(component.call_function("GetCollisionObjectType")) != 0:
        raise RuntimeError("private floor native collision defaults differ")
    bp.save_package()
    return dict(status="passed", kind="meleetracenetworkfixture", runtime_acceptance=False, gameplay_business=False, stage_only=True,
        original_lyra_modified=False, asset=str(stage/RELATIVE), sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest(),
        class_path=bp.GeneratedClass.get_path_name(), extent=[5000., 5000., 20.], native_object_type=0,
        native_replication_defaults=True, native_component_archetype_preserved_for_clients=True)


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc(), runtime_acceptance=False)
Path(arg("UEPMeleeNetworkFixtureResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
(ue.log if report["status"] == "passed" else ue.log_error)("UEP_MELEE_NETWORK_FIXTURE_"+report["status"].upper())
