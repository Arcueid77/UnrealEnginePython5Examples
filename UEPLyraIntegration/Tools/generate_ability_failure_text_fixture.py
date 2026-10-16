"""Test-only native live-text seed; do not ship it as presentation business."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, K2Node_FunctionResult, K2Node_MakeStruct
from unreal_engine.structs import EdGraphPinType

script = globals().get("__file__") or next(arg for arg in sys.argv if Path(arg).name == "generate_ability_failure_text_fixture.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import connect

PATH = "/Game/UEPValidation/BP_UEPFailureTextFixture"


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


def generate():
    require_authoring_stage(argument("UEPFailureTextStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    bp = ue.find_asset(PATH + ".BP_UEPFailureTextFixture")
    if bp is None:
        bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    if "MakeLiveTextFailure" not in {graph.get_name() for graph in bp.FunctionGraphs}:
        graph = ue.blueprint_add_function(bp, "MakeLiveTextFailure")
        entry = graph.Nodes[0]
        entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("PlayerController")), "Controller")
        for name in ("Namespace", "Key"):
            entry.node_create_pin(1, EdGraphPinType(PinCategory="string"), name)
        lookup = graph.graph_add_node_call_function(ue.find_class("KismetTextLibrary").FindTextInLocalizationTable)
        payload = ue.find_struct("LyraAbilitySimpleFailureMessage")
        make = graph.graph_add_node(K2Node_MakeStruct)
        make.StructType = payload
        graph.graph_reconstruct_node(make)
        outputs = [pin for pin in make.node_pins() if pin.direction == 1 and pin.category == "struct"]
        if len(outputs) != 1:
            raise RuntimeError("native failure make-struct output differs")
        result = graph.graph_add_node(K2Node_FunctionResult)
        result.node_create_pin(0, EdGraphPinType(PinCategory="struct", PinSubCategoryObject=payload), "Payload")
        result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "Found")
        connect(entry, "then", result, "execute")
        connect(entry, "Controller", make, "PlayerController")
        connect(entry, "Namespace", lookup, "Namespace")
        connect(entry, "Key", lookup, "Key")
        connect(lookup, "OutText", make, "UserFacingReason")
        connect(lookup, "ReturnValue", result, "Found")
        outputs[0].connect(result.node_find_pin("Payload"))
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2:
        raise RuntimeError("native text fixture did not compile")
    bp.save_package()
    return {"status": "passed", "fixture_only": True, "runtime_acceptance": False,
            "asset": PATH, "namespace": "InputKeys", "key": "LeftMouseButton",
            "graphs": [{"name": graph.get_name(), "nodes": len(graph.Nodes)} for graph in bp.FunctionGraphs],
            "signature": ue.describe_function(bp.GeneratedClass, "MakeLiveTextFailure")}


output = argument("UEPFailureTextAssetResult")
if output is None:
    raise RuntimeError("UEPFailureTextAssetResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_FAILURE_TEXT_FIXTURE_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
