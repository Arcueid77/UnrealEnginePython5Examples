"""Configure one retained hero ability in the marked disposable Lyra copy."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_hero_ability_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics, make_gate, insert_gate
from message_payload_graphs import connect


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def defaults(cdo):
    result = {key: int(cdo.get_property(key)) for key in
              ("InstancingPolicy", "NetExecutionPolicy", "NetSecurityPolicy", "ActivationPolicy")}
    for field in ("Duration", "Camera Mode", "PollInterval", "TimeSinceActivityToReload", "GE_Heal", "HealMontage", "ADSMultiplier", "Max Walk SpeedDefault", "ReloadMontage", "Playrate", "DidBlockFiring", "SpawnMontage", "EnableInputAfterTimeFraction"):
        if field in cdo.properties():
            value = cdo.get_property(field)
            result[field] = value.get_path_name() if hasattr(value, "get_path_name") else value
    if "WidgetClasses" in cdo.properties(): result["WidgetClasses"] = [value.get_path_name() if value else None for value in cdo.WidgetClasses]
    if "WidgetExtensionPointTags" in cdo.properties(): result["WidgetExtensionPointTags"] = [str(value.TagName) for value in cdo.WidgetExtensionPointTags]
    return result


def spawn_cdo_snapshot(bp, label):
    path = Path(arg("UEPHeroAbilityAssetsResult")).parent/("spawn-effect-"+label+"-cdo.t3d")
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    if not exporter.export_to_file(bp.GeneratedClass.get_cdo(), str(path)): raise RuntimeError("native SpawnEffect CDO export failed")
    raw = path.read_bytes()
    text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    allowed = ("PythonMixinProfile=", "PythonMixinSet=", "UEPSpawnEffectTearingDown=")
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(allowed))


def generate():
    stage = require_authoring_stage(arg("UEPHeroAbilityStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    kind = arg("UEPHeroAbilityKind")
    if kind == "scoreboardrows":
        from generate_scoreboard_row_assets import generate as generate_scoreboard_rows
        return generate_scoreboard_rows(stage)
    if kind == "eliminationwidgets":
        from generate_elimination_widget_assets import generate as generate_elimination_widgets
        return generate_elimination_widgets(stage)
    if kind == "accoladewidgets":
        from generate_accolade_widget_assets import generate as generate_accolade_widgets
        return generate_accolade_widgets(stage)
    if kind == "accoladerelay":
        from generate_accolade_relay_assets import generate as generate_accolade_relay
        return generate_accolade_relay(stage)
    if kind == "eliminationfeedrelay":
        from generate_elimination_feed_relay_assets import generate as generate_elimination_feed_relay
        return generate_elimination_feed_relay(stage)
    if kind == "controlpointfeedback":
        from generate_control_point_feedback_assets import generate as generate_control_point_feedback
        return generate_control_point_feedback(stage)
    if kind == "controlpointstate":
        from generate_control_point_state_assets import generate as generate_control_point_state
        return generate_control_point_state(stage)
    if kind == "controlpointhelpers":
        from generate_control_point_helpers_assets import generate as generate_control_point_helpers
        return generate_control_point_helpers(stage)
    if kind == "cpscoring":
        from generate_cp_scoring_assets import generate as generate_cp_scoring
        return generate_cp_scoring(stage)
    if kind == "tdmscoring":
        from generate_tdm_scoring_assets import generate as generate_tdm_scoring
        return generate_tdm_scoring(stage)
    if kind == "scoringbase":
        from generate_scoring_base_assets import generate as generate_scoring_base
        return generate_scoring_base(stage)
    if kind == "physicsfields":
        from generate_physics_field_assets import generate as generate_physics_fields
        return generate_physics_fields(stage)
    if kind == "smallburstcues":
        from generate_small_burst_cue_assets import generate as generate_small_burst_cues
        return generate_small_burst_cues(stage)
    if kind == "spawningcue":
        from generate_spawning_cue_assets import generate as generate_spawning_cue
        return generate_spawning_cue(stage)
    if kind == "traversalcues":
        from generate_traversal_cue_assets import generate as generate_traversal_cues
        return generate_traversal_cues(stage)
    if kind == "heroburstcues":
        from generate_hero_burst_cue_assets import generate as generate_hero_burst_cues
        return generate_hero_burst_cues(stage)
    if kind == "characterdamage":
        from generate_character_damage_assets import generate as generate_character_damage
        return generate_character_damage(stage)
    if kind == "messagewidgets":
        from generate_message_widget_assets import generate as generate_message_widgets
        return generate_message_widgets(stage)
    if kind == "cuewidgets":
        from generate_cue_widget_assets import generate as generate_cue_widgets
        return generate_cue_widgets(stage)
    if kind == "footstep":
        from generate_footstep_assets import generate as generate_footstep
        return generate_footstep(stage)
    if kind == "generalaudio":
        from generate_general_audio_assets import generate as generate_general_audio
        return generate_general_audio(stage)
    if kind == "windsystem":
        from generate_wind_assets import generate as generate_wind
        return generate_wind(stage)
    if kind == "musiccontrols":
        from generate_music_manager_assets import generate as generate_music_controls
        return generate_music_controls(stage)
    if kind == "weaponaudiomath":
        from generate_weapon_audio_math_assets import generate as generate_weapon_audio_math
        return generate_weapon_audio_math(stage)
    if kind == "weaponfirecues":
        from generate_weapon_fire_cue_assets import generate as generate_weapon_fire_cues
        return generate_weapon_fire_cues(stage)
    if kind == "netshooterability":
        from generate_netshooter_ability_assets import generate as generate_netshooter_ability
        return generate_netshooter_ability(stage)
    if kind == "netshooteractor":
        from generate_netshooter_actor_assets import generate as generate_netshooter_actor
        return generate_netshooter_actor(stage)
    if kind == "weaponabilityfire":
        from generate_weapon_ability_fire_assets import generate as generate_weapon_ability_fire
        return generate_weapon_ability_fire(stage)
    if kind == "weaponimpacts":
        from generate_weapon_impacts_assets import generate as generate_weapon_impacts
        return generate_weapon_impacts(stage)
    if kind == "weapondecals":
        from generate_weapon_decals_assets import generate as generate_weapon_decals
        return generate_weapon_decals(stage)
    if kind == "weaponfirefx":
        from generate_weapon_fire_fx_assets import generate as generate_weapon_fx
        return generate_weapon_fx(stage)
    if kind == "weaponactorhelpers":
        from generate_weapon_actor_helpers_assets import generate as generate_weapon_helpers
        return generate_weapon_helpers(stage)
    if kind == "grenadevfx":
        from generate_grenade_vfx_assets import generate as generate_grenade_vfx
        return generate_grenade_vfx(stage)
    if kind == "grenadewidget":
        from generate_grenade_widget_assets import generate as generate_grenade_widget
        return generate_grenade_widget(stage)
    if kind == "meleehitmontage":
        from generate_melee_hit_montage_assets import generate as generate_melee
        return generate_melee(stage)
    if kind == "dashselector":
        from generate_dash_selector_assets import generate as generate_dash_selector
        return generate_dash_selector(stage)
    if kind in ("characterinventory", "characteraudio", "characterquickbar", "characterloadout", "characteroutline", "characterteam", "characterstencil", "characterlifecycle", "characterparts", "characterhealth", "characterinput", "characterobserver", "characterlistener", "characterlegacy", "characterready", "characterwait", "characterpossessed", "charactervisibility", "characterbeginplay", "characterequipmenthide", "characterragdoll", "characterdeathstarted"):
        from generate_character_inventory_assets import generate as generate_character_inventory
        return generate_character_inventory(stage, audio=kind == "characteraudio", quickbar=kind == "characterquickbar", loadout=kind == "characterloadout", outline=kind == "characteroutline", team=kind == "characterteam", stencil=kind == "characterstencil", lifecycle=kind == "characterlifecycle", parts=kind == "characterparts", health=kind == "characterhealth", enhanced=kind == "characterinput", observer=kind == "characterobserver", listener=kind == "characterlistener", legacy=kind == "characterlegacy", ready=kind == "characterready", waiting=kind == "characterwait", possessed=kind == "characterpossessed", visibility=kind == "charactervisibility", beginning=kind == "characterbeginplay", hiding=kind == "characterequipmenthide", ragdoll=kind == "characterragdoll", dying=kind == "characterdeathstarted")
    if kind == "weaponinstance":
        from generate_weapon_instance_assets import generate as generate_weapon_instance
        return generate_weapon_instance(stage)
    if kind == "devicecolor":
        from generate_device_color_assets import generate as generate_device_color
        return generate_device_color(stage)
    if kind == "widgetheld":
        from generate_widget_held_assets import generate as generate_widget_held
        return generate_widget_held(stage)
    if kind == "widgetpressed":
        from generate_widget_pressed_assets import generate as generate_widget_pressed
        return generate_widget_pressed(stage)
    if kind == "autorespawnhelpers":
        from generate_auto_respawn_helper_assets import generate as generate_auto_respawn_helpers
        return generate_auto_respawn_helpers(stage)
    if kind == "autorespawnlisteners":
        from generate_auto_respawn_listener_assets import generate as generate_auto_respawn_listeners
        return generate_auto_respawn_listeners(stage)
    if kind == "autorespawnevents":
        from generate_auto_respawn_event_assets import generate as generate_auto_respawn_events
        return generate_auto_respawn_events(stage)
    if kind == "autorespawnactivation":
        from generate_auto_respawn_activation_assets import generate as generate_auto_respawn_activation
        default = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoRespawnDefaultProfile=")), "Python")
        if default not in ("Python", "BlueprintFallback"): raise RuntimeError("explicit AutoRespawn Profile required")
        return generate_auto_respawn_activation(stage, default)
    config = {
        "quickslot": ("/ShooterCore/Game/GA_QuickbarSlots", "quickslot_mixin", "LyraQuickslot", "Quickslot",
                      "Plugins/GameFeatures/ShooterCore/Content/Game/GA_QuickbarSlots.uasset", "K2_ActivateAbility"),
        "death": ("/Game/Characters/Heroes/Abilities/GA_Hero_Death", "death_mixin", "LyraDeath", "Death",
                  "Content/Characters/Heroes/Abilities/GA_Hero_Death.uasset", "K2_ActivateAbilityFromEvent"),
        "autoreload": ("/Game/Weapons/GA_Weapon_AutoReload", "autoreload_mixin", "LyraAutoReload", "AutoReload",
                       "Content/Weapons/GA_Weapon_AutoReload.uasset", "K2_ActivateAbility"),
        "heroheal": ("/Game/Characters/Heroes/Abilities/GA_Hero_Heal", "hero_heal_mixin", "LyraHeroHeal", "HeroHeal",
                     "Content/Characters/Heroes/Abilities/GA_Hero_Heal.uasset", "K2_ActivateAbility"),
        "dropweapon": ("/ShooterCore/Input/Abilities/GA_DropWeapon", "drop_weapon_mixin", "LyraDropWeapon", "DropWeapon",
                       "Plugins/GameFeatures/ShooterCore/Content/Input/Abilities/GA_DropWeapon.uasset", "K2_ActivateAbility"),
        "reloadmagazine": ("/Game/Weapons/GA_Weapon_ReloadMagazine", "reload_magazine_mixin", "LyraReloadMagazine", "ReloadMagazine",
                           "Content/Weapons/GA_Weapon_ReloadMagazine.uasset", "K2_ActivateAbility"),
        "spawneffect": ("/ShooterCore/Game/Respawn/GA_SpawnEffect", "spawn_effect_mixin", "LyraSpawnEffect", "SpawnEffect",
                        "Plugins/GameFeatures/ShooterCore/Content/Game/Respawn/GA_SpawnEffect.uasset", "K2_ActivateAbility"),
    }
    path, module, prefix, helper, relative, method = config[kind]
    original = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/relative
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, path+"."+path.rsplit("/", 1)[-1])
    # Loading an already-migrated parent may discover its runtime Mixin and
    # temporarily set FUNC_Native on inherited UFunctions. Compare/save only
    # restored Blueprint signatures, not that transient runtime dispatch flag.
    ue.unregister_all_mixins()
    before_defaults, signature = defaults(bp.GeneratedClass.get_cdo()), ue.describe_function(bp.GeneratedClass, method)
    original_class = bp.GeneratedClass.get_path_name()
    full_spawn_cdo = spawn_cdo_snapshot(bp, "before") if kind == "spawneffect" else None
    extra_signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in
        (("K2_OnEndAbility", "DisableInput", "EnableInputAgain") if kind == "spawneffect" else
        (("K2_CanActivateAbility", "ReloadAmmoIntoMagazine", "K2_OnEndAbility") if kind == "reloadmagazine" else
        (("CheckAmmoState", "PeriodicCheck") if kind == "autoreload" else (("K2_OnEndAbility",) if kind == "heroheal" else
            (("K2_OnEndAbility", "BroadcastToUI", "K2_OnAbilityAdded", "K2_OnAbilityRemoved") if kind == "ads" else ())))))}
    existing_end = None
    if kind in ("heroheal", "ads", "reloadmagazine", "spawneffect"):
        events = [node for graph in ue.blueprint_get_all_graphs(bp) for node in graph.Nodes
            if node.get_class().get_name() == "K2Node_Event" and str(node.EventReference.MemberName) == "K2_OnEndAbility"]
        if len(events) != 1: raise RuntimeError("one original HeroHeal native end event required")
        existing_end = events[0]
    ignored = {(existing_end.get_name(), "then")} if existing_end is not None else set()
    original_graphs = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    digests = {graph.get_name(): semantics(graph, names, ignored) for graph, names in original_graphs}
    guard, notify_name = "UEP"+helper+"TearingDown", "UEP"+helper+"NativeEnded"
    ue.blueprint_add_member_variable(bp, guard, EdGraphPinType(PinCategory="bool"))
    if existing_end is not None:
        make_gate(bp, notify_name, "bWasCancelled", existing_end.node_find_pin("bWasCancelled"))
    else:
        notify_graph = ue.blueprint_add_function(bp, notify_name)
        notify_graph.Nodes[0].node_create_pin(1, EdGraphPinType(PinCategory="bool"), "bWasCancelled")
    ue.compile_blueprint(bp)
    graph = bp.UbergraphPages[0]
    if existing_end is not None:
        insert_gate(graph, existing_end, "then", getattr(bp.GeneratedClass, notify_name), "bWasCancelled", "bWasCancelled")
        target = existing_end.node_find_pin("then").get_linked_to()[0]
        existing_end.node_find_pin("then").break_link_to(target)
        branch, get = graph.graph_add_node(K2Node_IfThenElse), graph.graph_add_node_variable_get(guard)
        connect(existing_end, "then", branch, "execute"); connect(get, guard, branch, "Condition")
        branch.node_find_pin("else").make_link_to(target)
    else:
        event = graph.graph_add_node_event(ue.find_class("GameplayAbility"), "K2_OnEndAbility")
        event.set_property("bOverrideFunction", True)
        branch, get = graph.graph_add_node(K2Node_IfThenElse), graph.graph_add_node_variable_get(guard)
        notify = graph.graph_add_node_call_function(getattr(bp.GeneratedClass, notify_name))
        connect(event, "then", branch, "execute"); connect(get, guard, branch, "Condition")
        connect(branch, "else", notify, "execute"); connect(event, "bWasCancelled", notify, "bWasCancelled")
    asset_name = "DA_"+helper+"AbilityMixin"; mixin_path = "/Game/UEPMixins/"+asset_name
    if ue.find_asset(mixin_path+"."+asset_name) is not None: raise RuntimeError("fresh retained hero ability authoring required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(asset_name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=value, PythonModule="uep_lyra_abilities."+module,
        PythonClass=prefix+value+"Profile") for value in ("Python", "BlueprintFallback")]
    ue.unregister_all_mixins(); ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp)
    if int(bp.Status) == 2 or defaults(bp.GeneratedClass.get_cdo()) != before_defaults or ue.describe_function(bp.GeneratedClass, method) != signature:
        raise RuntimeError("retained hero ability defaults/signature/compilation changed")
    if bp.GeneratedClass.get_path_name() != original_class: raise RuntimeError("retained hero ability class identity changed")
    if full_spawn_cdo is not None and spawn_cdo_snapshot(bp, "after") != full_spawn_cdo:
        raise RuntimeError("original full SpawnEffect CDO defaults changed")
    for name, description in extra_signatures.items():
        actual = ue.describe_function(bp.GeneratedClass, name)
        if actual != description:
            raise RuntimeError("retained public ability method signature changed: "+json.dumps(dict(name=name, before=description, after=actual)))
    for graph, names in original_graphs:
        if semantics(graph, names, ignored) != digests[graph.get_name()]: raise RuntimeError("original hero ability business graph changed")
    if ue.describe_function(bp.GeneratedClass, "K2_OnEndAbility")["owner"] != bp.GeneratedClass.get_path_name():
        raise RuntimeError("native EndAbility adapter not compiled on retained class")
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(original.read_bytes()).hexdigest() != original_hash: raise RuntimeError("official hero ability asset changed")
    return dict(schema_version=1, status="passed", kind=kind, runtime_acceptance=False, full_acceptance=False,
        original_class=bp.GeneratedClass.get_path_name(), original_defaults=before_defaults, original_signature=signature, extra_signatures=extra_signatures,
        full_spawn_cdo_preserved=full_spawn_cdo is not None,
        original_graphs=digests, native_end_adapter_nodes=4, original_class_defaults_signature_graphs_preserved=True,
        assets=[relative, "Content/UEPMixins/"+asset_name+".uasset"], reference_hashes={str(original): original_hash},
        dispatch_transport_endpoints=sorted(ignored), existing_native_end_business_preserved=existing_end is not None)


try:
    report = generate()
except Exception:
    report = dict(status="failed", error=traceback.format_exc()); ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["status"] != "passed": raise RuntimeError(report["error"])
ue.log("UEP_HERO_ABILITY_ASSETS_PASSED")
