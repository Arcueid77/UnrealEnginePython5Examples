"""Typed VM transport only: never call a wildcard CustomThunk via ProcessEvent.

New example-owned UObject BP has typed ReadUI/ReadVerb and BroadcastUI/Verb
functions. Native VM supplies FStructProperty for each wildcard. No gameplay
decision, subscription or animation business lives in this glue asset.
"""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_message_payload_adapter.py"), None)
if script is None:
    raise RuntimeError("pass the generator to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import read_graph, broadcast_graph


PATH = "/Game/UEPInterop/BP_UEPGameplayMessages"


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


def generate():
    require_authoring_stage(argument("UEPMessageAdapterStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    if ue.find_asset(PATH + ".BP_UEPGameplayMessages") is not None:
        raise RuntimeError("adapter exists; use a fresh marked stage or retain its verified asset")
    ue.unregister_all_mixins()
    bp = ue.create_blueprint(ue.find_class("Object"), PATH)
    ue.compile_blueprint(bp)
    proxy, router = ue.find_class("AsyncAction_ListenForGameplayMessage"), ue.find_class("GameplayMessageSubsystem")
    ui = ue.load_object(ue.find_class("UserDefinedStruct"), "/ShooterCore/Input/Abilities/Struct_UIMessaging.Struct_UIMessaging")
    rows = []
    for suffix, payload_type in (("UI", ui), ("Verb", ue.find_struct("LyraVerbMessage"))):
        for graph in (read_graph(bp, suffix, payload_type, proxy), broadcast_graph(bp, suffix, payload_type, router)):
            rows.append({"function": graph.get_name(), "nodes": len(graph.Nodes), "payload_type": payload_type.get_path_name()})
    ue.compile_blueprint(bp)
    if int(bp.Status) == 2:
        raise RuntimeError("typed message adapter did not compile")
    bp.save_package()
    return {"status": "passed", "asset": PATH, "functions": rows, "business_logic": False,
            "wildcard_calls_use_compiled_vm": True, "runtime_acceptance": False}


result = argument("UEPGenerateMessageAdapterResult")
if result is None:
    raise RuntimeError("UEPGenerateMessageAdapterResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_MESSAGE_ADAPTER_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
