"""Read original SpawnEffect/SpawnIn defaults and current native signatures."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_spawn_effect.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)): return value
    if hasattr(value, "get_path_name"): return value.get_path_name()
    raise RuntimeError("unexpected SpawnEffect default type: "+type(value).__name__)


def audit():
    stage = require_authoring_stage(arg("UEPSpawnEffectStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    rows, hashes = [], {}
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    for name in ("GA_SpawnEffect", "GE_SpawnIn"):
        relative = "Plugins/GameFeatures/ShooterCore/Content/Game/Respawn/"+name+".uasset"
        pair = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (source, stage)}
        if len(set(pair.values())) != 1: raise RuntimeError("read-only spawn audit requires original asset: "+name)
        hashes.update(pair)
        cls = ue.load_class("/ShooterCore/Game/Respawn/"+name+"."+name+"_C"); cdo = cls.get_cdo()
        path = Path(arg("UEPSpawnEffectAuditResult")).parent/(name+"-cdo.t3d")
        if not exporter.export_to_file(cdo, str(path)): raise RuntimeError("native SpawnEffect CDO export failed")
        fields = ("InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationPolicy", "SpawnMontage", "EnableInputAfterTimeFraction", "DurationPolicy")
        row = dict(native_class=cls.get_path_name(), defaults={field: serial(cdo.get_property(field)) for field in fields if field in cdo.properties()},
            native_cdo_text=str(path), signatures={})
        if name == "GA_SpawnEffect":
            row["signatures"] = {method: ue.describe_function(cls, method) for method in ("K2_ActivateAbility", "K2_OnEndAbility", "DisableInput", "EnableInputAgain")}
            row["native_montage_length"] = float(cdo.SpawnMontage.call_function("GetPlayLength"))
        rows.append(row)
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest: raise RuntimeError("read-only spawn audit changed an asset")
    return dict(status="passed", runtime_acceptance=False, assets_modified=False, assets=rows, reference_hashes=hashes)


report = audit()
Path(arg("UEPSpawnEffectAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_SPAWN_EFFECT_AUDIT_PASSED")
