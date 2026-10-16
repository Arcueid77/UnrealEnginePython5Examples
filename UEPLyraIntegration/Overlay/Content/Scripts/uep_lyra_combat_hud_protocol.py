"""Pure, fail-closed contracts for the opt-in combat HUD network pilot."""

import math

from uep_lyra_network_protocol import require, near


FIRE_PROFILES = {"fire_b": "BlueprintFallback", "fire_a_solo": "BlueprintFallback"}
CLICK_EVENT = "BndEvt__W_FireButton_ActionTouchButton_K2Node_ComponentBoundEvent_0_CommonButtonBaseClicked__DelegateSignature"


def values_agree(actual, expected):
    require(set(actual) == {"segments", "range"} and len(actual["range"]) == 4,
            "Incomplete reticle material values")
    require(all(type(value) in (int, float) and math.isfinite(value)
                for value in [actual["segments"]] + actual["range"]), "Invalid reticle material number")
    return (abs(actual["segments"] - expected["segments"]) < 1e-6
            and all(abs(left - right) < 1e-6 for left, right in zip(actual["range"], expected["range"])))


def validate_combat_ack(row, peer, ack):
    combat = ack.get("combat_hud")
    require(combat is not None, "Missing combat HUD checkpoint")
    reticle, button, weapon = combat["reticle"], combat["fire_button"], ack["weapon"]
    require(reticle["production_widget"] is False and reticle["origin"] == "test-owned-ammo-bar-overlay"
            and reticle["class"] == "W_Reticle_AmmoBar_C" and reticle["profile"] == "Python",
            "Reticle fixture must not claim production reachability")
    require(reticle["source_class"] in ("W_AmmoCounter_Pistol_C", "W_AmmoCounter_Rifle_C", "W_AmmoCounter_Shotgun_C")
            and bool(reticle["source_widget"]) and bool(reticle["weapon_instance"]),
            "Missing production native weapon context")
    require(reticle["controller"] == ack["player"]["controller_path"] and reticle["item"] == weapon["item"],
            "Reticle crossed native player/item ownership")
    expected = {"segments": float(weapon["maximum"] * 4 + 1),
                "range": [0.0, weapon["magazine"] / weapon["maximum"] * 0.25
                          if weapon["maximum"] else 0.0, 0.0, 1.0]}
    require(all(values_agree(reticle[name], expected) for name in ("python", "blueprint", "native")),
            "Reticle BP/Python/native material mismatch")
    health = combat["health_visuals"]
    require(health["controller"] == ack["player"]["controller_path"], "Health visuals crossed player ownership")
    require(near(health["current"], ack["player"]["health"])
            and near(health["target"], ack["player"]["health"])
            and near(health["updated"], ack["player"]["health"] / ack["player"]["max_health"]),
            "Health numeric/material presentation differs from native Health")
    require(button["class"] == "W_FireButton_C" and button["controller"] == ack["player"]["controller_path"],
            "FireButton crossed native player/class ownership")
    require(button["entry"] == CLICK_EVENT and button["physical_touch_tested"] is False
            and button["inventory_written"] is False, "FireButton entry/evidence boundary differs")
    before = row["packet"]["statuses_before"][peer]["combat_hud"]["fire_button"]["clicks"]
    after = button["clicks"]
    require(set(after) == {"Python", "BlueprintFallback"}
            and all(type(value) is int and value >= 0 for value in after.values()), "Invalid click counters")
    phase = row["phase"]
    firing = row["packet"]["target"] == peer and (phase.startswith("fire_") or phase == "empty_b")
    profile = FIRE_PROFILES.get(phase, "Python") if firing else None
    if firing:
        require(button["profile"] == profile and after[profile] > before[profile],
                "No selected BP/Python FireButton input")
    require(all(after[key] == before[key] for key in after if key != profile),
            "Unselected/other client FireButton injected input")
    if "debug_spread" in combat:
        validate_debug_spread(combat["debug_spread"], ack)


def validate_debug_spread(spread, ack):
    require(spread["class"] == "W_DebugWeaponSpreadWidget_C" and spread["profile"] == "Python",
            "Debug spread class/profile differs")
    require(spread["controller"] == ack["player"]["controller_path"] and spread["item"] == ack["weapon"]["item"]
            and bool(spread["weapon_instance"]), "Debug spread crossed owner/weapon")
    require(spread["python"] == spread["blueprint"] == spread["native"], "Debug BP/Python/native text differs")
    require(spread["python_ticks"] > 0 and spread["samples"] > 0 and math.isfinite(spread["native_angle"])
            and spread["native_angle"] >= 0 and spread["peak_angle"] >= spread["native_angle"], "Debug spread evidence missing")
    require(spread["production_widget"] is False and spread["origin"] == "test-owned-debug-spread-overlay"
            and spread["python_tick_called_by_probe"] is False and spread["spread_written"] is False,
            "Debug spread proof boundary differs")


def validate_production_reticle(reticle, ack):
    require(reticle['production_widget'] is True and reticle['profile'] == 'Python'
            and reticle['kind'] in ('Pistol', 'Rifle', 'Shotgun')
            and reticle['class'] == 'W_Reticle_' + reticle['kind'] + '_C', 'Not the production weapon reticle')
    require(reticle['controller'] == ack['player']['controller_path'] and reticle['item'] == ack['weapon']['item'],
            'Production reticle crossed native ownership')
    require(reticle['automatic_python_ticks'] > 0, 'Production reticle Python Tick bypassed')
    for name in ('python', 'blueprint', 'native'):
        values = reticle[name]
        require(set(values) == {'radius', 'width', 'height'} and all(math.isfinite(value) for value in values.values()),
                'Invalid production reticle geometry')
        require(all(abs(values[key] - reticle['native'][key]) < 0.05 for key in values), 'Production reticle geometry differs')


def validate_reticle_host(host, ack):
    require(host['production_widget'] is True and host['class'] == 'W_WeaponReticleHost_C'
            and host['profile'] == 'Python', 'Not the production Python reticle host')
    require(host['controller'] == ack['player']['controller_path'] and host['item'] == ack['weapon']['item']
            and bool(host['weapon_instance']), 'Reticle host crossed native player/item ownership')
    require(type(host['automatic_python_ticks']) is int and host['automatic_python_ticks'] > 0
            and host['python_tick_called_by_probe'] is False and host['weapon_event_called_by_probe'] is False,
            'Reticle host automatic native call evidence missing')
    kind = ack['combat_hud']['production_reticle']['kind']
    require(kind in ('Pistol', 'Rifle', 'Shotgun'), 'Unknown native reticle kind')
    expected = ['W_Reticle_' + kind + '_C', 'W_AmmoCounter_' + kind + '_C']
    children = host['children']
    require(host['native_config_classes'] == expected and [child['class'] for child in children] == expected
            and host['overlay_children'] == len(expected), 'Native reticle configuration or child cleanup differs')
    for child in children:
        require(child['item'] == host['item'] and child['weapon_instance'] == host['weapon_instance'],
                'Reticle host child crossed native ownership')
        require(child['horizontal'] == child['vertical'] == 0, 'Reticle host fill alignment differs')
    require(type(host['native_dead']) is bool and host['visibility'] == (1 if host['native_dead'] else 0),
            'Reticle host native death visibility differs')
