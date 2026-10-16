"""Bounded native held-widget evidence; UI pools are not widget destruction."""
import argparse
import json
from pathlib import Path

PLAN = ("release-held", "native-cancel", "external-native-end", "native-state-end",
        "active-profile-switch", "repeat-held", "paused-world-time")
NETWORK_PLAN = tuple(name for name in PLAN if name != "paused-world-time")
TDM = "/ShooterCore/Elimination/GA_ShowLeaderboard_TDM.GA_ShowLeaderboard_TDM_C"
CP = "/ShooterCore/ControlPoint/GA_ShowLeaderboard_CP.GA_ShowLeaderboard_CP_C"
CLASSES = dict(tdm=TDM, cp=CP)
WIDGETS = dict(tdm="/ShooterCore/Elimination/UI/W_MatchScoreBoard_Elimination.W_MatchScoreBoard_Elimination_C",
               cp="/ShooterCore/ControlPoint/UI/W_MatchScoreBoard_CP.W_MatchScoreBoard_CP_C")
FALSE_CLAIMS = ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested",
                "activation_handler_replayed", "task_callbacks_replayed", "ui_widget_created_by_probe",
                "widget_class_property_written", "animation_assets_modified", "localonly_authority_activation_claimed",
                "ui_widgets_destroyed_claimed", "cold_disk_io_claimed")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def validate(report, targets=None, plan=PLAN, safety=True):
    if targets is None: targets = tuple(report["targets"])
    require(targets and len(set(targets)) == len(targets) and all(value in CLASSES for value in targets) and
            report["targets"] == list(targets), "held-widget targets differ")
    require(report["status"] == "passed" and report["error"] is None, "held-widget did not pass")
    for field in FALSE_CLAIMS:
        require(report[field] is False, "unsupported held-widget claim: " + field)
    for field in ("original_player_restored", "original_profiles_restored", "original_ability_specs_restored",
                  "original_cdos_untouched", "native_layer_restored"):
        require(report[field] is True, "held-widget source/restoration proof missing: " + field)
    require([(row["target"], row["name"]) for row in report["cases"]] ==
            [(target, name) for target in targets for name in plan], "held-widget native matrix incomplete")
    for pair in report["cases"]:
        for side in ("blueprint", "python"):
            row = pair[side]
            for field in ("native_type_preserved", "profile_selected", "native_widget_activated", "native_widget_owner_correct",
                          "native_widget_in_original_layer", "native_widget_removed", "native_layer_restored",
                          "ability_ended", "no_late_callbacks", "player_restored"):
                require(row[field] is True, "held-widget native observation missing: " + field)
            require(row["native_widget_class"] == WIDGETS[pair["target"]] and row["original_soft_class_path"] == WIDGETS[pair["target"]],
                    "held-widget native soft target changed")
            require(row["native_tasks_during"] == 2 and row["native_tasks_after"] == 0 and row["input_injections"] >= 1,
                    "held-widget native input/task proof incomplete")
            require(row["activation_source"] == "existing-spec-enhanced-input",
                    "held-widget activation source differs")
            require(row["native_action_triggers_when_paused"] is False, "original scoreboard pause-input flag changed")
            scoring = ("Elimination/B_TeamDeathMatchScoring.B_TeamDeathMatchScoring_C" if pair["target"] == "tdm" else
                       "ControlPoint/B_ControlPointScoring.B_ControlPointScoring_C")
            require(row["native_scoring_component"] == "/ShooterCore/" + scoring and
                    ("L_Expanse" if pair["target"] == "tdm" else "L_Convolution_Blockout") in row["native_map"],
                    "held-widget UI tested in the wrong native scoring/Experience context")
            if pair["name"] == "native-state-end":
                require(row["native_state_end_removed_while_active"] is True, "native state end should remove UI, not end ability")
            if pair["name"] == "active-profile-switch":
                require(row["profile_teardown_ended_ability"] is True, "held-widget Profile teardown did not end")
            if pair["name"] == "paused-world-time":
                require(row["native_pause_observed"] and row["active_during_pause"] is False and
                        row["native_widget_removed_during_pause"] and row["paused_input_injections"] >= 2,
                        "native pause must invalidate original non-pause input and remove scoreboard while clock is frozen")
        counts = pair["python"]["counters"]
        require(counts["activations"] == counts["pushes_requested"] == counts["widgets_pushed"] == counts["widgets_removed"] == 1 and
                counts["tasks_created"] == counts["scopes_created"] == counts["scopes_closed"] == 2 and counts["fallback_activations"] == 0,
                "held-widget Python bypass/duplicate/lifetime leak")
        require(pair["blueprint"]["counters"]["fallback_activations"] == 1 and
                pair["blueprint"]["counters"]["activations"] == 0, "held-widget baseline was not original BP")
        if pair["name"] in ("release-held", "repeat-held", "native-state-end", "paused-world-time"):
            require(counts["input_released"] == 1, "held-widget native input release not observed")
    if safety:
        require([row["name"] for row in report["safety_regressions"]] ==
                ["cancel-pending", "repeat-pending", "profile-switch-pending"], "held-widget Python lifetime regressions incomplete")
        for row in report["safety_regressions"]:
            require(row["native_pending_observed"] and row["native_layer_restored"] and row["ability_ended"] and
                    row["no_late_callbacks"] and row["owned_scopes_balanced"], "held-widget pending regression incomplete")
            require(row["direct_native_asc_activation_fixture"] is True and row["bp_parity_claimed"] is False,
                    "held-widget pending safety source/parity claim differs")
            require(row["pending_references_cleared"] and row["pending_proxy_collected"], "held-widget canceled native proxy leaked")
    else:
        require(report["safety_regressions"] == [], "network did not run standalone pending regressions")
    stats = report["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [],
            "held-widget shutdown leak/error")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(targets) * len(plan),
                native_enhanced_input_targets=list(targets), fixture_granted_abilities=0,
                python_pending_regressions=len(report["safety_regressions"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
