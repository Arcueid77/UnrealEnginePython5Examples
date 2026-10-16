"""Read original reload child defaults/signatures and prototype reference closure."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "audit_reload_family.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

PACKAGES = ("/Game/Weapons/Pistol/GA_Weapon_Reload_Pistol", "/ShooterCore/Weapons/Rifle/GA_Weapon_Reload_Rifle",
    "/ShooterCore/Weapons/Shotgun/GA_Weapon_Reload_Shotgun", "/ShooterCore/Weapons/Shotgun/GA_Weapon_Reload_NetShooter",
    "/ShooterCore/Weapons/NetShooter_PROTO/ID_NetShooter")


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit():
    stage = require_authoring_stage(arg("UEPReloadFamilyStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes, rows = {}, []
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    for package in PACKAGES:
        mount, suffix = package[1:].split("/", 1)
        relative = Path("Content" if mount == "Game" else "Plugins/GameFeatures/"+mount+"/Content")/(suffix+".uasset")
        pair = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (source, stage)}
        if len(set(pair.values())) != 1: raise RuntimeError("original reload child/item asset required: "+package)
        hashes.update(pair)
        name = package.rsplit("/", 1)[1]; cls = ue.load_class(package+"."+name+"_C")
        ue.unregister_all_mixins(); cdo = cls.get_cdo()
        text = Path(arg("UEPReloadFamilyAuditResult")).parent/(name+"-cdo.t3d")
        if not exporter.export_to_file(cdo, str(text)): raise RuntimeError("native CDO export failed: "+package)
        defaults = {}
        for field in ("InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationPolicy", "ReloadMontage", "Playrate", "DidBlockFiring"):
            if field in cdo.properties():
                value = cdo.get_property(field)
                defaults[field] = value.get_path_name() if hasattr(value, "get_path_name") else value
        rows.append(dict(package=package, native_class=cls.get_path_name(), parent=cls.get_super_class().get_path_name(), defaults=defaults,
            signatures={name: ue.describe_function(cls, name) for name in
                ("K2_ActivateAbility", "K2_CanActivateAbility", "ReloadAmmoIntoMagazine", "K2_OnEndAbility")} if "ReloadMontage" in cdo.properties() else {},
            native_cdo_export=str(text), export_sha256=hashlib.sha256(text.read_bytes()).hexdigest()))
    registry = ue.FARFilter(); registry.package_paths = ["/ShooterCore/Weapons"]; registry.recursive_paths = True
    scanned = ue.get_assets_by_filter(registry, True)
    pending, closure = [PACKAGES[3], PACKAGES[4]], {}
    while pending:
        package = pending.pop(0)
        if package in closure: continue
        if len(closure) >= 500: raise RuntimeError("prototype reference closure exceeds bounded audit")
        refs = sorted(set(str(value) for value in ue.get_asset_referencers(package, 31))-{package})
        closure[package] = refs; pending.extend(value for value in refs if value not in closure)
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest: raise RuntimeError("read-only original reload asset changed")
    relative = Path("Plugins/GameFeatures/ShooterCore/Content/Weapons/NetShooter_PROTO/AbilitySet_ShooterNetShooter.uasset")
    pair = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (source, stage)}
    if len(set(pair.values())) != 1: raise RuntimeError("original prototype ability set required")
    hashes.update(pair)
    ability_set = ue.load_object(ue.find_class("LyraAbilitySet"),
        "/ShooterCore/Weapons/NetShooter_PROTO/AbilitySet_ShooterNetShooter.AbilitySet_ShooterNetShooter")
    grants = [dict(ability=value.Ability.get_path_name(), level=int(value.AbilityLevel), input_tag=str(value.InputTag.TagName))
        for value in ability_set.GrantedGameplayAbilities]
    return dict(status="passed", runtime_acceptance=False, assets_modified=False, assets=rows, reference_hashes=hashes,
        prototype_referencer_closure=closure, prototype_ability_grants=grants, synchronous_asset_registry_scan=True, weapon_registry_assets=len(scanned),
        dynamic_source_string_audit_required=True, prototype_unused_claimed=False, migration_complete=False)


try: report = audit()
except Exception: report = dict(status="failed", error=traceback.format_exc()); ue.log_error(report["error"])
Path(arg("UEPReloadFamilyAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_RELOAD_FAMILY_AUDIT_"+report["status"].upper())
if report["status"] != "passed": raise RuntimeError(report["error"])
