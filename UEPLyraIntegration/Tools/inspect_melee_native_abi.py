"""Read-only marked-stage native signatures; never a gameplay acceptance test."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "inspect_melee_native_abi.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


try:
    require_authoring_stage(arg("UEPDashRPCStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    report = dict(status="passed", runtime_acceptance=False, signatures={cls+"."+name: ue.describe_function(ue.find_class(cls), name)
        for cls, name in (("KismetSystemLibrary", "CapsuleTraceSingleForObjects"), ("KismetSystemLibrary", "LineTraceSingle"),
            ("GameplayStatics", "BreakHitResult"), ("LyraTeamSubsystem", "CompareTeams"))})
    for name in ("GCN_Weapon_Melee", "GCN_Weapon_MeleeImpact"):
        cls = ue.load_class("/ShooterCore/GameplayCues/"+name+"."+name+"_C")
        report[name] = str(cls.get_cdo().get_property("GameplayCueTag").TagName)
except Exception: report = dict(status="failed", error=traceback.format_exc(), runtime_acceptance=False)
Path(arg("UEPMeleeABIResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
(ue.log if report["status"] == "passed" else ue.log_error)("UEP_MELEE_ABI_DIAGNOSTIC_"+report["status"].upper())
