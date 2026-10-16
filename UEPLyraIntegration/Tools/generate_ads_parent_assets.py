"""ADS typed gates on its existing shared-parent router, no related routers."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, UEPPythonMixinSet, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_ads_parent_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import make_gate, insert_gate, semantics
from message_payload_graphs import connect

PARENT = "/Game/Characters/Heroes/Abilities/GA_AbilityWithWidget.GA_AbilityWithWidget"
ADS = "/ShooterCore/Input/Abilities/GA_ADS.GA_ADS"
SET = "/Game/UEPMixins/DA_AbilityWidgetMixin.DA_AbilityWidgetMixin"
ACTIVATE, END, BROADCAST, GUARD = "UEPADSActivateGate", "UEPADSNativeEndGate", "UEPADSBroadcastGate", "UEPADSTearingDown"
RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Input/Abilities/GA_ADS.uasset"


def arg(name): return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))
def one(values):
    if len(values) != 1: raise RuntimeError("one ADS original entry required")
    return values[0]


def defaults(cdo):
    result = {name: int(cdo.get_property(name)) for name in ("InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationPolicy")}
    for name in ("ADSMultiplier", "Max Walk SpeedDefault"):
        if name in cdo.properties(): result[name] = float(cdo.get_property(name))
    result.update(WidgetClasses=[value.get_path_name() if value else None for value in cdo.WidgetClasses],
        WidgetExtensionPointTags=[str(value.TagName) for value in cdo.WidgetExtensionPointTags])
    return result


def profile_rows(mixin):
    return [(str(value.ProfileName), str(value.PythonModule), str(value.PythonClass)) for value in mixin.Profiles]


def generate():
    stage = require_authoring_stage(arg("UEPADSParentStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes = {str(reference/name): hashlib.sha256((reference/name).read_bytes()).hexdigest()
        for name in (RELATIVE, "Content/Characters/Heroes/Abilities/GA_AbilityWithWidget.uasset")}
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != hashes[str(reference/RELATIVE)]:
        raise RuntimeError("ADS parent authoring requires restored original child asset")
    ue.unregister_all_mixins()
    parent, child, mixin = ue.load_object(Blueprint, PARENT), ue.load_object(Blueprint, ADS), ue.load_object(UEPPythonMixinSet, SET)
    ue.unregister_all_mixins()
    original_defaults = {"parent": defaults(parent.GeneratedClass.get_cdo()), "ads": defaults(child.GeneratedClass.get_cdo())}
    signatures = {name: ue.describe_function(child.GeneratedClass, name) for name in ("K2_ActivateAbility", "K2_OnEndAbility", "BroadcastToUI", "K2_OnAbilityAdded", "K2_OnAbilityRemoved")}
    existing_profiles, default_profile = profile_rows(mixin), str(mixin.DefaultProfile)
    event = child.UbergraphPages[0]
    entries = {method: one([node for node in event.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == method])
        for method in ("K2_ActivateAbility", "K2_OnEndAbility")}
    broadcast = one([graph for graph in child.FunctionGraphs if graph.get_name() == "BroadcastToUI"])
    broadcast_entry = one([node for node in broadcast.Nodes if node.get_class().get_name() == "K2Node_FunctionEntry"])
    ignored = {(node.get_name(), "then") for node in list(entries.values())+[broadcast_entry]}
    snapshots = {}
    for label, bp in (("parent", parent), ("ads", child)):
        snapshots[label] = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    digests = {label: {graph.get_name(): semantics(graph, names, ignored if label == "ads" else set()) for graph, names in rows}
        for label, rows in snapshots.items()}
    make_gate(parent, ACTIVATE, None)
    make_gate(parent, END, "bWasCancelled", entries["K2_OnEndAbility"].node_find_pin("bWasCancelled"))
    make_gate(parent, BROADCAST, "ON", broadcast_entry.node_find_pin("ON"))
    ue.compile_blueprint(parent)
    ue.blueprint_add_member_variable(child, GUARD, EdGraphPinType(PinCategory="bool")); ue.compile_blueprint(child)
    insert_gate(event, entries["K2_ActivateAbility"], "then", getattr(parent.GeneratedClass, ACTIVATE))
    insert_gate(broadcast, broadcast_entry, "then", getattr(parent.GeneratedClass, BROADCAST), "ON", "ON")
    insert_gate(event, entries["K2_OnEndAbility"], "then", getattr(parent.GeneratedClass, END), "bWasCancelled", "bWasCancelled")
    entry = entries["K2_OnEndAbility"]; target = one(entry.node_find_pin("then").get_linked_to())
    entry.node_find_pin("then").break_link_to(target)
    branch, get = event.graph_add_node(K2Node_IfThenElse), event.graph_add_node_variable_get(GUARD)
    connect(entry, "then", branch, "execute"); connect(get, GUARD, branch, "Condition"); branch.node_find_pin("else").make_link_to(target)
    if any(name in ("ADSPython", "ADSBlueprintFallback") for name, module, cls in existing_profiles):
        raise RuntimeError("fresh ADS parent profiles required")
    mixin.Profiles = list(mixin.Profiles)+[UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_abilities.ads_mixin", PythonClass=cls)
        for name, cls in (("ADSPython", "LyraADSPythonProfile"), ("ADSBlueprintFallback", "LyraADSBlueprintFallbackProfile"))]
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(child, mixin, "ADSPython", "PythonMixinProfile"); ue.compile_blueprint(child)
    ue.unregister_all_mixins()
    if int(parent.Status) == 2 or int(child.Status) == 2: raise RuntimeError("ADS parent/child compilation failed")
    if defaults(parent.GeneratedClass.get_cdo()) != original_defaults["parent"] or defaults(child.GeneratedClass.get_cdo()) != original_defaults["ads"]:
        raise RuntimeError("ADS parent/child business defaults changed")
    if str(mixin.DefaultProfile) != default_profile or profile_rows(mixin)[:len(existing_profiles)] != existing_profiles:
        raise RuntimeError("existing shared UI profiles/default changed")
    for name, before in signatures.items():
        if ue.describe_function(child.GeneratedClass, name) != before: raise RuntimeError("ADS public signature changed: "+name)
    for label, rows in snapshots.items():
        for graph, names in rows:
            if semantics(graph, names, ignored if label == "ads" else set()) != digests[label][graph.get_name()]:
                raise RuntimeError("ADS parent/child original business changed: "+label+"/"+graph.get_name())
    cdo = child.GeneratedClass.get_cdo()
    if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "ADSPython":
        raise RuntimeError("ADS CDO did not select shared-parent Set/Profile")
    parent.save_package(); child.save_package(); mixin.save_package()
    for file, digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest: raise RuntimeError("official ADS/parent asset changed")
    return dict(status="passed", kind="adsparent", runtime_acceptance=False, full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True, single_parent_router=True,
        original_defaults=original_defaults, original_signatures=signatures, original_graphs=digests,
        dispatch_transport_endpoints=sorted(ignored), existing_profiles_preserved=existing_profiles,
        new_profiles=["ADSPython", "ADSBlueprintFallback"], reference_hashes=hashes,
        assets=["Content/Characters/Heroes/Abilities/GA_AbilityWithWidget.uasset", "Content/UEPMixins/DA_AbilityWidgetMixin.uasset", RELATIVE])


try: report = generate()
except Exception: report = dict(status="failed", error=traceback.format_exc()); ue.log_error(report["error"])
Path(arg("UEPADSParentAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["status"] != "passed": raise RuntimeError(report["error"])
ue.log("UEP_ADS_PARENT_ASSETS_PASSED")
