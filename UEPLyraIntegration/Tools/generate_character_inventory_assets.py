"""One retained Character helper; preserve every original graph/CDO/signature."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics
from generate_auto_respawn_helper_assets import cdo_snapshot

RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Game/B_Hero_ShooterMannequin.uasset"
PACKAGE = "/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin"


def input_bindings(cls):
    values = []
    # UClass.get_property addresses instance fields, not class-object fields.
    # Existing typed UObject iteration can read only this generated class's
    # owned binding objects without reinterpreting memory or modifying C++.
    for binding in ue.tobject_iterator(ue.find_class("EnhancedInputActionDelegateBinding")):
        if binding.get_outer() == cls:
            for entry in binding.get_property("InputActionDelegateBindings"):
                values.append(dict(action=entry.InputAction.get_path_name(), trigger=int(entry.TriggerEvent), function=str(entry.FunctionNameToBind)))
    return sorted(values, key=lambda value: value["function"])


def generate(stage, audio=False, quickbar=False, loadout=False, outline=False, team=False, stencil=False, lifecycle=False, parts=False, health=False, enhanced=False, observer=False, listener=False):
    observer = observer or listener
    enhanced = enhanced or observer
    health = health or enhanced
    parts = parts or health
    lifecycle = lifecycle or parts
    stencil = stencil or lifecycle
    team = team or stencil
    outline = outline or team
    loadout = loadout or outline
    quickbar = quickbar or loadout
    audio = audio or quickbar
    kind, prefix, module = next((kind, prefix, module) for enabled, kind, prefix, module in (
        (listener, "characterlistener", "TeamListener", "team_listener_mixin"),
        (observer, "characterobserver", "TeamObserver", "team_observer_mixin"),
        (enhanced, "characterinput", "EnhancedInput", "enhanced_input_mixin"),
        (health, "characterhealth", "HealthChanged", "health_changed_mixin"),
        (parts, "characterparts", "PartsChanged", "parts_changed_mixin"),
        (lifecycle, "characterlifecycle", "Lifecycle", "lifecycle_mixin"),
        (stencil, "characterstencil", "Stencil", "stencil_mixin"),
        (team, "characterteam", "Team", "team_cosmetics_mixin"),
        (outline, "characteroutline", "Outline", "outline_mixin"),
        (loadout, "characterloadout", "Loadout", "initial_inventory_mixin"),
        (quickbar, "characterquickbar", "Quickbar", "quickbar_input_mixin"),
        (audio, "characteraudio", "Audio", "emote_audio_mixin"),
        (True, "characterinventory", "Inventory", "inventory_clear_mixin")) if enabled)
    if parts:
        from uep_lyra_characters.parts_changed_mixin import BOUND_EVENT
    if health:
        from uep_lyra_characters.health_changed_mixin import BOUND_EVENT as HEALTH_EVENT
    if enhanced:
        from uep_lyra_characters.enhanced_input_contract import ACTIONS
    if observer:
        from uep_lyra_characters.team_observer_mixin import BOUND_EVENT as OBSERVER_EVENT
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = source/RELATIVE; digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original Character required")
    bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    before, cls = cdo_snapshot(bp, "character-before"), bp.GeneratedClass.get_path_name()
    bindings_before = input_bindings(bp.GeneratedClass) if enhanced else None
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in
        (("ClearInventory", "AddInitialInventory", "K2_OnDeathFinished", "K2_OnReset", "ReceiveBeginPlay", "ReceivePossessed")+
            (("GetEmoteAudioComponent", "SetEmoteAudioComponent") if audio else ())+(("ChangeQuickbarSlot",) if quickbar else ())+(("CreateOrUpdateOutlineIfNeeded",) if outline else ())+(("OnTeamOrCosmeticsChanged",) if team else ())+(("UpdateCustomStencilFromTeamID",) if stencil else ())+((BOUND_EVENT,) if parts else ())+((HEALTH_EVENT,) if health else ())+((OBSERVER_EVENT, "ListenForTeam") if observer else ())) }
    input_signatures = {value["action"]: ue.describe_function(bp.GeneratedClass, value["function"]) for value in bindings_before} if enhanced else {}
    originals = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    graphs = {graph.get_name(): semantics(graph, names, set()) for graph, names in originals}
    name = "DA_Character"+prefix+"Mixin"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None: raise RuntimeError("fresh Character inventory Mixin required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_characters."+module,
        PythonClass="LyraCharacter"+prefix+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    transport = None
    if listener:
        from generate_character_team_listener_transport import generate as listener_transport
        transport = listener_transport(bp)
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != cls or cdo_snapshot(bp, "character-after") != before:
        raise RuntimeError("original Character identity/full CDO changed")
    for method, signature in signatures.items():
        if ue.describe_function(bp.GeneratedClass, method) != signature: raise RuntimeError("original Character signature changed: "+method)
    bindings_after = input_bindings(bp.GeneratedClass) if enhanced else None
    if enhanced:
        logical = lambda rows: sorted((value["action"], value["trigger"]) for value in rows)
        if logical(bindings_before) != logical(bindings_after) or len(bindings_after) != 5 or any(value["trigger"] != 1 for value in bindings_after):
            raise RuntimeError("original native input action/trigger binding semantics changed")
        for value in bindings_after:
            actual = ue.describe_function(bp.GeneratedClass, value["function"])
            if actual != input_signatures[value["action"]]: raise RuntimeError("compiler-generated input receiver signature changed")
            signatures[value["function"]] = actual
    all_graphs = ue.blueprint_get_all_graphs(bp)
    extra_graphs = {"GetPythonMixinSet", "GetPythonMixinProfile"} | ({transport["function"]} if listener else set())
    if set(graph.get_name() for graph in all_graphs)-set(graphs) != extra_graphs:
        raise RuntimeError("unexpected Character graph additions")
    if any(semantics(graph, names, set()) != graphs[graph.get_name()] for graph, names in originals):
        raise RuntimeError("original Character business/animation/input graph changed")
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(original.read_bytes()).hexdigest() != digest: raise RuntimeError("official Character asset changed")
    report = dict(status="passed", kind=kind, runtime_acceptance=False, full_acceptance=False, native_end_adapter_nodes=0,
        original_class=cls, original_signature=signatures["ClearInventory"], extra_signatures=signatures,
        original_class_defaults_signature_graphs_preserved=True, original_full_cdo_preserved=True, original_graphs_unmodified=True,
        original_graphs=graphs, implemented_methods=["ClearInventory"]+(["GetEmoteAudioComponent", "SetEmoteAudioComponent"] if audio else [])+(["ChangeQuickbarSlot"] if quickbar else [])+(["AddInitialInventory"] if loadout else [])+(["CreateOrUpdateOutlineIfNeeded"] if outline else [])+(["OnTeamOrCosmeticsChanged"] if team else [])+(["UpdateCustomStencilFromTeamID"] if stencil else [])+(["K2_OnDeathFinished", "K2_OnReset"] if lifecycle else [])+([BOUND_EVENT] if parts else [])+([HEALTH_EVENT] if health else [])+([value["function"] for value in bindings_after] if enhanced else [])+([OBSERVER_EVENT] if observer else []), added_interface_graphs=["GetPythonMixinSet", "GetPythonMixinProfile"],
        assets=[RELATIVE, "Content/UEPMixins/"+name+".uasset"], reference_hashes={str(original): digest})
    if listener:
        report["implemented_methods"].append("ListenForTeam")
        report["native_team_listener_transport"] = transport
        report["native_team_listener_transport_signature"] = ue.describe_function(bp.GeneratedClass, transport["function"])
    if team:
        if stencil:
            if lifecycle:
                from generate_character_stencil_probe import describe_existing as probe
            else:
                from generate_character_stencil_probe import generate as probe
            report["caller_probe"] = probe(stage, bp.GeneratedClass)
            team_probe = stage/"Content/UEPValidation/BP_CharacterTeamCallProbe.uasset"
            report["team_caller_probe"] = dict(asset=str(team_probe), sha256=hashlib.sha256(team_probe.read_bytes()).hexdigest())
            parent = "Content/Characters/Heroes/B_Hero_Default.uasset"
            parent_hashes = {str(root/parent): hashlib.sha256((root/parent).read_bytes()).hexdigest() for root in (stage, source)}
            if len(set(parent_hashes.values())) != 1: raise RuntimeError("original stencil parent asset changed")
            report["inherited_stencil_parent_reference_hashes"] = parent_hashes
            report["inherited_parent_asset_unmodified"] = True
        else:
            from generate_character_team_probe import generate as probe
            report["caller_probe"] = probe(stage, bp.GeneratedClass)
        report["native_team_signatures"] = {name: ue.describe_function(ue.find_class(cls), name) for cls, name in (
            ("LyraTeamStatics", "GetTeamColorWithFallback"), ("LyraTeamDisplayAsset", "ApplyToActor"),
            ("InputDeviceSubsystem", "ActivateDevicePropertyOfClass"))}
    elif outline:
        from generate_character_outline_probe import generate as probe
        report["caller_probe"] = probe(stage, bp.GeneratedClass)
        report["native_camera_interface_signature"] = ue.describe_function(ue.find_class("CameraComponent"), "AddOrUpdateBlendable")
    elif loadout:
        from generate_character_loadout_probe import generate as probe
        report["caller_probe"] = probe(stage, bp.GeneratedClass)
    elif quickbar:
        from generate_character_quickbar_probe import generate as probe
        report["caller_probe"] = probe(stage, bp.GeneratedClass)
    elif audio:
        from generate_character_audio_probe import generate as probe
        report["caller_probe"] = probe(stage, source)
    if parts:
        report["native_parts_signatures"] = {name: ue.describe_function(ue.find_class(cls), name) for cls, name in (
            ("LyraTeamStatics", "FindTeamFromObject"), ("LyraPawnComponent_CharacterParts", "AddCharacterPart"),
            ("LyraPawnComponent_CharacterParts", "RemoveCharacterPart"))}
        try:
            ue.register_declared_mixin(bp.GeneratedClass)
            registered, = [entry for entry in ue.get_registered_mixins() if entry["target_class"] == bp.GeneratedClass]
            expected = set(report["implemented_methods"])
            fallback_expected = expected-{value["function"] for value in bindings_after} if enhanced else expected
            if set(registered["functions"]) != expected or set(registered["profiles"]["Python"]["functions"]) != expected or set(registered["profiles"]["BlueprintFallback"]["functions"]) != fallback_expected:
                raise RuntimeError("component-bound receiver is not actually routed on both profiles")
            report["actual_native_registered_profile_method_counts"] = {name: len(value["functions"]) for name, value in registered["profiles"].items()}
        finally:
            ue.unregister_all_mixins()
        if any(ue.describe_function(bp.GeneratedClass, name) != signature for name, signature in signatures.items()):
            raise RuntimeError("native component receiver registration did not restore original signatures")
        report["component_bound_receiver"] = BOUND_EVENT
        report["native_component_receiver_register_restore_passed"] = True
    if health:
        report["health_component_bound_receiver"] = HEALTH_EVENT
        report["native_health_signatures"] = {name: ue.describe_function(ue.find_class(cls), name) for cls, name in (
            ("AISense_Damage", "ReportDamageEvent"), ("AIBlueprintHelperLibrary", "GetAIController"),
            ("AIPerceptionComponent", "GetActorsPerception"))}
    if enhanced:
        report.update(original_enhanced_input_binding_semantics_preserved=True, compiler_receiver_names_resolved_dynamically=True,
            automatic_native_original_input_fallback=True, python_input_action_value_roundtrip_supported=False,
            original_enhanced_input_bindings=bindings_before, enhanced_input_bindings=bindings_after,
            native_input_signatures={name: ue.describe_function(ue.find_class(cls), name) for cls, name in (
                ("EnhancedInputLocalPlayerSubsystem", "InjectInputVectorForAction"), ("SubsystemBlueprintLibrary", "GetLocalPlayerSubsystem"))})
    if observer:
        from generate_character_team_listener_probe import generate as listener_probe
        report["team_listener_probe"] = listener_probe(stage, bp.GeneratedClass, reuse=listener)
        report["native_team_observer_signatures"] = {name: ue.describe_function(ue.find_class(cls), name) for cls, name in (
            ("AsyncAction_ObserveTeamColors", "ObserveTeamColors"), ("CancellableAsyncAction", "Cancel"), ("CancellableAsyncAction", "IsActive"))}
        report["team_observer_callback"] = OBSERVER_EVENT
        report["original_listener_factory_orchestration_remains_bp"] = not listener
    return report
