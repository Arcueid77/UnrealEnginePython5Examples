"""Read unchanged AutoRespawn defaults/signatures; no Blueprint compile/save."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "audit_auto_respawn_helpers.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage

PACKAGE = "/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn"
RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Game/Respawn/GA_AutoRespawn.uasset"
METHODS = ("GetOwningPlayerState", "Is Avatar Dead or Dying", "EndDeathAbilities")


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def audit():
    stage = require_authoring_stage(arg("UEPAutoRespawnHelpersStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes = {str(root/RELATIVE): hashlib.sha256((root/RELATIVE).read_bytes()).hexdigest() for root in (stage, source)}
    if len(set(hashes.values())) != 1: raise RuntimeError("unchanged original AutoRespawn asset required")
    cls = ue.load_class(PACKAGE+"_C"); ue.unregister_all_mixins()
    cdo = cls.get_cdo()
    output = Path(arg("UEPAutoRespawnHelpersAuditResult"))
    cdo_path = output.parent/"GA_AutoRespawn-cdo.t3d"
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    if not exporter.export_to_file(cdo, str(cdo_path)): raise RuntimeError("native AutoRespawn CDO export failed")
    defaults = {name: cdo.get_property(name) for name in
        ("RespawnDelayDuration", "InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationPolicy")}
    signatures = {name: ue.describe_function(cls, name) for name in METHODS}
    native = {clsname+"."+name: ue.describe_function(ue.find_class(clsname), name) for clsname, name in
        (("AbilitySystemComponent", "FindAllAbilitiesWithTags"), ("AbilitySystemBlueprintLibrary", "GetGameplayAbilityFromSpecHandle"))}
    for path, digest in hashes.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest: raise RuntimeError("original AutoRespawn changed")
    return dict(status="passed", runtime_acceptance=False, full_acceptance=False, assets_modified=False,
        assets=[dict(path=PACKAGE, defaults=defaults, signatures=signatures, native_signatures=native,
            native_cdo_text_export=str(cdo_path))], reference_hashes=hashes,
        helper_scope=list(METHODS), death_listener_timer_restart_business_migrated=False)


try:
    result = audit()
    Path(arg("UEPAutoRespawnHelpersAuditResult")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    ue.log("UEP_AUTO_RESPAWN_HELPERS_AUDIT_PASSED")
except Exception:
    Path(arg("UEPAutoRespawnHelpersAuditResult")).write_text(json.dumps(dict(status="failed", error=traceback.format_exc())), encoding="utf-8")
    ue.log_error(traceback.format_exc())
    raise
