"""Pure, fail-closed contracts for synthetic local network UI checkpoints."""

import math

from uep_lyra_network_protocol import require


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_progress(value, ack):
    require(value["production_widget"] is True and value["class"] == "W_AbilityProgress_C"
            and value["profile"] == "Python", "Wrong production ability progress")
    require(value["controller"] == ack["player"]["controller_path"]
            and value["pawn"] == ack["player"]["pawn_path"]
            and value["world_token"] == ack["player"]["world_token"], "Ability progress crossed ownership/world")
    require(value["phase"] == ack["phase"] and value["completed"] is True, "Missing duration completion for phase")
    require(value["synthetic_local_messages"] is True and value["native_interaction_producer_tested"] is False
            and value["replicated_duration_message_tested"] is False
            and value["python_tick_called_by_probe"] is False, "Misleading duration producer/Tick evidence")
    require(type(value["automatic_tick_delta"]) is int and value["automatic_tick_delta"] > 1,
            "No automatic duration UMG Tick")
    require(type(value["comparisons"]) is int and value["comparisons"] > 1
            and type(value["visible_comparisons"]) is int and value["visible_comparisons"] > 0,
            "No visible countdown BP/Python comparisons")
    for field in ("owner_deliveries", "foreign_rejections"):
        require(type(value[field]) is int and value[field] == 1, "Duration delivery missing or duplicated")
    require(value["foreign_instigator_kind"] == "owning-controller-not-pawn", "Undeclared duration foreign fixture")
    original, actual = value["blueprint"], value["python"]
    for key in ("duration", "start", "percent"):
        require(number(original[key]) and number(actual[key]), "Invalid duration numeric state")
    require(actual["duration"] == original["duration"] == 1.25 and actual["start"] == original["start"]
            and actual["start"] >= 0 and abs(actual["percent"] - original["percent"]) < 0.00001
            and actual["percent"] >= 1.0, "Duration BP/Python numeric mismatch")
    require(type(actual["visibility"]) is int and type(original["visibility"]) is int
            and actual["visibility"] == original["visibility"] == 1, "Duration not collapsed after completion")
    require(type(actual["text"]) is str and actual["text"] and actual["text"] == original["text"], "Duration text mismatch")
    require(actual["active_range"] == original["active_range"] == [0.0] * 4, "Duration material range mismatch")


def validate_scopes(final, peer):
    require(all(type(final[key]) is int and final[key] >= 0 for key in ("active_count", "scopes_created", "scopes_closed")),
            "Invalid duration scope counters")
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and final["errors"] == [],
            "Duration scope leak/error")
    require(final["scopes_created"] == 0 if peer == "server" else final["scopes_created"] > 0,
            "Dedicated server duration UI or missing client evidence")
