"""Independent actual native Clear/Give and latent-cancellation semantic gate."""
import argparse
import json
from pathlib import Path
from .auto_respawn_helpers_contract import require

PLAN = ("clear-live", "clear-pending-long", "clear-pending-short")
CLASS = "/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn_C"


def decode_ui_valid(result):
    # IsValid(FUIExtensionHandle&) returns (ReturnValue, Handle), not a bool.
    require(type(result) is tuple and len(result) == 2 and type(result[0]) is bool and result[1] is not None,
        "native UI IsValid return/reference shape differs")
    return result[0]


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["mode"] == "native-test-owned-end-clear-give" and
        report["full_auto_respawn_acceptance"] is False and report["native_clear_ability_called_by_fixture"] is True and
        report["native_end_ability_called_by_fixture"] is True and report["native_give_ability_called_by_fixture"] is True and
        report["test_owned_root_removed_before_exit"] is True and report["native_end_cancels_latent_actions"] is True,
        "native test-owned GAS lifecycle evidence incomplete")
    for field in ("replacement_handle_claimed_identical", "callback_replay", "health_properties_written", "ability_spec_properties_written", "inventory_properties_written"):
        require(report[field] is False, "unsupported lifecycle fixture claim: "+field)
    expected = [(name, profile) for name in PLAN for profile in ("BlueprintFallback", "Python")]
    require([(row["name"], row["profile"]) for row in report["cases"]] == expected, "native Clear/Give lifecycle matrix incomplete")
    held = report["fixture_roots"]
    require(held == dict(added=0, released=0, active=0), "GAS removal must not receive an externally rooted instance")
    previous_new = None
    for row in report["cases"]:
        for field in ("native_type_preserved", "ability_active_before", "proxy_active_before", "runtime_ended",
            "reflected_proxy_cleared", "health_listener_cleared", "no_new_pawn_before_fixture_recovery", "original_source_object_is_null",
            "replacement_handle_differs", "new_root_active", "new_root_ui_valid", "new_root_proxy_active",
            "old_instance_valid_at_deadline", "old_instance_inactive_at_deadline"):
            require(row[field] is True, "native lifecycle state missing: "+field)
        for field in ("native_active_after_end", "listening_after_end", "old_proxy_active_after_end"):
            require(row[field] is False, "native resource survived actual EndAbility: "+field)
        for key, expected_ui in (("ui_before", True), ("ui_after_end", False)):
            probe = row[key]
            require(probe["valid"] is expected_ui and probe["container"] == "tuple" and probe["arity"] == 2 and
                probe["return_type"] == "bool" and bool(probe["reference_type"]), "native UI return/reference evidence invalid: "+key)
        require(row["native_root_spec_count_after_end"] == row["native_root_spec_count_at_deadline"] == 1 and row["native_root_spec_count_after_clear"] == 0 and row["native_root_spec_count_after_give"] == 1 and
            row["old_handle"] > 0 and row["new_handle"] > 0 and row["old_handle"] != row["new_handle"], "native root grant/removal identity differs")
        if previous_new is not None: require(row["old_handle"] == previous_new, "native lifecycle root sequence not continuous")
        previous_new = row["new_handle"]
        expected_model = dict(classes=list(row["specs_before"]["classes"]), persistent=sorted(
            [row["new_handle"] if path == CLASS else handle, path] for handle, path in row["specs_before"]["persistent"]))
        require(row["specs_expected_after_native_regrant"] == row["specs_after"] == expected_model,
            "native Clear/Give class/persistent model changed beyond explicit new root handle")
        stats = row["after_clear_policy"]
        prefix = "" if row["profile"] == "Python" else "fallback_"
        require(stats[prefix+"removed"] == 0 and stats[prefix+"end_cleanups"] == 1 and
            stats["native_reset_cancelled"] == 1, "actual native End/removal did not cancel exactly its own reset listener")
        require(row["after_remove_policy"][prefix+"removed"] == 1 and row["after_remove_policy"][prefix+"end_cleanups"] == 0,
            "native inactive ClearAbility did not perform exactly one real removal")
        require(stats["cancelled_long_continuations"] == stats["cancelled_short_continuations"] == 0,
            "native EndAbility must remove latent callbacks rather than replay them into Python guards")
        require(row["observation_game_seconds"] >= .3 and
            (row["name"] != "clear-pending-long" or row["elapsed_game_seconds"] >= 5.5), "cancellation observed before native deadline")
        events = row["after_clear_events"]
        at_end = row["events_at_end"]
        long_done = at_end["long_continuations"]+at_end["fallback_long_continuations"]
        short_done = at_end["short_continuations"]+at_end["fallback_short_continuations"]
        require(long_done == int(row["name"] == "clear-pending-short") and short_done == 0,
            "native End did not occur within the declared latent window")
        require(all(events[key] == at_end[key] for key in ("long_continuations", "fallback_long_continuations", "short_continuations", "fallback_short_continuations")),
            "native delayed callback survived EndAbility through its original deadline")
        require(events["native_restarts"] == events["native_completion_rpcs"] == events["cosmetic_completion_messages"] == 0,
            "cleared old ability restarted or broadcast completion")
        new = row["new_root_policy"]
        require(new.get("added", 0)+new.get("fallback_added", 0) == 1 and
            new.get("activated", 0)+new.get("fallback_activated", 0) == 1,
            "native replacement grant did not naturally execute Added/OnSpawn")
        require(all(type(value) is bool for value in row["fixture_recovery"].values()), "fixture recovery must be explicit native actions")
    return dict(status="passed", bounded_native_clear_give_cancellation=True, pairs=3,
        pending_native_delays_cancelled=4, old_late_callbacks_observed=0, native_reset_producer_tested=False, full_auto_respawn_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
