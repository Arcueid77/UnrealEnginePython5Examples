"""Independent helper-only native lethal death/restart report gate."""
import argparse
import json
from pathlib import Path

PLAN = ("natural-death", "repeat-death", "profile-switch-during-death", "paused-world-time")
NETWORK_PLAN = PLAN[:3]
AUTHORITY_PHASES = ("native_authority_before", "native_authority_at_death", "native_authority_after")
FALSE_FLAGS = ("full_acceptance", "packaged_runtime", "physical_input_tested", "death_listener_timer_restart_business_migrated",
    "original_delay_written", "ability_granted_by_probe", "death_event_sent_by_probe", "helper_end_called_by_probe",
    "health_properties_written", "callback_replay")


def require(condition, message):
    if not condition: raise RuntimeError(message)


def spec_model(rows):
    # Native restart recreates equipment grants. Compare their class multiset,
    # while retaining the exact persistent AutoRespawn/Death handles separately.
    persistent = {"/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn_C",
        "/Game/Characters/Heroes/Abilities/GA_Hero_Death.GA_Hero_Death_C"}
    return dict(classes=sorted(path for handle, path in rows),
        persistent=sorted([handle, path] for handle, path in rows if path in persistent))


def validate_row(value, name, profile, *, authority=True, auto_active_required=True):
    for field in ("native_type_preserved",
        "native_death_active_observed", "native_death_ended", "delay_unchanged", "specs_unchanged"):
        require(value[field] is True, "AutoRespawn helper native lifecycle/restore missing: "+field)
    require(type(value["native_auto_respawn_active"]) is bool and
        value["native_auto_respawn_active"] is value["native_auto_respawn_still_active"] and
        (not auto_active_required or value["native_auto_respawn_active"]), "helper-only routing changed native active state")
    require(value["specs_before"] == value["specs_after"], "native persistent handles/class multiset changed")
    for field, dead in (("living_query", False), ("dead_query", True), ("after_query", False)):
        require(value[field]["owner_matches"] is True and value[field]["dead"] is dead, "AutoRespawn helper owner/death result differs")
    require(value["old_pawn"] != value["new_pawn"] and value["health_before"] > 0 and value["health_after_damage"] == 0 and
        value["respawn_health"] > 0 and value["original_delay"] == 5. and 5. <= value["native_elapsed"] < 14.,
        "original AutoRespawn damage/delay/native restart missing")
    require(value["native_net_policy"] == 0 and value["native_security_policy"] == 3 and
        value["native_owner_role"] == (3 if authority else 2), "AutoRespawn native policy/role changed")
    # This original BP branches on the ability's activation mode. Its inactive
    # owning-client instance retains the native default Authority mode, although
    # its Pawn is AutonomousProxy and no GameMode exists locally. Preserve that
    # original behavior; do not substitute an Actor-role authority check.
    for phase in AUTHORITY_PHASES:
        state = value.get(phase, {})
        require(state.get("ability_authority") is True and type(state.get("activation_mode")) is int and
            state["activation_mode"] == 0 and type(state.get("pawn_role")) is int and
            state["pawn_role"] == (3 if authority else 2) and state.get("game_mode_available") is authority,
            "native ability authority/activation mode/Pawn role/GameMode evidence differs: "+phase)
    switched = name == "profile-switch-during-death"
    require(value["profile_switched"] is switched and value["native_pause_observed"] is (name == "paused-world-time"),
        "native helper lifecycle intervention incomplete")
    stats = value["counters"]
    prefix = "" if profile == "Python" else "fallback_"
    require(stats[prefix+"player_state_queries"] >= 2 and stats[prefix+"death_queries"] >= 2, "routed public helper queries missing")
    final = "BlueprintFallback" if switched and profile == "Python" else "Python" if switched else profile
    require(stats["death_end_calls"] == int(final == "Python") and
        stats["fallback_death_end_calls"] == int(final == "BlueprintFallback") and
        stats["abilities_ended"] == int(final == "Python"),
        "original BP must traverse exactly the final Profile's native death end helper")


def validate_pair(blueprint, python):
    for field in AUTHORITY_PHASES+("native_auto_respawn_active", "native_auto_respawn_still_active"):
        require(blueprint[field] == python[field], "BP/Python native authority/lifetime differs: "+field)


def validate(report, plan=PLAN, *, network=False, event_business=False):
    require(report["status"] == "passed" and report["error"] is None and report["original_profile_restored"] and
        report["original_specs_restored"] and report["real_lethal_gas_damage"], "native AutoRespawn helper evidence incomplete")
    for field in FALSE_FLAGS:
        expected = event_business if field == "death_listener_timer_restart_business_migrated" else False
        require(report[field] is expected, "unsupported AutoRespawn helper claim: "+field)
    require(report["network_acceptance"] is network, "wrong native AutoRespawn lane")
    require([row["name"] for row in report["cases"]] == list(plan), "native AutoRespawn helper matrix incomplete")
    for row in report["cases"]:
        for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
            validate_row(row[key], row["name"], profile, authority=not network, auto_active_required=not network)
        validate_pair(row["blueprint"], row["python"])
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(plan),
        whole_auto_respawn_migrated=False, network_acceptance=network)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
