"""Scope-qualified multi-client respawn UI contracts."""
import math
from uep_lyra_network_protocol import require


def foreign_delivery_evidence(before, current, synchronous_pair):
    require(all(type(value) is int and value >= 0 for value in (before, current, synchronous_pair)), "invalid respawn foreign counters")
    require(synchronous_pair == 2 and current-before >= synchronous_pair, "respawn foreign pair missing or counter decreased")
    return {"foreign_rejections": synchronous_pair, "total_foreign_rejections": current-before,
            "additional_foreign_rejections": current-before-synchronous_pair}


def validate_respawn(value, ack):
    require(value["production_widget"] is True and value["class"] == "W_RespawnTimer_C" and value["profile"] == "Python", "wrong production respawn")
    require(value["controller"] == ack["player"]["controller_path"] and value["pawn"] == ack["player"]["pawn_path"] and value["world_token"] == ack["player"]["world_token"], "respawn crossed owner/world")
    require(value["phase"] == ack["phase"] and value["completed"] is True and value["synthetic_local_messages"] is True and
            value["native_respawn_producer_tested"] is False and value["replicated_message_tested"] is False and value["fixture_event_invoked"] is False, "misleading respawn phase/producer evidence")
    require(type(value["owner_deliveries"]) is int and value["owner_deliveries"] == 1 and
            type(value["foreign_rejections"]) is int and value["foreign_rejections"] == 2 and
            value["foreign_instigator_kind"] == "owning-pawn-not-playerstate" and
            type(value["comparisons"]) is int and value["comparisons"] > 1 and
            type(value["visible_comparisons"]) is int and value["visible_comparisons"] > 0, "respawn delivery/visible proof missing")
    if "total_foreign_rejections" in value:
        require(foreign_delivery_evidence(0, value["total_foreign_rejections"], value["foreign_rejections"]) ==
                {key: value[key] for key in ("foreign_rejections", "total_foreign_rejections", "additional_foreign_rejections")},
                "respawn synthetic/native foreign counts were conflated")
    actual, original = value["python"], value["blueprint"]
    for state in (actual, original):
        for key in ("duration", "start", "numeric", "glow", "fill"):
            require(type(state[key]) in (int, float) and math.isfinite(state[key]), "nonfinite respawn state: " + key)
    require(actual == original and actual["duration"] == 3.0 and actual["visibility"] == 1 and actual["numeric"] == 0.0 and
            actual["timer_active"] is False and actual["respawning"] is False, "respawn final state differs")


def validate_scopes(final, peer):
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and final["errors"] == [], "respawn scopes survived exit")
    require(final["scopes_created"] == 0 if peer == "server" else final["scopes_created"] > 0, "dedicated UI or missing respawn scope")
    pool = final["pool_lifetime"]
    require(pool["active_count"] == 0 and pool["ticker_active"] is False and pool["registered"] == pool["unregistered"] and pool["errors"] == [], "respawn pool watch survived exit")
