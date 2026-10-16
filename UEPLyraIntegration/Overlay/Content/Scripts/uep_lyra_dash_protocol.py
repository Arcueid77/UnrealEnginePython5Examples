"""Bounded Dash network contracts; synthetic local messages are not RPCs."""
import math
from uep_lyra_network_protocol import require


def validate_dash(value, ack):
    require(value["production_widget"] is True and value["class"] == "W_DashCooldown_C" and value["profile"] == "Python", "wrong production Dash")
    require(value["controller"] == ack["player"]["controller_path"] and value["pawn"] == ack["player"]["pawn_path"] and value["world_token"] == ack["player"]["world_token"], "Dash crossed owner/world")
    require(value["phase"] == ack["phase"] and value["completed"] is True, "Dash phase incomplete")
    require(value["synthetic_local_messages"] is True and value["native_dash_producer_tested"] is False and
            value["replicated_duration_message_tested"] is False and value["python_tick_called_by_probe"] is False and
            value["foreign_instigator_kind"] == "owning-controller-not-pawn", "misleading Dash source/lifetime claim")
    require(type(value["owner_deliveries"]) is int and type(value["foreign_rejections"]) is int and
            value["owner_deliveries"] == value["foreign_rejections"] == 1, "Dash delivery not exact-once")
    require(all(type(value[key]) is int and value[key] > 1 for key in ("automatic_tick_delta", "comparisons")) and
            type(value["visible_comparisons"]) is int and value["visible_comparisons"] > 0, "missing Dash automatic/charging comparisons")
    require(value["python"] == value["blueprint"] and set(value["python"]) == {"duration", "start", "charging", "visibility", "glow", "fill"}, "Dash BP/Python final differs")
    state = value["python"]
    require(state["duration"] == 1.25 and math.isfinite(state["start"]) and state["charging"] is False and
            state["fill"] == state["glow"] == 1.0 and state["visibility"] == 3, "Dash did not become ready")


def validate_scopes(final, peer):
    pool = final["pool_lifetime"]
    require(pool["source"] == "read-only-native-UIExtension-active-entry-membership" and
            pool["active_count"] == 0 and pool["ticker_active"] is False and
            pool["registered"] == pool["unregistered"] and pool["errors"] == [], "Dash pool lifetime sampler survived exit")
    require(all(type(final[key]) is int and final[key] >= 0 for key in ("active_count", "scopes_created", "scopes_closed", "health_binds", "health_unbinds")), "invalid Dash counters")
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and
            final["health_binds"] == final["health_unbinds"] and final["errors"] == [], "Dash scopes survived exit")
    require(final["scopes_created"] == final["health_binds"] == 0 if peer == "server" else
            final["scopes_created"] > 0 and final["health_binds"] > 0, "dedicated server Dash or missing client health scope")
