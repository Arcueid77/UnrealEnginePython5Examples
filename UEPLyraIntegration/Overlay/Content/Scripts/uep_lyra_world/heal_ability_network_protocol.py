"""Pure gates for equipment-granted, owner-predicted native GAS evidence."""
import copy
from .launcher_network_protocol import PEERS, near, require

SCENARIOS = ("original-montage", "native-cancel", "native-timer")
PLAN = tuple((peer, scenario, profile) for peer in PEERS for scenario in SCENARIOS
             for profile in ("BlueprintFallback", "Python"))
FALSE_CLAIMS = ("full_acceptance", "packaged_runtime", "physical_client_input_tested",
                "ability_activate_called_by_probe", "task_callbacks_called_by_probe",
                "health_properties_written", "inventory_properties_written", "animation_assets_modified",
                "net_policies_changed", "production_placement_tested", "travel_rejoin_tested")


def expected_after_inventory(packet):
    expected = copy.deepcopy(packet["prepared_inventory"])
    item = expected[packet["target"]]
    require(item["magazine"] == 1, "heal original item must have one native use before commit")
    item["magazine"] = 0
    return expected


def validate_counts(counts, expected):
    for field in ("activations", "heals", "tasks_created", "scopes_created", "scopes_closed",
                  "timers_created", "timers_cleared", "native_ends"):
        require(counts[field] == expected, "heal native policy/lifetime count differs: "+field)
    require(counts["cost_rejections"] == counts["commit_rejections"] == 0,
            "heal network activation unexpectedly refused cost/commit")


def validate_ack(packet, ack, peer, stage):
    require((ack["run_id"], ack["case_index"], ack["peer"], ack["stage"]) ==
            (packet["run_id"], packet["case_index"], peer, stage), "foreign heal network ACK")
    player = ack["player"]
    require(player["player_id"] == packet["roster"][peer]["player_id"] and
            player["pawn_path"] == packet["client_pawns"][peer] and
            player["world_token"] == packet["client_worlds"][peer], "heal ACK crossed owner/Pawn/world")
    expected_inventory = packet["original_inventory"][peer] if stage == "rollback" else expected_after_inventory(packet)[peer]
    require(ack["inventory"] == expected_inventory, "heal native replicated inventory/equipment differs")
    health = packet["original_health"][peer] if stage == "rollback" else 100.
    require(near(player["health"], health), "heal native replicated owner Health differs")
    visual = ack["health_visual"]
    require(near(visual["number"], health) and near(visual["target"], health) and
            near(visual["ratio"], health/player["max_health"]), "heal native owner HUD differs")
    if stage == "rollback":
        require(ack["ability_active"] is False, "heal ability survived inventory rollback")
        return
    require(stage == "observe" and ack["ability_active"] is False, "heal observation is not a native ended ability")
    target = peer == packet["target"]
    require(ack["native_asc_activation_requests"] == int(target), "heal activation crossed owner or replayed")
    require(ack["native_active_observed"] is target and ack["native_source_verified"] is target,
            "heal native activation/equipment source missing or crossed owner")
    require(ack["native_cancel_requested"] is (target and packet["scenario"] == "native-cancel"),
            "heal cancellation provenance differs")
    validate_counts(ack["python_counters"], int(target and packet["profile"] == "Python"))
    if target:
        require(ack["ability_class"] == packet["ability_class"] and ack["native_type_preserved"] is True and
                ack["instancing_policy"] == 1 and ack["net_execution_policy"] == 0,
                "heal owner class/instancing/LocalPredicted policy changed")
        require(ack["montage_was_playing"] is True, "native owning client did not play the original Montage task")
        if packet["scenario"] == "native-timer":
            require(ack["native_elapsed_seconds"] >= .99 and ack["montage_still_playing"] is True,
                    "heal timer shortened or bStopWhenAbilityEnds changed")
            if packet["profile"] == "Python":
                require(ack["python_counters"]["timer_callbacks"] == 1, "heal owner native timer did not fire")


def validate_cases(cases):
    require(len(cases) == len(PLAN), "heal two-owner matrix incomplete")
    for index, (row, identity) in enumerate(zip(cases, PLAN)):
        require((row["target"], row["scenario"], row["profile"]) == identity and row["case_index"] == index,
                "heal case identity/order differs")
        require(row["native_inventory_equipment_ability_grant"] is True and row["native_source_verified"] is True and
                row["server_native_active_observed"] is True and row["server_ability_active_after"] is False and
                row["native_type_preserved"] is True and row["instancing_policy"] == 1 and row["net_execution_policy"] == 0,
                "heal server native ability source/activation/end/type proof missing")
        require(row["prepared_health"][row["target"]] == 75. and all(near(v, 100.) for v in row["after_health"].values()),
                "heal server Health/owner isolation differs")
        require(row["after_inventory"] == expected_after_inventory(row), "heal native cost did not consume exactly one owner item use")
        require(row["original_inventory_restored"] is True, "heal server changed original inventory identity")
        validate_counts(row["server_python_counters"], int(row["profile"] == "Python"))
        for stage in ("observe", "rollback"):
            require(set(row["acks"][stage]) == set(PEERS), "heal native client ACK missing")
            for peer in PEERS:
                validate_ack(row, row["acks"][stage][peer], peer, stage)
        if row["profile"] == "Python":
            previous = cases[index-1]
            for key in ("prepared_health", "after_health", "prepared_inventory", "after_inventory", "original_inventory"):
                require(row[key] == previous[key], "heal BP/Python native parity differs: "+key)
    return True
