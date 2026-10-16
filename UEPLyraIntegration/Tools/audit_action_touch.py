"""Read-only touch button defaults, native signatures and actual composition."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "audit_action_touch.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))


def serial(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "get_path_name"):
        return value.get_path_name()
    if hasattr(value, "TagName"):
        return str(value.TagName)
    if all(hasattr(value, key) for key in ("Left", "Top", "Right", "Bottom")):
        return [float(getattr(value, key)) for key in ("Left", "Top", "Right", "Bottom")]
    if hasattr(value, "ImageSize"):
        return dict(size=[float(value.ImageSize.x), float(value.ImageSize.y)],
                    resource=serial(value.ResourceObject), draw_as=int(value.DrawAs))
    return str(value)


def audit():
    stage = require_authoring_stage(arg("UEPActionTouchStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes, rows = {}, []
    fields = ("AssociatedAction", "DurationMessageTag", "Charging", "Duration", "StartTime", "HasCooldown", "IsToggleButton",
              "IsDisabled", "UseBacking", "UseShadow", "UseBlur", "UseGlow", "UseGlowBoost", "HitTestPadding",
              "ButtonBrush", "ButtonGlowBrush", "GlowOverdraw", "BlurCornerRadius", "BlurPadding",
              "TickFrequency", "bHasScriptImplementedTick", "Visibility")
    functions = ("PreConstruct", "Construct", "Tick", "OnInitialized", "BP_OnClicked", "BP_OnDisabled", "BP_OnEnabled",
                 "BP_OnSelected", "BP_OnDeselected", "SetButtonStyle", "ResetMaterials", "UpdateCoolDownPercent", "ListenForDuration", "Destruct")
    for name in ("W_ActionTouchButton", "W_ActionTouchButton_MobileOnly"):
        relative = Path("Content/UI/Hud")/(name+".uasset")
        pair = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (stage, reference)}
        if len(set(pair.values())) != 1:
            raise RuntimeError("original touch inputs required")
        hashes.update(pair)
        bp = ue.load_object(ue.find_class("Blueprint"), "/Game/UI/Hud/"+name+"."+name)
        cdo = bp.GeneratedClass.get_cdo()
        rows.append(dict(asset=bp.get_path_name(), parent=bp.ParentClass.get_path_name(),
            defaults={n: serial(cdo.get_property(n)) for n in fields if n in cdo.properties()},
            properties=sorted(cdo.properties()), signatures={n: ue.describe_function(bp.GeneratedClass, n) for n in functions}))
    fire = ue.load_object(ue.find_class("Blueprint"), "/ShooterCore/UserInterface/W_FireButton.W_FireButton")
    fire_path = stage/"Plugins/GameFeatures/ShooterCore/Content/UserInterface/W_FireButton.uasset"
    hashes[str(fire_path)] = hashlib.sha256(fire_path.read_bytes()).hexdigest()
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("read-only touch input changed")
    return dict(status="passed", runtime_acceptance=False, assets=rows, reference_hashes=hashes,
        fire_button_parent=fire.ParentClass.get_path_name(), fire_button_is_composite_not_subclass=fire.ParentClass.get_path_name() == "/Script/UMG.UserWidget")


try:
    report = audit()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPActionTouchAuditResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_ACTION_TOUCH_AUDIT_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
