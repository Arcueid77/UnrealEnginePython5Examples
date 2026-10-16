"""Configure helper-only Mixin; no original AutoRespawn graph/latent edits."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics

PACKAGE = "/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn"
RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Game/Respawn/GA_AutoRespawn.uasset"
METHODS = ("GetOwningPlayerState", "Is Avatar Dead or Dying", "EndDeathAbilities")


def cdo_snapshot(bp, label):
    result = next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-UEPHeroAbilityAssetsResult="))
    path = Path(result).parent/("auto-respawn-helpers-"+label+"-cdo.t3d")
    if not ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(bp.GeneratedClass.get_cdo(), str(path)):
        raise RuntimeError("AutoRespawn CDO export failed")
    raw = path.read_bytes(); text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("PythonMixinProfile=", "PythonMixinSet=")))


def generate(stage, listener_transports=None, event_transports=None):
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = source/RELATIVE; digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original AutoRespawn required")
    bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    before, cls_path = cdo_snapshot(bp, "before"), bp.GeneratedClass.get_path_name()
    methods = METHODS+("BindDeathListener", "ClearDeathListener", "OnDeathStarted", "OnAvatarEndPlay",
        "K2_ActivateAbility", "K2_OnPawnAvatarSet", "K2_OnAbilityAdded", "K2_OnAbilityRemoved", "K2_OnEndAbility")
    signatures = {method: ue.describe_function(bp.GeneratedClass, method) for method in methods}
    originals = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    graphs = {graph.get_name(): semantics(graph, names, set()) for graph, names in originals}
    transport = listener_transports(bp) if listener_transports else []
    events = event_transports(bp, originals) if event_transports else None
    if events: graphs = events["original_graphs"]
    name = "DA_AutoRespawnListenersMixin" if listener_transports else "DA_AutoRespawnHelpersMixin"
    module = "auto_respawn_listeners_mixin" if listener_transports else "auto_respawn_helpers_mixin"
    prefix = "LyraAutoRespawnListeners" if listener_transports else "LyraAutoRespawnHelpers"
    if events: name, module, prefix = "DA_AutoRespawnEventsMixin", "auto_respawn_events_mixin", "LyraAutoRespawnEvents"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None: raise RuntimeError("fresh AutoRespawn helper Mixin required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities."+module,
        PythonClass=prefix+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != cls_path or cdo_snapshot(bp, "after") != before:
        raise RuntimeError("original AutoRespawn identity/full CDO changed")
    for name_, description in signatures.items():
        if ue.describe_function(bp.GeneratedClass, name_) != description: raise RuntimeError("original AutoRespawn signature changed: "+name_)
    after = {graph.get_name(): semantics(graph, {node.get_name() for node in graph.Nodes}, set()) for graph in ue.blueprint_get_all_graphs(bp)}
    additions = sorted(set(after)-set(graphs))
    expected_additions = sorted(["GetPythonMixinProfile", "GetPythonMixinSet"]+[row["function"] for row in transport])
    if events: expected_additions = sorted(expected_additions+events["gate_functions"])
    checked = {graph.get_name(): semantics(graph, names, set(map(tuple, events["dispatch_transport_endpoints"]))
        if graph.get_name() == events["dispatch_graph"] else set()) for graph, names in originals} if events else after
    if additions != expected_additions or any(checked.get(key) != value for key, value in graphs.items()):
        raise RuntimeError("original AutoRespawn business/latent/listener graph changed; added="+repr(additions))
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(original.read_bytes()).hexdigest() != digest: raise RuntimeError("official AutoRespawn changed")
    return dict(status="passed", kind="autorespawnevents" if events else "autorespawnlisteners" if listener_transports else "autorespawnhelpers", runtime_acceptance=False, full_acceptance=False,
        native_end_adapter_nodes=0, original_class=cls_path, original_signature=signatures[METHODS[0]], extra_signatures=signatures,
        original_class_defaults_signature_graphs_preserved=True, original_full_cdo_preserved=True,
        original_graphs_unmodified=not bool(events), original_business_graphs_preserved_with_dispatch=bool(events),
        original_graphs=graphs, added_interface_graphs=["GetPythonMixinProfile", "GetPythonMixinSet"],
        event_transport=events,
        typed_listener_transports=transport, typed_listener_transport_nodes=sum(row["nodes"] for row in transport),
        original_entry_transport_nodes=0, named_query_output="IsDeadOrDying",
        implemented_methods=list(METHODS)+(["BindDeathListener", "ClearDeathListener"] if listener_transports else [])+
            (["OnDeathStarted", "OnAvatarEndPlay"]+events["gate_functions"] if events else []),
        death_listener_orchestration_migrated=bool(listener_transports),
        death_listener_timer_restart_business_migrated=bool(events),
        assets=[RELATIVE, "Content/UEPMixins/"+name+".uasset"], reference_hashes={str(original): digest})
