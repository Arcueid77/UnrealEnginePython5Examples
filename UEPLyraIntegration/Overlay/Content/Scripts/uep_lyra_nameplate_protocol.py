"""Nameplate-specific network evidence; the old HUD lane is insufficient."""
import math
from uep_lyra_network_protocol import require


def validate_comparator_roots(value, final=False):
    for field in ("created", "released", "active", "pair_count"):
        require(type(value[field]) is int and value[field] >= 0, "invalid BP comparator root counter")
    require(value["mounts_for_native_construct"] is True and value["created"] > 0 and
            value["created"] == value["released"]+value["active"] and value["active"] == 2*value["pair_count"],
            "BP comparator root ownership mismatch")
    if final:
        require(value["active"] == 0, "BP comparator survived final cleanup")


def validate_nameplate(value, ack):
    player = ack["player"]
    require(value["controller"] == player["controller_path"] and value["pawn"] == player["pawn_path"] and
            value["world_token"] == player["world_token"], "nameplate crossed player/world")
    for flag in ("synthetic_messages", "native_state_written", "projection_parity_tested", "production_lifecycle_replayed"):
        require(value[flag] is False, "unsupported nameplate claim: " + flag)
    require(bool(value["production_local_manager"]) and value["manager_profile"] == "Python" and value["manager_same_class"] is True,
            "wrong production nameplate manager")
    rows = value["descriptors"]
    require(bool(rows) and len({row["pawn"] for row in rows}) == len(rows) and player["pawn_path"] in {row["pawn"] for row in rows},
            "missing/duplicate native Pawn descriptor")
    for row in rows:
        require(row["native_membership"] is True and row["native_source"] is True and row["python"] == row["blueprint"] and
                row["python"]["pawn"] == row["pawn"] and bool(row["python"]["scene"]), "native component descriptor differs")
    require(bool(value["widgets"]), "missing production nameplate Widget")
    require(value["bp_baseline_epoch_policy"] == "BP comparator Bind in production native Bind callback; no production replay or value copying" and
            type(value["native_bind_pairs"]) is int and value["native_bind_pairs"] > 0, "nameplate BP comparison epoch not declared")
    validate_comparator_roots(value["comparator_roots"])
    initialized = 0
    for row in value["widgets"]:
        require(row["profile"] == "Python" and row["class"] == "W_Nameplate_C" and row["same_class"] is True and
                row["automatic_native_binding"] is True and row["python"] == row["blueprint"] and
                row["pawn"] in {item["pawn"] for item in rows}, "nameplate production/BP UI differs")
        require(row["same_native_bind_comparator"] is True, "late-created BP comparator cannot prove native binding parity")
        require(type(row["python"]["progress"]) in (int, float) and math.isfinite(row["python"]["progress"]), "nonfinite nameplate health")
        native = row["native_health"]
        if native["available"] is True:
            require(native["maximum"] > 0 and native["unavailable_reason"] is None, "invalid initialized native health")
            if row["python"]["resource"] is not None:
                require(type(native["normalized"]) in (int, float) and math.isfinite(native["normalized"]) and
                        abs(native["normalized"]-row["python"]["progress"]) < .0001, "initialized native nameplate health differs")
                initialized += 1
        else:
            require(native["available"] is False and native["maximum"] == 0.0 and native["normalized"] is None and
                    native["unavailable_reason"] == "native-attribute-set-not-initialized", "unavailable health relabeled as native parity")
    require(initialized > 0, "no initialized native health comparison")
    require(type(value["map_removals_observed"]) is int and value["map_removals_observed"] >= 0 and
            type(value["world_epochs"]) is int and value["world_epochs"] > 0, "invalid nameplate lifetime evidence")


def validate_scopes(final, peer):
    placement = final["native_placement"]
    require(placement["native_asset_read"] is True and placement["asset_modified"] is False and
            placement["asset"] == "/ShooterCore/Experiences/LAS_ShooterGame_StandardComponents.LAS_ShooterGame_StandardComponents" and
            set(placement["rows"]) == {"source", "manager"}, "native nameplate placement evidence missing")
    for kind, name in (("source", "NameplateSource"), ("manager", "NameplateManagerComponent")):
        row = placement["rows"][kind]
        require(row["class"] == "/Game/UI/Indicators/"+name+"."+name+"_C" and row["client"] is True and
                row["server"] is False, "retained nameplate client-only placement differs")
    for kind in ("sources", "managers", "widgets"):
        state = final[kind]
        require(state["active_count"] == 0 and state["errors"] == [] and state["scopes_created"] == state["scopes_closed"],
                "nameplate scopes survived shutdown: " + kind)
        require(type(state["scopes_created"]) is int and state["scopes_created"] >= 0, "invalid nameplate scope counter")
        if kind != "widgets":
            require(type(state["helpers_rooted"]) is int and state["helpers_rooted"] >= 0 and
                    state["helpers_rooted"] == state["helpers_unrooted"], "nameplate helper root leak")
        require(state["scopes_created"] == 0 if peer == "server" else state["scopes_created"] > 0,
                "dedicated nameplate component or missing local observation")
    source = final["sources"]
    require((source["adds"] == source["removes"] == 0) if peer == "server" else
            (source["adds"] > 0 and source["removes"] > 0), "native nameplate Source lifecycle differs from placement")
    widget = final["widgets"]
    require(widget["team_proxies_created"] == widget["team_proxies_cancelled"] and
            widget["init_bound"] == widget["init_unbound"]+widget["init_owner_released"], "nameplate team/init delegate leak")


def validate_history(reports):
    for row in reports["server"]["phases"]:
        state = row["nameplate_server"]
        require(state["managers"]["active_count"] == 0 and state["widgets"]["active_count"] == 0 and
                all(state[kind]["errors"] == [] for kind in ("sources", "managers", "widgets")), "dedicated nameplate eligibility failed")
        for peer, ack in row["acks"].items():
            validate_nameplate(ack["nameplates"], ack)
            if row["phase"] == "respawn_a" and peer == "A":
                old = row["packet"]["statuses_before"][peer]["player"]["pawn_path"]
                retirement = row["packet"]["old_pawn_retirement"]
                require(retirement["old_pawn"] == row["packet"]["before"]["A"]["pawn_path"] and retirement["native_destroy_complete"] is True and
                        retirement["manual_lifecycle_event"] is False and retirement["death_ability_tested"] is False,
                        "old-Pawn destruction origin/lifetime not declared")
                require(any(value["old_pawn"] == old and value["all_sources_destroyed"] is True and
                            value["manual_lifecycle_event"] is False for value in ack["nameplates"]["fixture_source_retirements"]),
                        "client old-Pawn native Source retirement was not observed")
                require(old not in {item["pawn"] for item in ack["nameplates"]["descriptors"]} and
                        ack["nameplates"]["map_removals_observed"] > 0, "old respawn Pawn nameplate retained")
            if row["phase"].startswith("travel_"):
                previous = row["packet"]["statuses_before"][peer]["nameplates"]
                require(ack["nameplates"]["world_epochs"] > previous["world_epochs"], "nameplate manager did not change world")
    solo = next(row for row in reports["server"]["phases"] if row["phase"] == "fire_a_solo")
    exit_row = next(row for row in reports["server"]["phases"] if row["phase"] == "exit_b")
    departed_id = exit_row["acks"]["B0"]["player"]["player_id"]
    # UObject path suffixes are process-local. Find B's replica IN A before
    # departure, then compare it with A afterwards, never B's own local path.
    replicas = [item["pawn"] for item in exit_row["acks"]["A"]["nameplates"]["descriptors"] if item["player_id"] == departed_id]
    require(len(replicas) == 1, "departed Pawn replica identity missing in client A")
    departed = replicas[0]
    require(departed not in {item["pawn"] for item in solo["acks"]["A"]["nameplates"]["descriptors"]}, "departed client nameplate retained")
