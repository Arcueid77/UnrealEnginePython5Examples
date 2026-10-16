"""Read original weapon/ability spawner defaults, signatures and pickup data."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "audit_spawners.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))

def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "get_path_name"):
        return value.get_path_name()
    if all(hasattr(value, k) for k in ("x", "y", "z")):
        return [float(getattr(value, k)) for k in ("x", "y", "z")]
    if all(hasattr(value, k) for k in ("r", "g", "b", "a")):
        return [float(getattr(value, k)) for k in ("r", "g", "b", "a")]
    return str(value)

def audit():
    stage = require_authoring_stage(arg("UEPSpawnerStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes, rows, pickups = {}, [], []
    assets = ["Blueprint/B_WeaponSpawner", "Blueprint/B_AbilitySpawner"]
    assets += ["Weapons/"+kind+"/WeaponPickupData_"+kind for kind in ("Pistol", "Rifle", "Shotgun")]
    assets += ["Items/HealthPickup/WeaponPickupData_Heal_"+size for size in ("Small", "Big")]
    for asset in assets:
        relative = Path("Plugins/GameFeatures/ShooterCore/Content")/(asset+".uasset")
        for root in (stage, reference):
            file = root/relative;hashes[str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
        if hashes[str(stage/relative)] != hashes[str(reference/relative)]:
            raise RuntimeError("spawner audit requires original inputs: "+asset)
        path = "/ShooterCore/"+asset+"."+asset.split("/")[-1]
        if asset.startswith("Blueprint"):
            bp = ue.load_object(ue.find_class("Blueprint"), path);cdo = bp.GeneratedClass.get_cdo()
            defaults = {}
            for field in ("WeaponDefinition", "CoolDownTime", "CheckExistingOverlapDelay", "CoolDownPercentage", "bIsWeaponAvailable",
                          "GiveAmmoForDuplicatedWeapons", "IgnorePickUpWhenReload", "LightColor", "LightIntensity", "LightRadius",
                          "LifeTimeReload", "Glow Intensity", "Weapon Mesh Offset", "GameplayEffectToApply", "bReplicates"):
                if field in cdo.properties():
                    defaults[field] = serial(cdo.get_property(field))
            signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in
                ("GiveWeapon", "PlayPickupEffects", "PlayRespawnEffects", "Broadcast Failure Message", "ReceiveTick", "ReceiveBeginPlay")}
            timelines = [{"name": timeline.get_name(), "length": float(timeline.TimelineLength),
                "tracks": [{"name": str(t.TrackName), "samples": [float(t.CurveFloat.call_function("GetFloatValue", value))
                             for value in (0.0, .25, .5, .75, 1.0)]} for t in timeline.FloatTracks]} for timeline in bp.Timelines]
            rows.append({"asset": path, "class": bp.GeneratedClass.get_path_name(), "defaults": defaults,
                "signatures": signatures, "timelines": timelines, "properties": sorted(cdo.properties())})
        else:
            data = ue.load_object(ue.find_class("LyraWeaponPickupDefinition"), path)
            pickups.append({"asset": path, "properties": {field: serial(data.get_property(field)) for field in
                ("InventoryItemDefinition", "SpawnCoolDownSeconds", "DisplayMesh", "WeaponMeshOffset", "WeaponMeshScale")}})
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("spawner input changed during read-only audit")
    return {"status": "passed", "runtime_acceptance": False, "reference_hashes": hashes, "assets": rows, "pickups": pickups}

try:
    report = audit()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(arg("UEPSpawnerAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_SPAWNER_AUDIT_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
