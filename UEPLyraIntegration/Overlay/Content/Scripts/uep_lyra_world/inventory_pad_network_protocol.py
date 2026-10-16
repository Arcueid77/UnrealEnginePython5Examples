"""Pure gates for server collision, owning-client inventory/equipment/fire."""
PEERS = ("A", "B0")
CLASSES = ("B_GrantInventory_Pad_C", "B_GrantInventoryPad_WithMesh_C")
PLAN = tuple((cls, kind, target, profile) for cls in CLASSES for kind in ("pickup", "full")
             for target in PEERS for profile in ("BlueprintFallback", "Python"))


def require(value, message):
    if not value:
        raise RuntimeError(message)


def baseline_ready(statuses, baseline):
    # Atomic status publication can be temporarily unreadable on Windows.
    # No previous/fabricated state is substituted for that missing sample.
    return set(statuses) == set(PEERS) and all(isinstance(statuses[peer], dict) and
        statuses[peer].get("inventory") is not None and statuses[peer]["inventory"] == baseline[peer] for peer in PEERS)


def validate_ack(packet, ack, peer):
    require(peer in PEERS and ack["peer"] == peer and ack["run_id"] == packet["run_id"] and
            ack["case_index"] == packet["case_index"], "wrong inventory ACK identity")
    player = ack["player"]
    require(player["player_id"] == packet["roster"][peer]["player_id"] and
            player["pawn_path"] == packet["client_pawns"][peer] and
            player["world_token"] == packet["client_worlds"][peer], "inventory ACK crossed player/Pawn/world")
    expected = dict(packet["expected"][peer])
    if packet["kind"] == "pickup" and peer == packet["target"]:
        expected["magazine"] -= 1
        require(type(ack["input_frames"]) is int and ack["input_frames"] > 0, "owning client did not drive native fire input")
    else:
        require(ack["input_frames"] == 0, "wrong inventory client drove fire")
    require(ack["inventory"] == expected, "replicated inventory/equipment/fire differs")


def validate_cases(cases):
    require(len(cases) == len(PLAN), "inventory network matrix incomplete")
    for index, (row, identity) in enumerate(zip(cases, PLAN)):
        require(row["case_index"] == index and (row["class"], row["kind"], row["target"], row["profile"]) == identity,
                "inventory case order differs")
        require(row["physical_events"] == ["begin", "end"] and row["pad_destroyed"] is True and
                row["fixture_scope_closed"] is True, "inventory native collision/fixture lifetime missing")
        for peer in PEERS:
            validate_ack(row, row["acks"][peer], peer)
            require(row["after"][peer] == row["acks"][peer]["inventory"], "server/owner replicated state differs")
            rollback = row["rollbacks"][peer]
            require(rollback["inventory"] == row["baseline"][peer] and rollback["case_index"] == index and
                    rollback["run_id"] == row["run_id"] and rollback["peer"] == peer, "inventory rollback did not replicate")
        other = next(peer for peer in PEERS if peer != row["target"])
        require(row["after"][other] == row["baseline"][other], "inventory changed non-target owner")
        target = row["target"]
        if row["kind"] == "pickup":
            require(len(row["after"][target]["items"]) == len(row["baseline"][target]["items"])+1 and
                    row["expected"][target]["magazine"]-row["after"][target]["magazine"] == 1,
                    "authority grant/fire outcome missing")
        else:
            require(row["after"][target] == row["expected"][target], "full inventory changed")
        if row["profile"] == "Python":
            require(row["python_grants"] == (1 if row["kind"] == "pickup" else 0) and
                    row["python_full_rejections"] == (1 if row["kind"] == "full" else 0), "Python pad path bypassed/replayed")
            original = cases[index-1]
            require(row["after"] == original["after"] and row["expected"] == original["expected"], "network BP/Python outcome differs")


def validate_reports(reports):
    run_id = reports["server"]["run_id"]
    for peer in ("server",)+PEERS:
        row = reports[peer]
        require(row["run_id"] == run_id and row["peer"] == peer and row["status"] == "passed" and row["error"] is None,
                "inventory peer did not pass")
        require(row["shutdown"]["status"] == "passed" and row["shutdown"]["hud"]["active_widget_count"] == 0 and
                row["shutdown"]["weapon_observer"]["active_scopes"] == 0 and not row["shutdown"]["weapon_observer"]["ticker_active"],
                "inventory HUD/observer shutdown leak")
        require(len(row["cases"]) == len(PLAN) and row["fixture_scope_closed"] is True, "inventory cases/scopes missing")
        require(row["inventory_policy"]["errors"] == [] and row["client_aim_restored"] is True, "inventory policy/aim cleanup failed")
        if peer == "server":
            require(row["native_players_restored"] == {key: True for key in PEERS}, "native server player restore missing")
        for flag in ("full_acceptance", "packaged_runtime", "remote_audio_tested", "client_pad_profile_parity_tested",
                     "overlap_handler_called_by_probe", "ammo_properties_written", "inventory_properties_written",
                     "pad_replication_forced", "physical_client_input_tested", "travel_rejoin_tested"):
            require(row[flag] is False, "unsupported inventory network claim: "+flag)
    validate_cases(reports["server"]["cases"])
    for peer in PEERS:
        for packet, ack in zip(reports["server"]["cases"], reports[peer]["cases"]):
            validate_ack(packet, ack, peer)
    return {"status": "passed", "cases": len(PLAN), "clients": 2, "run_id": run_id,
            "native_inventory_equipment_fire_replication": True, "full_acceptance": False}
