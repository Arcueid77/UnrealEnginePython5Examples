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


def generate(stage, audio=False, quickbar=False, loadout=False, outline=False, team=False):
    outline = outline or team
    loadout = loadout or outline
    quickbar = quickbar or loadout
    audio = audio or quickbar
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = source/RELATIVE; digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original Character required")
    bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    before, cls = cdo_snapshot(bp, "character-before"), bp.GeneratedClass.get_path_name()
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in
        (("ClearInventory", "AddInitialInventory", "K2_OnDeathFinished", "K2_OnReset", "ReceiveBeginPlay", "ReceivePossessed")+
            (("GetEmoteAudioComponent", "SetEmoteAudioComponent") if audio else ())+(("ChangeQuickbarSlot",) if quickbar else ())+(("CreateOrUpdateOutlineIfNeeded",) if outline else ())+(("OnTeamOrCosmeticsChanged",) if team else ())) }
    originals = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    graphs = {graph.get_name(): semantics(graph, names, set()) for graph, names in originals}
    name = "DA_CharacterTeamMixin" if team else "DA_CharacterOutlineMixin" if outline else "DA_CharacterLoadoutMixin" if loadout else "DA_CharacterQuickbarMixin" if quickbar else "DA_CharacterAudioMixin" if audio else "DA_CharacterInventoryMixin"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None: raise RuntimeError("fresh Character inventory Mixin required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_characters."+("team_cosmetics_mixin" if team else "outline_mixin" if outline else "initial_inventory_mixin" if loadout else "quickbar_input_mixin" if quickbar else "emote_audio_mixin" if audio else "inventory_clear_mixin"),
        PythonClass=("LyraCharacterTeam" if team else "LyraCharacterOutline" if outline else "LyraCharacterLoadout" if loadout else "LyraCharacterQuickbar" if quickbar else "LyraCharacterAudio" if audio else "LyraCharacterInventory")+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != cls or cdo_snapshot(bp, "character-after") != before:
        raise RuntimeError("original Character identity/full CDO changed")
    for method, signature in signatures.items():
        if ue.describe_function(bp.GeneratedClass, method) != signature: raise RuntimeError("original Character signature changed: "+method)
    all_graphs = ue.blueprint_get_all_graphs(bp)
    if set(graph.get_name() for graph in all_graphs)-set(graphs) != {"GetPythonMixinSet", "GetPythonMixinProfile"}:
        raise RuntimeError("unexpected Character graph additions")
    if any(semantics(graph, names, set()) != graphs[graph.get_name()] for graph, names in originals):
        raise RuntimeError("original Character business/animation/input graph changed")
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(original.read_bytes()).hexdigest() != digest: raise RuntimeError("official Character asset changed")
    report = dict(status="passed", kind="characterteam" if team else "characteroutline" if outline else "characterloadout" if loadout else "characterquickbar" if quickbar else "characteraudio" if audio else "characterinventory", runtime_acceptance=False, full_acceptance=False, native_end_adapter_nodes=0,
        original_class=cls, original_signature=signatures["ClearInventory"], extra_signatures=signatures,
        original_class_defaults_signature_graphs_preserved=True, original_full_cdo_preserved=True, original_graphs_unmodified=True,
        original_graphs=graphs, implemented_methods=["ClearInventory"]+(["GetEmoteAudioComponent", "SetEmoteAudioComponent"] if audio else [])+(["ChangeQuickbarSlot"] if quickbar else [])+(["AddInitialInventory"] if loadout else [])+(["CreateOrUpdateOutlineIfNeeded"] if outline else [])+(["OnTeamOrCosmeticsChanged"] if team else []), added_interface_graphs=["GetPythonMixinSet", "GetPythonMixinProfile"],
        assets=[RELATIVE, "Content/UEPMixins/"+name+".uasset"], reference_hashes={str(original): digest})
    if team:
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
    return report
