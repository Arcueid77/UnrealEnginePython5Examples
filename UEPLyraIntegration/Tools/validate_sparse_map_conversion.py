"""Transient native BP Map_Remove versus UEP reads; never save reference assets."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine import FVector

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "validate_sparse_map_conversion.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


result = Path(arg("UEPSparseMapResult"))
report = dict(schema_version=1, status="running", runtime_acceptance=False,
              assets_modified=False, cpp_compile_executed=False, cases=[], reference_hashes={})
manager, pawns = None, []
try:
    stage = require_authoring_stage(arg("UEPSparseMapStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    official = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    for root in (stage, official):
        file = root/"Content/UI/Indicators/NameplateManagerComponent.uasset"
        report["reference_hashes"][str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
    cls = ue.load_class("/Game/UI/Indicators/NameplateManagerComponent.NameplateManagerComponent_C")
    ue.register_declared_mixin(cls)
    manager = ue.new_object(cls)
    manager.add_to_root()
    ue.set_mixin_profile(manager, "BlueprintFallback")
    world = ue.get_editor_world()
    for index in range(6):
        pawns.append(world.actor_spawn(ue.find_class("Pawn"), FVector(index*1000.0, 0.0, 10000.0)))
    descriptors = [ue.new_object(ue.find_class("IndicatorDescriptor")) for _ in pawns]
    complete = dict(zip(pawns, descriptors))
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    for name, removed in (("dense", ()), ("remove-first", (0,)), ("remove-middle", (2,)),
                          ("remove-last", (5,)), ("multiple-holes", (0, 2, 4)), ("empty", tuple(range(6)))):
        manager.set_property("IndicatorMap", complete)
        expected = dict(complete)
        for index in removed:
            # Execute unchanged BP's real native Map_Remove. No Python dict
            # rewrite, wildcard ProcessEvent or synthetic sparse representation.
            manager.call_mixin_original("UnregisterNameplateSource", pawns[index])
            expected.pop(pawns[index])
        observed = dict(manager.get_property("IndicatorMap"))
        text_path = result.parent/(name+"-native.t3d")
        if not exporter.export_to_file(manager, str(text_path)):
            raise RuntimeError("native T3D export failed")
        raw = text_path.read_bytes()
        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
        map_lines = [line.strip() for line in text.splitlines() if "IndicatorMap=" in line]
        native_map = "\n".join(map_lines)
        native_present = {pawn for pawn in pawns if pawn.get_path_name() in native_map}
        if native_present != set(expected):
            raise AssertionError("unchanged BP native Map_Remove contents differ from expected")
        row = dict(name=name, passed=observed == expected,
            expected=sorted(key.get_path_name() for key in expected),
            observed=sorted(key.get_path_name() for key in observed),
            native_map_lines=map_lines, native_export=str(text_path), native_bp_remove=True,
            native_export_matches_expected=True)
        report["cases"].append(row)
    if not all(row["passed"] for row in report["cases"]):
        raise AssertionError("sparse native TMap entries were omitted by UEP conversion")
    report["status"] = "passed"
except Exception:
    report.update(status="failed", error=traceback.format_exc())
finally:
    if manager is not None:
        manager.set_property("IndicatorMap", {})
        manager.remove_from_root()
    for pawn in pawns:
        pawn.actor_destroy()
    for file, digest in report["reference_hashes"].items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            report.update(status="failed", error="reference asset changed")
    result.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ue.log("UEP_SPARSE_MAP_CONVERSION_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
