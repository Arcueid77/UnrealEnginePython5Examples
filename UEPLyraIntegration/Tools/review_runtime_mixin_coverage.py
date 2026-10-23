"""Review native registration exceptions without promoting them to gameplay proof."""
import argparse
from collections import Counter
import json
from pathlib import Path

CHARACTER = "/Game/Characters/Character_Default.Character_Default"
PROMPT = "/ShooterExplorer/UserInterface/W_InteractionPrompt.W_InteractionPrompt"
PARENT = "/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default_C"
WIDGET = "/Game/Characters/Heroes/Abilities/GA_AbilityWithWidget.GA_AbilityWithWidget"
ADS = "/ShooterCore/Input/Abilities/GA_ADS.GA_ADS"
EMOTE = "/ShooterCore/Game/Emote/GA_Emote.GA_Emote"
ADS_GATES = {"UEPADSActivateGate", "UEPADSBroadcastGate", "UEPADSNativeEndGate"}
EMOTE_GATES = {"UEPEmoteActivateGate", "UEPEmoteMovementGate", "UEPEmoteNativeEndGate"}
MACROS = {
    "/Game/Audio/Blueprints/WeaponAudioMacros.WeaponAudioMacros": "141-audio-vfx-macro-python-consumer-closure.json",
    "/ShooterCore/Blueprint/Macros/BPML_VFXMacros.BPML_VFXMacros": "141-audio-vfx-macro-python-consumer-closure.json",
    "/Game/UI/Menu/Experiences/UIExperienceMacros.UIExperienceMacros": "162-ui-experience-preparation-python-consumer-closure.json"}
FORWARDERS = {
    "/Game/Characters/Heroes/B_SimpleHeroPawn.B_SimpleHeroPawn",
    "/ShooterExplorer/Blueprint/B_SimpleFollowPawn.B_SimpleFollowPawn",
    "/ShooterExplorer/Blueprint/B_SimpleFollowPawn_Big.B_SimpleFollowPawn_Big"}
EXPLORERS = {"/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer", "/ShooterExplorer/Blueprint/B_Pawn_Explorer.B_Pawn_Explorer"}
TOUCH_REGIONS = {"/Game/UI/Hud/W_TouchRegion_Right.W_TouchRegion_Right", "/ShooterCore/Input/W_TouchRegion_Left.W_TouchRegion_Left"}
PARENT_METHODS = {"AnimMotionEffect", "HideEquippedWeapons", "Ragdoll", "UEPHeroDefaultAfterDeathDelay", "UpdateCustomStencilFromTeamID",
    "BndEvt__HealthComponent_K2Node_ComponentBoundEvent_0_LyraHealth_DeathEvent__DelegateSignature"}


def require(value, message):
    if not value: raise ValueError(message)


def static_targets(asset):
    prefix = "/Game/UEPMixins/"
    def target(name): return prefix+name+"."+name+"_C"
    if asset == "/Game/Audio/Blueprints/GeneralAudioFunctions.GeneralAudioFunctions":
        return {"UEPGeneralAudioStinger": target("BP_GeneralAudioRouter")}
    if asset == "/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions":
        return {method: target(name) for method, name in (
            ("UEPAudioSendFire", "BP_WeaponAudioDispatchRouter"), ("UEPAudioSoundParams", "BP_WeaponAudioDispatchRouter"),
            ("UEPAudioDebugTap", "BP_WeaponAudioDispatchRouter"), ("UEPAudioTapProperties", "BP_WeaponAudioDispatchRouter"),
            ("UEPAudioEarlySchedule", "BP_WeaponAudioEarlyRouter"), ("UEPAudioSideAngles", "BP_WeaponAudioMathRouter"),
            ("UEPAudioWhizBy", "BP_WeaponAudioMathRouter"), ("UEPAudioWhizSchedule", "BP_WeaponAudioWhizRouter"))}
    return {}


def parent_binding(row):
    matches = [binding for binding in row["all_ancestor_bindings"] if binding["target_class"] == PARENT]
    require(len(matches) == 1 and PARENT_METHODS <= set(matches[0]["profiles"]["Python"]), "incomplete inherited Hero parent routes")


def forwarder_entries(row):
    for entry in row["staged_wired_entries"]:
        require(set(entry["reachable_node_classes"]) <= {"K2Node_CallParentFunction", "K2Node_FunctionResult", "K2Node_Knot"},
            "retained shell contains independent execution business")
        require(not entry["calls"] or set(entry["calls"]) == {entry["entry"]}, "retained shell calls a non-parent behavior")


def classify(row, by_path):
    asset = row["asset"]
    require(row["class_identity_preserved"] and row["original_class"] == asset+"_C", "original class identity changed")
    if row["native_router_class"] is None:
        if asset in TOUCH_REGIONS:
            forwarder_entries(row); return "retained-native-cpp-touch-parent-forwarder"
        targets = static_targets(asset)
        if targets:
            for method, target in targets.items():
                matches = [bridge for bridge in row["typed_dispatch_bridges"] if bridge["method"] == method and bridge["target"] == target]
                require(matches and all(bridge["default_profile"] == "Python" and method in bridge["profiles"]["Python"]["functions"] for bridge in matches),
                    "static library typed Python dispatch is missing: "+method)
            return "typed-static-python-forwarding"
        if asset in MACROS: return "retained-macro-definition-python-consumers"
        if asset == CHARACTER:
            forwarder_entries(row); return "retained-empty-native-parent-shell"
        if asset == PROMPT:
            require(all(not entry["calls"] and set(entry["reachable_node_classes"]) <= {"K2Node_DynamicCast"}
                for entry in row["staged_wired_entries"]), "prompt gained observable execution business")
            return "retained-unobservable-prompt-shell"
        raise ValueError("unreviewed candidate without native routing: "+asset)
    effective = row["effective_cdo_profile"]
    require(effective in ("Python", "ADSPython", "EmotePython") and effective in row["profiles"], "unsupported effective candidate Profile")
    missing = set(row["unimplemented_union_methods"])
    if missing:
        expected = {WIDGET: ("Python", ADS_GATES | EMOTE_GATES), ADS: ("ADSPython", EMOTE_GATES), EMOTE: ("EmotePython", ADS_GATES)}
        require(asset in expected and (effective, missing) == expected[asset], "unreviewed missing Python business methods")
        referenced = {call for entry in row["staged_wired_entries"] for call in entry["calls"]}
        require(not missing & referenced, "a referenced gate would fall through the effective Profile")
        definitions = {entry["entry"]: entry for entry in by_path[WIDGET]["staged_wired_entries"]}
        for method in missing:
            entry = definitions[method]
            require(not entry["calls"] and entry["reachable_node_classes"] == ["K2Node_FunctionResult"], "inactive family gate has execution business")
    if asset in FORWARDERS:
        forwarder_entries(row); parent_binding(row); return "retained-forwarder-inherited-python-parent"
    if asset in EXPLORERS: parent_binding(row)
    return "native-python-router-with-reviewed-family-stubs" if missing else "native-python-router"


def review(coverage, manifest):
    require(coverage["status"] == "passed" and coverage["all_original_candidates"] and
        coverage["coverage_is_registration_not_gameplay"] and not coverage["runtime_acceptance"] and not coverage["full_acceptance"], "not a complete read-only native inventory")
    rows = coverage["assets"]
    require(len(rows) == 246 and [row["asset"] for row in rows] == [row["path"] for row in manifest["assets"]], "original candidate order/scope changed")
    require([row["version"] for row in rows] == [row["version"] for row in manifest["assets"]], "original candidate versions changed")
    by_path = {row["asset"]: row for row in rows}; results = []
    for row, asset in zip(rows, manifest["assets"]):
        disposition = classify(row, by_path)
        if row["asset"] in EXPLORERS:
            require(set(asset["implemented_helpers"]) <= set(row["profiles"][row["effective_cdo_profile"]]["functions"]), "Explorer own declared methods lost their Python route")
        results.append(dict(asset=row["asset"], version=row["version"], disposition=disposition,
            effective_profile=row.get("effective_cdo_profile"), gameplay_completion_proven=False))
    return dict(schema_version=1, status="passed", reviewed_candidates=246, disposition_counts=dict(Counter(row["disposition"] for row in results)),
        registration_dispositions_reviewed=True, source_or_historical_semantic_evidence_still_required=True,
        native_business_executed=False, runtime_acceptance=False, full_migration_acceptance_proven=False, candidates=results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--coverage", required=True); parser.add_argument("--manifest", required=True); parser.add_argument("--result", required=True)
    args = parser.parse_args()
    report = review(json.loads(Path(args.coverage).read_text(encoding="utf-8-sig")), json.loads(Path(args.manifest).read_text(encoding="utf-8-sig")))
    Path(args.result).write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "candidates"}))
