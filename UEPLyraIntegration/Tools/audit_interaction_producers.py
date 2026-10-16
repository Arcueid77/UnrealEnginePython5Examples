"""Read original interaction producer defaults and native transport dependencies."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "audit_interaction_producers.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

PACKAGES = ("/ShooterExplorer/Input/Abilities/GA_Interact", "/ShooterExplorer/Interact/GA_Interaction_Collect",
            "/ShooterExplorer/Interact/GA_Interaction_Sit", "/ShooterExplorer/Items/B_InteractableChair",
            "/ShooterExplorer/Items/B_InteractableRock")


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit():
    stage = require_authoring_stage(arg("UEPInteractionStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    official = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    exporter, rows, hashes = ue.new_object(ue.find_class("ObjectExporterT3D")), [], {}
    for package in PACKAGES:
        relative = Path("Plugins/GameFeatures/ShooterExplorer/Content")/(package.split("/", 2)[2]+".uasset")
        pair = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (stage, official)}
        if len(set(pair.values())) != 1:
            raise RuntimeError("interaction audit requires unchanged original assets: "+package)
        hashes.update(pair)
        cls = ue.load_class(package+"."+package.rsplit("/", 1)[1]+"_C")
        cdo = cls.get_cdo()
        text_path = Path(arg("UEPInteractionAuditResult")).parent/(cls.get_name()+".t3d")
        if not exporter.export_to_file(cdo, str(text_path)):
            raise RuntimeError("native interaction CDO export failed")
        raw = text_path.read_bytes()
        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
        defaults = {}
        for field in ("ActivationPolicy", "InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "bReplicates"):
            if field in cdo.properties():
                defaults[field] = int(cdo.get_property(field))
        if "Option" in cdo.properties():
            option = cdo.get_property("Option")
            ability = option.InteractionAbilityToGrant
            defaults["interaction_ability_to_grant"] = ability.get_path_name() if ability is not None else None
        rows.append(dict(asset=package, native_class=cls.get_path_name(), defaults=defaults, native_export=str(text_path),
            relevant_native_lines=[line.strip() for line in text.splitlines() if any(word in line for word in
                ("Option=", "Montage", "AbilityTriggers", "InteractionScan", "DefaultInteractionWidget", "ActivationBlocked"))]))
    if any(hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest for file, digest in hashes.items()):
        raise RuntimeError("read-only interaction audit changed a reference asset")
    return dict(schema_version=1, status="passed", runtime_acceptance=False, assets_modified=False,
                native_interaction_producer_tested=False, original_assets_unchanged=True, assets=rows, reference_hashes=hashes)


try:
    report = audit()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPInteractionAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_INTERACTION_PRODUCER_AUDIT_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
