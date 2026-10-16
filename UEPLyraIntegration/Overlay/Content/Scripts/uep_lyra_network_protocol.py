"""Pure, fail-closed contracts for the two-client test harness (no UE imports)."""

import math


PHASES = (
    "join_a", "join_b", "authority", "damage_a", "heal_a", "damage_b",
    "heal_b", "damage_both", "heal_both", "respawn_a", "respawn_b",
    "travel_one", "travel_two", "exit_b", "damage_a_solo", "heal_a_solo",
    "rejoin_b", "damage_b1", "heal_b1", "complete",
)


def participants(phase):
    if phase in ("join_a", "damage_a_solo", "heal_a_solo"):
        return ["A"]
    if PHASES.index(phase) >= PHASES.index("rejoin_b"):
        return ["A", "B1"]
    return ["A", "B0"]


def deltas(phase):
    return {
        "damage_a": {"A": -10}, "heal_a": {"A": 10},
        "damage_b": {"B0": -20}, "heal_b": {"B0": 20},
        "damage_both": {"A": -10, "B0": -20},
        "heal_both": {"A": 10, "B0": 20},
        "damage_a_solo": {"A": -10}, "heal_a_solo": {"A": 10},
        "damage_b1": {"B1": -20}, "heal_b1": {"B1": 20},
    }.get(phase, {})


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def near(actual, expected):
    return (type(actual) in (int, float) and math.isfinite(actual)
            and abs(actual - expected) <= 0.05)


def validate_hud(hud, player=None):
    require(hud.get("errors") == [], "HUD presenter errors")
    count = 1 if player is not None else 0
    for key in ("active_widget_count", "live_widget_reference_count"):
        require(type(hud.get(key)) is int and hud[key] == count, "HUD ownership count: " + key)
    require(len(hud.get("active_widgets", [])) == count, "HUD active ledger mismatch")
    for prefix in ("controller", "health"):
        bound, unbound = hud.get(prefix + "_bind_count"), hud.get(prefix + "_unbind_count")
        require(type(bound) is int and type(unbound) is int and bound >= unbound >= 0
                and bound - unbound == count, "HUD callback imbalance")
    if player is None:
        require(hud.get("construct_count") == 0 and not hud.get("health_events"), "Server created HUD")
        return
    entry = hud["instances"][hud["active_widgets"][0]]
    for field, player_field in (("last_controller", "controller_path"), ("last_pawn", "pawn_path"),
                                ("last_health_component", "health_component_path")):
        require(entry.get(field) == player[player_field], "HUD bound to wrong player: " + field)
    require(near(entry.get("last_health"), player["health"]), "HUD value differs from local Health")


def validate_ack(packet, ack, peer):
    for key in ("run_id", "phase_index", "phase", "server_world_token"):
        require(ack.get(key) == packet[key], "stale/mismatched ACK: " + key)
    require(peer in packet["participants"] and ack.get("peer") == peer, "Wrong ACK participant")
    target = packet["roster"][peer]
    require(ack.get("server_player_token") == target["player_token"], "Wrong server player token")
    player = ack["player"]
    require(player["world_token"] == packet["client_worlds"][peer], "Stale client World")
    require(player["player_id"] == target["player_id"] and player["player_name"] == target["player_name"],
            "ACK player identity mismatch")
    require(player["net_mode"] == "Client" and player["pawn_local_role"] == "AutonomousProxy",
            "ACK is not a real client player")
    require(player["local_player_controller_count"] == 1, "Client local player count mismatch")
    require(near(player["health"], packet["expected_health"][peer]), "ACK Health mismatch")
    require(ack.get("command_ids") == packet["command_ids"], "Wrong ACK command IDs")
    validate_hud(ack["hud"], player)
    if peer in packet["changed_health"]:
        require(any(e.get("event") == "health_changed" and e.get("sequence", 0) > packet["event_floor"][peer]
                    and e.get("pawn") == player["pawn_path"]
                    and e.get("health_component") == player["health_component_path"]
                    and near(e.get("health"), packet["expected_health"][peer])
                    for e in ack["hud"]["health_events"]), "Missing fresh replicated Health event")


def validate_command(result, status, applied):
    require(result.get("status") == status and result.get("applied") is applied
            and result.get("accepted") is applied, "Unexpected command outcome: " + str(result))


def validate_phase_names(records, peer):
    expected = [name for name in PHASES if peer == "server" or peer in participants(name)]
    if peer == "B0":
        expected = expected[:expected.index("exit_b") + 1]
    require([row["phase"] for row in records] == expected, "Missing/reordered phase evidence for " + peer)


def validate_run(reports, run_id):
    require(set(reports) == {'server', 'A', 'B0', 'B1'}, 'Missing network process report')
    for peer, report in reports.items():
        require(report.get('run_id') == run_id and report.get('peer') == peer, 'Wrong report identity')
        require(report.get('status') == 'passed' and report.get('schema_version') == 5
                and report.get('network_schema_version') == 1, 'Missing final network report')
        require(report.get('shutdown', {}).get('status') == 'passed', 'Missing network shutdown')
        require(report.get('python_version', '').startswith('3.11.'), 'Wrong network Python')
        validate_phase_names(report['phases'], peer)
    server = reports['server']
    rows = {row['phase']: row for row in server['phases']}
    for index, phase in enumerate(PHASES):
        row = rows[phase]
        packet = row['packet']
        require(len(row.get('bot_isolation', [])) == 3
                and all(b['running'] is False for b in row['bot_isolation']), 'Bot combat not isolated')
        require(packet['run_id'] == run_id and packet['phase_index'] == index
                and packet['phase'] == phase and packet['participants'] == participants(phase),
                'Wrong phase definition')
        require(set(row['acks']) == set(participants(phase)), 'Missing participant ACK')
        for peer in participants(phase):
            validate_ack(packet, row['acks'][peer], peer)
            local = next(r for r in reports[peer]['phases'] if r['phase'] == phase)
            require(local['ack'] == row['acks'][peer], 'Server/client ACK evidence differs')
        for peer, delta in deltas(phase).items():
            target = packet['roster'][peer]
            applied = [c for c in row['commands'] if c.get('status') == 'Applied'
                       and c.get('target_actor') == target['pawn_path']]
            require(len(applied) == 1 and near(applied[0]['requested_health_delta'], delta),
                    'Missing explicit-target damage/heal')
            require(any(c.get('status') == 'RejectedDuplicateCommand'
                        and c['command_id'] == applied[0]['command_id']
                        and c['applied'] is False for c in row['commands']), 'Missing command idempotency')
        if phase != 'exit_b':
            require(len(row['server_after']) == len(participants(phase)), 'Wrong server player count')
            for peer in participants(phase):
                target = packet['roster'][peer]
                observed = [r for r in row['server_after'] if r['player_token'] == target['player_token']]
                require(len(observed) == 1 and near(observed[0]['health'], packet['expected_health'][peer]),
                        'Server/client Health mismatch')
    authority = rows['authority']
    require(any(c['status'] == 'RejectedAmbiguousTarget' for c in authority['commands']), 'Legacy ambiguity unchecked')
    for peer in ('A', 'B0'):
        validate_command(authority['acks'][peer]['authority_rejection'], 'RejectedNotAuthority', False)
    for phase in ('authority', 'travel_one', 'travel_two', 'exit_b', 'rejoin_b'):
        require(rows[phase]['restart_rejections'] and all(r['accepted'] is False
                for r in rows[phase]['restart_rejections']), 'Missing stale restart rejection')
    for phase, first, second in (('damage_both', 'B0', 'A'), ('heal_both', 'A', 'B0')):
        acks = rows[phase]['acks']
        require(acks[first]['observed_at_ns'] < acks[second]['observed_at_ns'], 'ACK order test missing')
    joined_a = rows['join_a']['acks']['A']['player']
    joined_b_a = rows['join_b']['acks']['A']['player']
    require(joined_a['pawn_path'] == joined_b_a['pawn_path'], 'Second join replaced player A')
    for phase, target in (('respawn_a', 'A'), ('respawn_b', 'B0')):
        row = rows[phase]
        for peer in ('A', 'B0'):
            old = row['statuses_before'][peer]['player']['pawn_path']
            new = row['acks'][peer]['player']['pawn_path']
            require((old != new) == (peer == target), 'Respawn player isolation failed')
    for phase in ('travel_one', 'travel_two'):
        row = rows[phase]
        for peer in ('A', 'B0'):
            old = row['statuses_before'][peer]
            ack = row['acks'][peer]
            require(old['player']['world_token'] != ack['player']['world_token'], 'Client did not travel')
            require(ack['hud']['construct_count'] > old['hud']['construct_count']
                    and ack['hud']['destruct_count'] > old['hud']['destruct_count'], 'HUD did not reconstruct')
    old_b = rows['exit_b']['packet']['roster']['B0']
    new_b = rows['rejoin_b']['packet']['roster']['B1']
    require(old_b['player_token'] != new_b['player_token'], 'Rejoin reused old connection token')
    require(len(rows['exit_b']['server_after']) == 1, 'B0 stayed connected')
    return {'status': 'passed', 'required_client_count': 2, 'process_instances': 4,
            'scenario_ids': ['N%02d' % i for i in range(1, 17)]}
