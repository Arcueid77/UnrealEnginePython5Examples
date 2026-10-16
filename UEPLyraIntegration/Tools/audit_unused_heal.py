"""Read native dependency closure for the old heal ability; no blind exclusion."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "audit_unused_heal.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

PACKAGE = "/ShooterCore/Items/HealthPickup_Unused/GA_HealPickup"


def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))


def audit():
    stage = require_authoring_stage(arg("UEPUnusedHealStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    relative = "Plugins/GameFeatures/ShooterCore/Content/Items/HealthPickup_Unused/GA_HealPickup.uasset"
    hashes = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (stage, reference)}
    if len(set(hashes.values())) != 1:
        raise RuntimeError("original unused-heal inputs required")
    asset_filter = ue.FARFilter()
    asset_filter.package_paths = ["/ShooterCore/Items/HealthPickup_Unused"]
    asset_filter.recursive_paths = True
    # This UEP API calls synchronous native SearchAllAssets(true) before the
    # filtered query; an unscanned registry must never masquerade as zero refs.
    registry_assets = ue.get_assets_by_filter(asset_filter, True)
    bp = ue.load_object(ue.find_class("Blueprint"), PACKAGE+".GA_HealPickup")
    cdo = bp.GeneratedClass.get_cdo()
    defaults = {}
    for name in ("Heal Montage", "Heal Effect", "InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationOwnedTags"):
        if name in cdo.properties():
            value = cdo.get_property(name)
            defaults[name] = value.get_path_name() if hasattr(value, "get_path_name") else (value if isinstance(value, (int, float, bool, str)) else str(value))
    pending, refs, limit = [PACKAGE], {}, 250
    while pending:
        package = pending.pop(0)
        if package in refs:
            continue
        if len(refs) >= limit:
            raise RuntimeError("reference closure exceeded bounded audit; no unreachable claim")
        values = sorted(set(str(p) for p in ue.get_asset_referencers(package, 31))-{package})
        refs[package] = values
        pending.extend(value for value in values if value not in refs)
    dependencies = sorted(str(p) for p in ue.get_asset_dependencies(PACKAGE, 31))
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("read-only unused-heal changed")
    return dict(status="passed", runtime_acceptance=False, assets=[dict(asset=bp.get_path_name(),
        parent=bp.ParentClass.get_path_name(), all_dependency_referencer_closure=refs, dependencies=dependencies,
        properties=sorted(cdo.properties()), defaults=defaults,
        signatures={name: ue.describe_function(bp.GeneratedClass, name) for name in ("K2_ActivateAbility", "End Heal", "K2_OnEndAbility")},
        task_factory_signature=ue.describe_function(ue.find_class("AbilityTask_PlayMontageAndWait"), "CreatePlayMontageAndWaitProxy"))],
        reference_hashes=hashes, dependency_mask=31, source_string_reference_audit_required=True,
        synchronous_asset_registry_scan=True, unused_folder_asset_count=len(registry_assets),
        disposition="review_native_reference_closure_and_dynamic_loading_before_retention", migration_complete=False)


try:
    report = audit()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPUnusedHealAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_UNUSED_HEAL_AUDIT_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
