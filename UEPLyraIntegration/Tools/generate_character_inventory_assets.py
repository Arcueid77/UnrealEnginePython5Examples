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


def possession_graph(originals):
    graph, = [graph for graph, _ in originals if graph.get_name() == "EventGraph"]
    event, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "ReceivePossessed"]
    output, = event.node_find_pin("then").get_linked_to(); authority = output.owning_node
    if authority.get_class().get_name() != "K2Node_MacroInstance": raise RuntimeError("original possession authority is not a macro")
    macro = authority.node_get_macro_graph()
    calls = [node for node in macro.Nodes if node.get_class().get_name() == "K2Node_CallFunction" and str(node.FunctionReference.MemberName) == "HasAuthority"]
    if macro.get_path_name() != "/Engine/EditorBlueprintResources/ActorMacros.ActorMacros:Switch Has Authority" or len(calls) != 1:
        raise RuntimeError("original possession macro does not call native HasAuthority: "+macro.get_path_name())
    branch, = [node for node in macro.Nodes if node.get_class().get_name() == "K2Node_IfThenElse"]
    condition, = branch.node_find_pin("Condition").get_linked_to()
    if condition.owning_node != calls[0] or condition.name != "ReturnValue": raise RuntimeError("original authority branch does not use native HasAuthority result")
    target, = authority.node_find_pin("Authority").get_linked_to(); factory = target.owning_node
    if authority.node_find_pin("Remote").get_linked_to() or event.node_find_pin("NewController").get_linked_to() or factory.get_class().get_name() != "K2Node_AsyncAction" or str(factory.ProxyFactoryFunctionName) != "WaitForExperienceReady" or factory.ProxyFactoryClass != ue.find_class("AsyncAction_ExperienceReady") or factory.node_find_pin("WorldContextObject").get_linked_to() or factory.node_find_pin("then").get_linked_to():
        raise RuntimeError("original possession authority/factory/context/controller semantics differ")
    continuation, = factory.node_find_pin("OnReady").get_linked_to()
    if continuation.owning_node.node_get_macro_graph().get_name() != "WaitForInventoryReadiness":
        raise RuntimeError("original possession Experience continuation differs")
    return dict(authority_macro=macro.get_path_name(), authority_macro_semantics=semantics(macro, {node.get_name() for node in macro.Nodes}, set()), factory="WaitForExperienceReady",
        remote_branch_noop=True, controller_parameter_unused=True, implicit_self_world_context=True, parent_event_called=False,
        original_continuation="WaitForInventoryReadiness")


def visibility_graph(originals):
    from uep_lyra_characters.visibility_mixin import SHOW
    graph, = [graph for graph, _ in originals if graph.get_name() == "EventGraph"]
    event, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CustomEvent" and str(node.CustomFunctionName) == SHOW]
    pin, = event.node_find_pin("then").get_linked_to(); delay = pin.owning_node
    if str(delay.FunctionReference.MemberName) != "DelayUntilNextTick" or event.node_find_pin("Params").get_linked_to() or delay.node_find_pin("WorldContextObject").get_linked_to() or delay.node_find_pin("LatentInfo").get_linked_to():
        raise RuntimeError("original visibility input/native delay semantics differ")
    pin, = delay.node_find_pin("then").get_linked_to(); show = pin.owning_node
    if str(show.FunctionReference.MemberName) != "SetActorHiddenInGame" or show.node_find_pin("bNewHidden").default_value != "false" or show.node_find_pin("bNewHidden").get_linked_to() or show.node_find_pin("then").get_linked_to():
        raise RuntimeError("original visibility continuation is not exactly SetActorHiddenInGame(false)")
    return dict(callback=SHOW, payload_ignored=True, scheduler="DelayUntilNextTick", hidden_after_resume=False, whole_begin_play_migrated=False)


def begin_play_graph(originals):
    graph, = [graph for graph, _ in originals if graph.get_name() == "EventGraph"]
    event, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "ReceiveBeginPlay"]
    pin, = event.node_find_pin("then").get_linked_to(); parent = pin.owning_node
    if parent.get_class().get_name() != "K2Node_CallParentFunction" or str(parent.FunctionReference.MemberName) != "ReceiveBeginPlay": raise RuntimeError("original BeginPlay parent call differs")
    pin, = parent.node_find_pin("then").get_linked_to(); listen = pin.owning_node
    pin, = listen.node_find_pin("then").get_linked_to(); hide = pin.owning_node
    pin, = hide.node_find_pin("then").get_linked_to(); register = pin.owning_node
    if str(listen.FunctionReference.MemberName) != "ListenForTeam" or str(hide.FunctionReference.MemberName) != "SetActorHiddenInGame" or hide.node_find_pin("bNewHidden").default_value != "true" or hide.node_find_pin("bNewHidden").get_linked_to() or str(register.FunctionReference.MemberName) != "RegisterAndCallForInitStateChange" or register.node_find_pin("RequiredState").default_value != '(TagName="InitState.GameplayReady")' or register.node_find_pin("bCallImmediately").default_value != "true" or register.node_find_pin("then").get_linked_to():
        raise RuntimeError("original BeginPlay ordered listener/hide/InitState registration differs")
    component, = register.node_find_pin("self").get_linked_to(); callback, = register.node_find_pin("Delegate").get_linked_to()
    if str(component.owning_node.VariableReference.MemberName) != "PawnExtComponent" or str(callback.owning_node.CustomFunctionName) != "ShowPawnAgainNextFrame": raise RuntimeError("original BeginPlay component/named delegate differs")
    return parent, dict(order=["parent", "listen", "hide", "register"], component="PawnExtComponent", tag="InitState.GameplayReady", call_immediately=True)


def generate(stage, audio=False, quickbar=False, loadout=False, outline=False, team=False, stencil=False, lifecycle=False, parts=False, health=False, enhanced=False, observer=False, listener=False, legacy=False, ready=False, waiting=False, possessed=False, visibility=False, beginning=False, hiding=False):
    beginning = beginning or hiding
    visibility = visibility or beginning
    possessed = possessed or visibility
    waiting = waiting or possessed
    ready = ready or waiting
    legacy = legacy or ready
    listener = listener or legacy
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
        (hiding, "characterequipmenthide", "EquipmentHide", "equipment_hide_mixin"),
        (beginning, "characterbeginplay", "BeginPlay", "begin_play_mixin"),
        (visibility, "charactervisibility", "Visibility", "visibility_mixin"),
        (possessed, "characterpossessed", "Possessed", "possessed_mixin"),
        (waiting, "characterwait", "InventoryWait", "inventory_wait_mixin"),
        (ready, "characterready", "InventoryReady", "inventory_ready_mixin"),
        (legacy, "characterlegacy", "LegacyPlayerInfo", "legacy_player_info_mixin"),
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
    if ready:
        from uep_lyra_characters.inventory_ready_mixin import READY
    if visibility:
        from uep_lyra_characters.visibility_mixin import SHOW, RESUME as VISIBILITY_RESUME
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = source/RELATIVE; digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original Character required")
    bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    if ready:
        # Loading existing dependent Blueprints can compile them. Do that while
        # the root is still the untouched original, before declaring routers.
        for name in ("BP_CharacterTeamListenProbe", "BP_CharacterLegacyPlayerInfoProbe"):
            ue.load_object(Blueprint, "/Game/UEPValidation/"+name+"."+name)
            ue.unregister_all_mixins()
    before, cls = cdo_snapshot(bp, "character-before"), bp.GeneratedClass.get_path_name()
    bindings_before = input_bindings(bp.GeneratedClass) if enhanced else None
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in
        (("ClearInventory", "AddInitialInventory", "K2_OnDeathFinished", "K2_OnReset", "ReceiveBeginPlay", "ReceivePossessed")+
            (("GetEmoteAudioComponent", "SetEmoteAudioComponent") if audio else ())+(("ChangeQuickbarSlot",) if quickbar else ())+(("CreateOrUpdateOutlineIfNeeded",) if outline else ())+(("OnTeamOrCosmeticsChanged",) if team else ())+(("UpdateCustomStencilFromTeamID",) if stencil else ())+((BOUND_EVENT,) if parts else ())+((HEALTH_EVENT,) if health else ())+((OBSERVER_EVENT, "ListenForTeam") if observer else ())+(("OnRep_PlayerInfo",) if legacy else ())+((READY,) if ready else ())+((SHOW,) if visibility else ())+(("HideEquippedWeapons",) if hiding else ())) }
    input_signatures = {value["action"]: ue.describe_function(bp.GeneratedClass, value["function"]) for value in bindings_before} if enhanced else {}
    originals = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    possession = possession_graph(originals) if possessed else None
    visibility_original = visibility_graph(originals) if visibility else None
    parent_source, begin_original = begin_play_graph(originals) if beginning else (None, None)
    graphs = {graph.get_name(): semantics(graph, names, set()) for graph, names in originals}
    if legacy:
        graph, = [value for value, _ in originals if value.get_name() == "OnRep_PlayerInfo"]
        call, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallFunction"]
        if len(graph.Nodes) != 2 or str(call.FunctionReference.MemberName) != "OnTeamOrCosmeticsChanged" or call.node_find_pin("TeamID").default_value != "0" or call.node_find_pin("TeamDisplayAsset").default_object is not None or call.node_find_pin("TeamID").get_linked_to() or call.node_find_pin("TeamDisplayAsset").get_linked_to():
            raise RuntimeError("original legacy team refresh literal defaults differ")
    name = "DA_Character"+prefix+"Mixin"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None: raise RuntimeError("fresh Character inventory Mixin required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_characters."+module,
        PythonClass="LyraCharacter"+prefix+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    transport = ready_transport = wait_stub = visibility_stub = visibility_transport = None
    if listener:
        from generate_character_team_listener_transport import generate as listener_transport
        transport = listener_transport(bp)
    if ready:
        from generate_character_inventory_ready_probe import transport as experience_transport
        ready_transport = experience_transport(bp)
    if waiting:
        from generate_character_inventory_wait_stub import generate as resume_stub
        wait_stub = resume_stub(bp)
    if visibility:
        visibility_stub = resume_stub(bp, VISIBILITY_RESUME)
        from generate_character_visibility_transport import generate as visibility_registration
        visibility_transport = visibility_registration(bp)
    if beginning:
        from generate_character_begin_play_parent import generate as begin_parent
        parent_transport = begin_parent(bp, parent_source)
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
    extra_graphs = {"GetPythonMixinSet", "GetPythonMixinProfile"} | ({transport["function"]} if listener else set()) | ({ready_transport["function"]} if ready else set()) | ({wait_stub["function"]} if waiting else set())
    if visibility: extra_graphs |= {visibility_stub["function"], visibility_transport["function"]}
    if beginning: extra_graphs.add(parent_transport["function"])
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
    if legacy:
        report["implemented_methods"].append("OnRep_PlayerInfo")
        report["legacy_player_info_literal_defaults"] = dict(team_id=0, display_asset=None)
        report["legacy_named_player_info_property_present"] = "PlayerInfo" in bp.GeneratedClass.get_cdo().properties()
    if ready:
        report["implemented_methods"].append(READY)
        macro, = [graph for graph, _ in originals if graph.get_name() == "WaitForInventoryReadiness"]
        delays = [node for node in macro.Nodes if node.get_class().get_name() == "K2Node_CallFunction" and str(node.FunctionReference.MemberName) == "DelayUntilNextTick"]
        if len(delays) != 3: raise RuntimeError("original deferred inventory wait macro differs")
        report["inventory_ready_immediate_branch_migrated"] = True
        report["inventory_ready_receiver"] = READY
        report["native_inventory_ready_transport"] = ready_transport
        report["inventory_ready_pending_wait_migrated"] = waiting
        report["original_inventory_readiness_macro_retained"] = True
    if waiting:
        report["implemented_methods"].append(wait_stub["function"])
        report["native_inventory_wait_stub"] = wait_stub
        report["native_inventory_wait_resume_signature"] = ue.describe_function(bp.GeneratedClass, wait_stub["function"])
        report["native_inventory_wait_signatures"] = {name: ue.describe_function(ue.find_class("KismetSystemLibrary"), name) for name in ("DelayUntilNextTick", "GetFrameCount")}
    if possessed:
        report["implemented_methods"].append("ReceivePossessed")
        report["original_possession_semantics"] = possession
        report["experience_ready_factory_migrated"] = True
        report["native_possession_factory_signatures"] = {name: ue.describe_function(ue.find_class(cls), name) for cls, name in (
            ("AsyncAction_ExperienceReady", "WaitForExperienceReady"), ("AsyncAction_ExperienceReady", "Activate"), ("Actor", "HasAuthority"))}
    if visibility:
        report["implemented_methods"] += [SHOW, VISIBILITY_RESUME]
        report.update(visibility_callback_business_migrated=True, original_visibility_semantics=visibility_original,
            native_visibility_resume_stub=visibility_stub, native_visibility_registration_transport=visibility_transport,
            native_visibility_resume_signature=ue.describe_function(bp.GeneratedClass, VISIBILITY_RESUME),
            native_visibility_signatures={name: ue.describe_function(ue.find_class(cls), name) for cls, name in (
                ("GameFrameworkInitStateInterface", "RegisterAndCallForInitStateChange"), ("Actor", "SetActorHiddenInGame"))})
    if beginning:
        report["implemented_methods"].append("ReceiveBeginPlay")
        report.update(begin_play_business_migrated=True, original_begin_play_semantics=begin_original, native_begin_play_parent_transport=parent_transport)
    if hiding:
        report["implemented_methods"].append("HideEquippedWeapons")
        parent_path = "Content/Characters/Heroes/B_Hero_Default.uasset"
        parent_bp = ue.load_object(Blueprint, "/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default")
        graph, = [value for value in ue.blueprint_get_all_graphs(parent_bp) if value.get_name() == "HideEquippedWeapons"]
        functions = [str(node.FunctionReference.MemberName) for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallFunction"]
        if sorted(functions) != sorted(("GetComponentByClass", "GetEquipmentInstancesOfType", "GetSpawnedActors", "SetActorHiddenInGame")) or len(graph.Nodes) != 8:
            raise RuntimeError("original inherited equipment-hide graph differs")
        call, = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_CallFunction" and str(node.FunctionReference.MemberName) == "SetActorHiddenInGame"]
        if call.node_find_pin("bNewHidden").default_value != "true" or call.node_find_pin("bNewHidden").get_linked_to(): raise RuntimeError("original inherited equipment hide literal differs")
        hashes = {str(root/parent_path): hashlib.sha256((root/parent_path).read_bytes()).hexdigest() for root in (source, stage)}
        if len(set(hashes.values())) != 1: raise RuntimeError("official/staged inherited Hero parent drift")
        from generate_character_equipment_hide_probe import generate as hide_probe
        report.update(inherited_equipment_hide_migrated=True, inherited_equipment_hide_owner=signatures["HideEquippedWeapons"]["owner"],
            inherited_equipment_hide_graph=semantics(graph, {node.get_name() for node in graph.Nodes}, set()), inherited_equipment_parent_hashes=hashes,
            equipment_hide_probe=hide_probe(stage, bp.GeneratedClass))
        report["native_equipment_hide_signatures"] = {name: ue.describe_function(ue.find_class(cls), name) for cls, name in (
            ("LyraEquipmentManagerComponent", "GetEquipmentInstancesOfType"), ("LyraEquipmentInstance", "GetSpawnedActors"), ("Actor", "SetActorHiddenInGame"))}
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
    if legacy:
        from generate_character_legacy_player_info_probe import generate as legacy_probe
        report["legacy_player_info_probe"] = legacy_probe(stage, bp.GeneratedClass, reuse=ready)
    if ready:
        from generate_character_inventory_ready_probe import generate as ready_probe
        report["inventory_ready_probe"] = ready_probe(stage, bp.GeneratedClass)
    if parts:
        # Verify temporary injection only after all Blueprint compiler work.
        # No dependent fixture is compiled against a transient router function.
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
        if waiting and ue.describe_function(bp.GeneratedClass, wait_stub["function"]) != report["native_inventory_wait_resume_signature"]:
            raise RuntimeError("native inventory wait resume signature not restored")
        if visibility and ue.describe_function(bp.GeneratedClass, VISIBILITY_RESUME) != report["native_visibility_resume_signature"]:
            raise RuntimeError("native visibility resume signature not restored")
    return report
