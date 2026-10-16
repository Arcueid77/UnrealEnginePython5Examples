"""Read unchanged original ability cost/failure-message defaults; no asset save."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "audit_native_ability_producers.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

PACKAGES = ("/ShooterCore/Game/Dash/GA_Hero_Dash", "/ShooterCore/Input/Abilities/GA_Grenade",
    "/ShooterCore/Weapons/Pistol/GA_Weapon_Fire_Pistol", "/ShooterCore/Weapons/Rifle/GA_Weapon_Fire_Rifle_Auto",
    "/ShooterCore/Weapons/Shotgun/GA_Weapon_Fire_Shotgun", "/Game/Weapons/Pistol/GA_Weapon_Reload_Pistol",
    "/Game/Weapons/GA_Weapon_Fire", "/Game/Characters/Heroes/Abilities/GA_Hero_Heal")


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(serial(key)): serial(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(item) for item in value]
    if hasattr(value, "get_path_name"):
        return value.get_path_name()
    if hasattr(value, "TagName"):
        return str(value.TagName)
    if hasattr(value, "GameplayTags"):
        return [serial(item) for item in value.GameplayTags]
    return str(value)


def audit():
    stage = require_authoring_stage(arg("UEPAbilityProducerStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes, rows = {}, []
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    for package in PACKAGES:
        mount, relative = package[1:].split("/", 1)
        relative = Path("Content" if mount == "Game" else "Plugins/GameFeatures/"+mount+"/Content")/(relative+".uasset")
        pair = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (stage, source)}
        if len(set(pair.values())) != 1:
            raise RuntimeError("native producer audit requires unchanged original ability: "+package)
        hashes.update(pair)
        name = package.rsplit("/", 1)[1]
        cls = ue.load_class(package+"."+name+"_C")
        cdo = cls.get_cdo()
        # TMap<GameplayTag,...> cannot be returned as a Python dict: the current
        # struct wrapper is deliberately unhashable. Existing native T3D export
        # reads the exact serialized map without a C++ change or wildcard thunk.
        text_path = Path(arg("UEPAbilityProducerAuditResult")).parent/(name+"-cdo.t3d")
        if not exporter.export_to_file(cdo, str(text_path)):
            raise RuntimeError("native CDO text export failed: "+package)
        raw = text_path.read_bytes()
        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
        map_fields = ("FailureTagToUserFacingMessages", "FailureTagToAnimMontage")
        fields = ("AdditionalCosts", "CostGameplayEffectClass",
            "CooldownGameplayEffectClass", "InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationPolicy",
            "ActivationRequiredTags", "ActivationBlockedTags", "ActivationOwnedTags", "CancelAbilitiesWithTag", "BlockAbilitiesWithTag")
        row = dict(ability=cls.get_path_name(), defaults={field: serial(cdo.get_property(field)) for field in fields if field in cdo.properties()},
            native_cdo_text_export=str(text_path), native_failure_map_lines=[line.strip() for line in text.splitlines()
                if any(field in line for field in map_fields)],
            native_additional_costs=[])
        if "AdditionalCosts" in cdo.properties():
            for cost in cdo.get_property("AdditionalCosts"):
                if cost is None:
                    continue
                values = {field: serial(cost.get_property(field)) for field in cost.properties()
                          if any(word in field.lower() for word in ("cost", "tag", "count", "amount", "apply"))}
                row["native_additional_costs"].append(dict(object=cost.get_path_name(), type=cost.get_class().get_path_name(), defaults=values))
        rows.append(row)
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("read-only native producer audit changed input")
    return dict(status="passed", runtime_acceptance=False, native_failure_producer_tested=False,
        native_ability_cost_refusal_tested=False, assets_modified=False, abilities=rows, reference_hashes=hashes)


try:
    report = audit()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPAbilityProducerAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_ABILITY_PRODUCER_AUDIT_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
