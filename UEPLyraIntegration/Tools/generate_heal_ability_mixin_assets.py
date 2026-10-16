"""Original ability class/graph, one direct Mixin Set and native task observation."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "generate_heal_ability_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from message_payload_graphs import connect


def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))


def generate():
    stage = require_authoring_stage(arg("UEPUnusedHealStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    path = reference/"Plugins/GameFeatures/ShooterCore/Content/Items/HealthPickup_Unused/GA_HealPickup.uasset"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, "/ShooterCore/Items/HealthPickup_Unused/GA_HealPickup.GA_HealPickup")
    cdo = bp.GeneratedClass.get_cdo()
    defaults = {name: cdo.get_property(name) for name in ("Heal Montage", "Heal Effect", "InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy")}
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in ("K2_ActivateAbility", "End Heal")}
    event = bp.UbergraphPages[0]
    tasks = [n for n in event.Nodes if n.get_class().get_name() == "K2Node_LatentAbilityCall"]
    if len(tasks) != 1:
        raise RuntimeError("one original heal Montage task required")
    task = tasks[0]; names = {n.get_name() for n in event.Nodes}; ignored = {(task.get_name(), "then")}
    before = semantics(event, names, ignored)
    ue.blueprint_add_member_variable(bp, "UEPOriginalHealTask", EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("AbilityTask_PlayMontageAndWait")))
    ue.compile_blueprint(bp)
    links = task.node_find_pin("then").get_linked_to()
    if len(links) != 1:
        raise RuntimeError("original heal task continuation differs")
    task.node_find_pin("then").break_link_to(links[0])
    setter = event.graph_add_node_variable_set("UEPOriginalHealTask")
    connect(task, "then", setter, "execute"); setter.node_find_pin("then").make_link_to(links[0])
    connect(task, "AsyncTaskProxy", setter, "UEPOriginalHealTask")
    # Native GAS EndAbility is allowed during Profile teardown, while routed
    # Python callbacks deliberately are not. Original End Heal is a single
    # native EndAbility forwarder: leave it UNMIXED, including fallback task/
    # timer delegates. Only the normal native end notification enters Python.
    ue.blueprint_add_member_variable(bp, "UEPHealTearingDown", EdGraphPinType(PinCategory="bool"))
    native_end = ue.blueprint_add_function(bp, "UEPHealNativeEnded")
    native_end.Nodes[0].node_create_pin(1, EdGraphPinType(PinCategory="bool"), "bWasCancelled")
    ue.compile_blueprint(bp)
    end_event = event.graph_add_node_event(ue.find_class("GameplayAbility"), "K2_OnEndAbility")
    end_event.set_property("bOverrideFunction", True)
    branch = event.graph_add_node(K2Node_IfThenElse)
    guard = event.graph_add_node_variable_get("UEPHealTearingDown")
    notify = event.graph_add_node_call_function(bp.GeneratedClass.UEPHealNativeEnded)
    connect(end_event, "then", branch, "execute"); connect(guard, "UEPHealTearingDown", branch, "Condition")
    connect(branch, "else", notify, "execute"); connect(end_event, "bWasCancelled", notify, "bWasCancelled")
    name = "DA_HealAbilityMixin"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None:
        raise RuntimeError("fresh heal ability Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=p, PythonModule="uep_lyra_world.heal_ability_mixin",
        PythonClass="LyraHealAbility"+p+"Profile") for p in ("Python", "BlueprintFallback")]
    ue.unregister_all_mixins(); ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(bp); cdo = bp.GeneratedClass.get_cdo()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_name() != "GA_HealPickup_C" or cdo.GetPythonMixinSet() != mixin:
        raise RuntimeError("heal ability original class/Set differs")
    if any(cdo.get_property(name) != value for name, value in defaults.items()):
        raise RuntimeError("original heal Montage/effect/instancing/network defaults changed")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()):
        raise RuntimeError("original heal signature changed")
    if ue.describe_function(bp.GeneratedClass, "K2_OnEndAbility")["owner"] != bp.GeneratedClass.get_path_name():
        raise RuntimeError("native end notification override was not compiled on the original ability class")
    if semantics(bp.UbergraphPages[0], names, ignored) != before:
        raise RuntimeError("original heal graph changed beyond task transport")
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("official heal ability changed")
    return dict(status="passed", runtime_acceptance=False, class_preserved=True, single_parent_interface_set=True,
        gate_count=0, original_blocks_retained=True, original_graphs=[dict(graph="EventGraph", original_semantic_digest=before,
            dispatch_transport_endpoints=sorted(ignored))], direct_function_mixin=True,
        original_montage_effect_instancing_network_preserved=True, original_task_exposed_for_observation=True,
        native_end_lifecycle_adapter_nodes=4, original_end_heal_unmixed_forwarder=True,
        reference_hashes={str(path): digest})


try:
    report = generate()
except Exception:
    report = dict(status="failed", error=traceback.format_exc())
Path(arg("UEPGenerateHealAbilityResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_HEAL_ABILITY_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
