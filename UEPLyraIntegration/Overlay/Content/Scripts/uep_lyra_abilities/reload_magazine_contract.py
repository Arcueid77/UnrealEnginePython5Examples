"""Actual equipped-pistol reload differential; models are not engine proof."""
import argparse
import json
from pathlib import Path

PLAN = ("empty-magazine", "partial-limited-spare", "full-magazine-refused", "no-spare-refused", "native-cancel",
    "montage-interrupt", "external-native-end", "active-profile-switch", "repeat-partial", "paused-world-time")
REFUSED = {"full-magazine-refused": "Ability.ActivateFail.MagazineFull", "no-spare-refused": "Ability.ActivateFail.NoSpareAmmo"}
EARLY = ("native-cancel", "montage-interrupt", "external-native-end", "active-profile-switch")
NETWORK_PLAN = tuple(name for name in PLAN if name != "paused-world-time")
WEAPONS = {
    "pistol": ("/Game/Weapons/Pistol/GA_Weapon_Reload_Pistol.GA_Weapon_Reload_Pistol_C", None, "ID_Pistol"),
    "rifle": ("/ShooterCore/Weapons/Rifle/GA_Weapon_Reload_Rifle.GA_Weapon_Reload_Rifle_C", "/ShooterCore/Weapons/Rifle/ID_Rifle.ID_Rifle_C", "ID_Rifle"),
    "shotgun": ("/ShooterCore/Weapons/Shotgun/GA_Weapon_Reload_Shotgun.GA_Weapon_Reload_Shotgun_C", "/ShooterCore/Weapons/Shotgun/ID_Shotgun.ID_Shotgun_C", "ID_Shotgun"),
    "netshooter": ("/ShooterCore/Weapons/Shotgun/GA_Weapon_Reload_NetShooter.GA_Weapon_Reload_NetShooter_C", "/ShooterCore/Weapons/NetShooter_PROTO/ID_NetShooter.ID_NetShooter_C", "ID_NetShooter"),
}


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report, authority=True, plan=PLAN):
    weapon = report.get("weapon", "pistol")
    require(weapon in WEAPONS, "unknown native weapon-family reload")
    require(report.get("native_reload_class", WEAPONS[weapon][0]) == WEAPONS[weapon][0], "wrong native weapon-family reload class")
    if weapon != "pistol":
        require(report["equipped_fixture_state_restored"] and report["temporary_weapon_removed"] and
            report["native_weapon_fixture"]["weapon"] == weapon, "native temporary weapon fixture not restored")
    if weapon == "netshooter": require(report["native_equipped_autoreload_grant_count"] == 0, "prototype original absence of AutoReload changed")
    require(report["status"] == "passed" and report["error"] is None and report["original_player_restored"] and
        report["original_autoreload_active_restored"] and report["fixture_native_inventory_api_used"], "reload original player/AutoReload restore incomplete")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
        "task_callbacks_replayed", "reload_done_event_injected", "ammo_properties_written", "ability_activation_called_by_probe"):
        require(report[field] is False, "unsupported reload claim: "+field)
    require([row["name"] for row in report["cases"]] == list(plan), "reload differential matrix incomplete")
    for pair in report["cases"]:
        name = pair["name"]
        for side in ("blueprint", "python"):
            row = pair[side]
            require(row["native_type_preserved"] and row["native_equipment_item_source_matches"] and row["fixture_ammo_restored"] and
                row["native_class"] == WEAPONS[weapon][0] and
                row["input_injections"] == 1 and row["tasks_after_end"] == 0 and row["native_ability_inactive"] and
                row["no_late_callback"] and not row["no_firing_after_end"], "reload native input/source/end/restore differs")
            require(row["final_ammo"][0]+row["final_ammo"][2] == row["initial_ammo"][0]+row["initial_ammo"][2], "reload lost or created ammo")
            if name in REFUSED:
                require(not row["native_active_observed"] and row["native_failure_tags"] == [REFUSED[name]] and row["failure_messages"] == 1 and
                    row["initial_ammo"] == row["final_ammo"], "native GAS reload refusal/reason differs")
            else:
                require(row["native_active_observed"] and row["native_tasks_observed"] == 2 and row["original_montage_playing_observed"] and
                    row["expected_no_firing_observed"], "native reload activation/tasks/montage/NoFiring not observed")
                if name in EARLY:
                    require(row["initial_ammo"] == row["final_ammo"] and row["native_reload_done_events"] == 0, "early reload end transferred ammo")
                else:
                    require(row["native_reload_done_events"] == 1 and row["final_ammo"] == row["expected_ammo"], "original montage notify/native authority reload result missing")
                if name == "active-profile-switch": require(row["profile_teardown_ended_native_ability"], "reload Profile left native ability active")
                if name == "paused-world-time": require(row["native_pause_observed"], "native reload pause not observed")
        require(pair["blueprint"]["final_ammo"] == pair["python"]["final_ammo"] and
            pair["blueprint"]["native_failure_tags"] == pair["python"]["native_failure_tags"], "original/Python native reload result differs")
        stats = pair["python"]["counters"]
        require(stats["can_activate_checks"] >= 1, "native GAS did not reach Python reload CanActivate")
        if name in REFUSED:
            require(stats["activations"] == 0 and stats["magazine_full_refusals" if name == "full-magazine-refused" else "no_spare_refusals"] >= 1,
                "Python reload refusal decision was bypassed")
        else:
            require(stats["activations"] == stats["scopes_created"] == stats["scopes_closed"] == 1 and stats["tasks_created"] == 2,
                "Python native reload task scope was bypassed/leaked")
            require(stats["authority_reloads"] == int(authority and name not in EARLY), "wrong native authority reload count")
            require(stats["native_ends"] == int(name != "active-profile-switch") and
                stats["blocks_added"] == stats["blocks_removed"] == int(pair["python"]["initial_ammo"][0] == 0), "native reload End/owned tag cleanup was bypassed")
            original = pair["blueprint"]["counters"]
            require(original["fallback_activations"] == 1 and original["fallback_native_ends"] == int(name != "active-profile-switch"),
                "original BP native activation/End not observed")
    final = report["policy_shutdown"]
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and final["errors"] == [] and
        report["observer_scopes_created"] == report["observer_scopes_closed"], "reload policy/source observer leak")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(plan), original_native_montage_notify=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
