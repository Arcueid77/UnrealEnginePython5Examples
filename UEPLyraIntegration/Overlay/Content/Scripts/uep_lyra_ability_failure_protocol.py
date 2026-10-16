"""Fail-closed multi-client failure UI contracts; local messages are not RPCs."""
from uep_lyra_network_protocol import require


def validate_failure(value, ack):
    require(value["production_widget"] is True and value["class"] == "W_AbilityFailureFeedback_C" and value["profile"] == "Python", "wrong production failure UI")
    require(value["controller"] == ack["player"]["controller_path"] and value["pawn"] == ack["player"]["pawn_path"] and value["world_token"] == ack["player"]["world_token"], "failure feedback crossed owner/world")
    require(value["phase"] == ack["phase"] and value["completed"] is True, "missing failure phase completion")
    require(value["synthetic_local_messages"] is True and value["native_ability_producer_tested"] is False and value["replicated_failure_message_tested"] is False and value["fixture_event_invoked"] is False and value["timer_clock"] == "native-retriggerable-delay", "misleading failure producer/timer evidence")
    require(value["foreign_controller_kind"] == "null-controller", "undeclared foreign controller fixture")
    require(all(type(value[key]) is int and value[key] > 0 for key in ("owner_deliveries", "foreign_rejections", "visible_comparisons")) and type(value["comparisons"]) is int and value["comparisons"] > 1, "missing delivery/visible comparisons")
    require(value["python"] == value["blueprint"] and value["python"]["visibility"] == 1 and isinstance(value["python"]["text"], str), "failure feedback did not finish in parity")
    require(value["expected_synthetic_reason"] == "UEP " + ack["peer"] + " " + ack["phase"], "wrong synthetic reason attribution")


def validate_scopes(final, peer):
    require(all(type(final[key]) is int and final[key] >= 0 for key in ("active_count", "scopes_created", "scopes_closed")), "invalid failure scope counters")
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and final["errors"] == [], "failure UI scope leak/error")
    require(final["scopes_created"] == 0 if peer == "server" else final["scopes_created"] > 0, "dedicated server UI or missing failure scope")
