"""Configure original Jump/shared-widget BP classes in a marked disposable copy."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_jump_ability_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from message_payload_graphs import connect


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def defaults(cdo):
    result = {key: int(cdo.get_property(key)) for key in ("InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy")}
    for field in ("WidgetClass",):
        if field in cdo.properties():
            value = cdo.get_property(field); result[field] = value.get_path_name() if value is not None else None
    if "WidgetExtensionPointTag" in cdo.properties(): result["WidgetExtensionPointTag"] = str(cdo.WidgetExtensionPointTag.TagName)
    if "WidgetClasses" in cdo.properties(): result["WidgetClasses"] = [value.get_path_name() if value else None for value in cdo.WidgetClasses]
    if "WidgetExtensionPointTags" in cdo.properties(): result["WidgetExtensionPointTags"] = [str(value.TagName) for value in cdo.WidgetExtensionPointTags]
    return result


def generate():
    stage = require_authoring_stage(arg("UEPJumpStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    original = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    rows, hashes, assets = [], {}, []
    for name, module, profile, asset_name in (
        ("GA_AbilityWithWidget", "widget_lifecycle", "LyraAbilityWidget", "DA_AbilityWidgetMixin"),
        ("GA_Hero_Jump", "jump_mixin", "LyraJump", "DA_JumpAbilityMixin")):
        relative = Path("Content/Characters/Heroes/Abilities")/(name+".uasset")
        hashes[str(original/relative)] = hashlib.sha256((original/relative).read_bytes()).hexdigest()
        ue.unregister_all_mixins()
        bp = ue.load_object(Blueprint, "/Game/Characters/Heroes/Abilities/"+name+"."+name)
        before_defaults = defaults(bp.GeneratedClass.get_cdo())
        methods = ["K2_OnAbilityAdded", "K2_OnAbilityRemoved"]+(["K2_ActivateAbility"] if name == "GA_Hero_Jump" else [])
        signatures = {method: ue.describe_function(bp.GeneratedClass, method) for method in methods}
        original_graphs = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
        digests = {graph.get_name(): semantics(graph, names, set()) for graph, names in original_graphs}
        if name == "GA_Hero_Jump":
            ue.blueprint_add_member_variable(bp, "UEPJumpTearingDown", EdGraphPinType(PinCategory="bool"))
            notify_graph = ue.blueprint_add_function(bp, "UEPJumpNativeEnded")
            notify_graph.Nodes[0].node_create_pin(1, EdGraphPinType(PinCategory="bool"), "bWasCancelled")
            ue.compile_blueprint(bp)
            event = bp.UbergraphPages[0]
            end = event.graph_add_node_event(ue.find_class("GameplayAbility"), "K2_OnEndAbility")
            end.set_property("bOverrideFunction", True)
            branch = event.graph_add_node(K2Node_IfThenElse)
            guard = event.graph_add_node_variable_get("UEPJumpTearingDown")
            notify = event.graph_add_node_call_function(bp.GeneratedClass.UEPJumpNativeEnded)
            connect(end, "then", branch, "execute"); connect(guard, "UEPJumpTearingDown", branch, "Condition")
            connect(branch, "else", notify, "execute"); connect(end, "bWasCancelled", notify, "bWasCancelled")
        path = "/Game/UEPMixins/"+asset_name
        if ue.find_asset(path+"."+asset_name) is not None:
            raise RuntimeError("fresh jump/widget Mixin authoring required")
        factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(asset_name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
        mixin.DefaultProfile = "Python"
        mixin.Profiles = [UEPPythonMixinProfile(ProfileName=value, PythonModule="uep_lyra_abilities."+module,
            PythonClass=profile+value+"Profile") for value in ("Python", "BlueprintFallback")]
        ue.unregister_all_mixins(); ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
        ue.compile_blueprint(bp)
        if int(bp.Status) == 2 or bp.GeneratedClass.get_name() != name+"_C" or defaults(bp.GeneratedClass.get_cdo()) != before_defaults:
            raise RuntimeError("jump/widget original class or defaults changed")
        if any(ue.describe_function(bp.GeneratedClass, method) != signature for method, signature in signatures.items()):
            raise RuntimeError("jump/widget original function signature changed")
        for graph, names in original_graphs:
            if semantics(graph, names, set()) != digests[graph.get_name()]:
                raise RuntimeError("jump/widget original business graph changed")
        if name == "GA_Hero_Jump" and ue.describe_function(bp.GeneratedClass, "K2_OnEndAbility")["owner"] != bp.GeneratedClass.get_path_name():
            raise RuntimeError("jump native-end adapter was not compiled on the original class")
        bp.save_package(); mixin.save_package()
        assets.extend([str(relative), "Content/UEPMixins/"+asset_name+".uasset"])
        rows.append(dict(original_class=bp.GeneratedClass.get_path_name(), defaults=before_defaults,
            original_graphs=digests, original_signatures=signatures, native_end_adapter=name == "GA_Hero_Jump"))
    for file, expected in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != expected: raise RuntimeError("official ability asset changed")
    return dict(schema_version=1, status="passed", runtime_acceptance=False, full_acceptance=False,
        assets=assets, classes=rows, reference_hashes=hashes, original_class_defaults_signatures_and_graphs_preserved=True)


try:
    report = generate()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPJumpAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_JUMP_ABILITY_ASSETS_"+report["status"].upper())
if report["status"] != "passed": raise RuntimeError(report["error"])
