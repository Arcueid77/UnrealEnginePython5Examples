"""Native inventory/quickbar evidence, including routed named-output query."""
import math
from uep_lyra_network_protocol import require


def validate_quickbar(value, ack):
    require(value["controller"] == ack["player"]["controller_path"] and value["pawn"] == ack["player"]["pawn_path"] and
            value["world_token"] == ack["player"]["world_token"], "quickbar crossed owner/world")
    for flag in ("synthetic_local_messages", "native_inventory_properties_written", "bp_initialization_parity_tested"):
        require(value[flag] is False, "unsupported quickbar claim: "+flag)
    require(value["external_named_query_migrated"] is True and
            sum(row["named_query_calls"] for row in value["slots"]) > 0, "missing Python named query evidence")
    require(len(value["slots"]) == 3 and [row["python"]["index"] for row in value["slots"]] == [0, 1, 2], "quickbar slot inventory differs")
    require(len({row["widget"] for row in value["slots"]}) == 3, "duplicated quickbar slot evidence")
    require(value["baseline_epoch_policy"] == "same-production-widget -> same BP baseline; native owner/remount/resume; no state copying" and
            type(value["reused_baseline_epochs"]) is int and value["reused_baseline_epochs"] >= 0, "quickbar baseline epoch policy missing")
    for row in value["slots"]:
        require(row["production_widget"] is True and row["class"] == "W_QuickBarSlot_C" and row["profile"] == "Python", "wrong production quickbar")
        require(row["python"] == row["blueprint"] and math.isfinite(row["python"]["numeric"]), "quickbar BP/Python differs")
        require(type(row["automatic_ticks"]) is int and row["automatic_ticks"] > 0, "no native quickbar Tick")
        if row["native_item"] is None:
            require(row["python"]["empty"] is True, "native empty quickbar differs")
        else:
            require(row["python"]["empty"] is False and row["python"]["numeric"] == row["native_total"] and
                    row["python"]["selected"] is row["native_active"], "native quickbar inventory presentation differs")


def validate_scopes(final, peer):
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and final["errors"] == [], "quickbar scopes survived exit")
    require(final["scopes_created"] == 0 if peer == "server" else final["scopes_created"] >= 3, "dedicated UI or missing quickbar slots")
    pool = final["pool_lifetime"]
    require(pool["active_count"] == 0 and pool["ticker_active"] is False and pool["registered"] == pool["unregistered"] and pool["errors"] == [], "quickbar pool watch survived exit")
