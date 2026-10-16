"""Opt-in real Lyra two-client scenario; filesystem messages only orchestrate tests."""

import copy
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue

from uep_lyra_probe import LyraRuntimeProbe, _command_line_value, _field, _is_valid
from uep_lyra_hud import state as hud_state
from uep_lyra_hud.shutdown_validation import defer_until_shutdown
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_network_protocol import (
    PHASES, participants, deltas, require, near, validate_hud, validate_ack,
    validate_command, validate_phase_names,
)


class NetworkProbe(LyraRuntimeProbe):
    def __init__(self):
        super().__init__()
        self.peer = _command_line_value('-UEPLyraNetPeer=')
        self.run_id = _command_line_value('-UEPLyraNetRun=')
        self.root = Path(_command_line_value('-UEPLyraNetDirectory='))
        require(self.peer in ('server', 'A', 'B0', 'B1') and self.run_id, 'Invalid network identity')
        self.result_path = str(self.root / (self.peer + '.json'))
        self.mode = 'server' if self.peer == 'server' else 'client'
        self.timeout_seconds = 900
        self.rows = []
        self.player = None
        self.history = []
        self.index = 0
        self.packet = None
        self.preparation = None
        self.last_phase = -1
        self.last_publish = -1.0
        self.next_tick = 0.0
        self.phase_started = time.monotonic()
        self.phase_commands = []
        self.server_ready = False
        self.restart_rejections = []
        self.bot_isolation = []
        self.peer_frame_snapshots = {}
        self.gameplay_statics = ue.find_class('GameplayStatics').get_cdo()
        self.bot_class = ue.find_class('LyraPlayerBotController')

    def _isolate_bot_combat(self):
        # Test-only: retain bots for native Warmup, stop their autonomous combat.
        # Never alter human Pawn Health, immunity, GAS or replication settings.
        self.bot_isolation = isolate_bots(self.gameplay_statics, self.world, self.bot_class)

    def _snapshot_report(self, snapshot):
        result = super()._snapshot_report(snapshot)
        for key, field in (
            ('world_token', 'WorldToken'), ('player_token', 'PlayerToken'),
            ('player_name', 'PlayerName'), ('controller_path', 'ControllerPath'),
            ('pawn_path', 'PawnPath'), ('health_component_path', 'HealthComponentPath'),
        ):
            result[key] = str(_field(snapshot, field, ''))
        result['player_id'] = int(_field(snapshot, 'PlayerId', -1))
        return result

    def _player_ready(self, row):
        return (row['game_thread'] and row['game_world'] and row['experience_loaded']
                and 'B_ShooterGame_Elimination' in (row['experience'] or '')
                and row['player_pawn'] and row['player_state_ready'] and row['ability_system_ready']
                and row['health_ready'] and not row['damage_immune']
                and row['health'] > 0 and row['player_id'] >= 0 and bool(row['player_token'])
                and any(f['name'] == 'ShooterCore' and f['active'] for f in row['game_features']))

    def _status(self):
        hud = hud_state.snapshot()
        ready = self.player is not None and self._player_ready(self.player)
        if ready:
            try:
                validate_hud(hud, self.player)
            except RuntimeError:
                ready = False
        return {'run_id': self.run_id, 'peer': self.peer, 'phase_index': self.last_phase,
                'player': self.player, 'players': self.rows, 'hud': hud,
                'bridge_generation': self.bridge_generation,
                'bot_isolation': copy.deepcopy(self.bot_isolation),
                'ready': ready}

    def _peer_status(self, peer):
        if peer in self.peer_frame_snapshots:
            return self.peer_frame_snapshots[peer]
        status = read_json(self.root / 'status' / (peer + '.json'))
        if status is not None:
            require(status['run_id'] == self.run_id and status['peer'] == peer, 'Wrong status identity')
        self.peer_frame_snapshots[peer] = status
        return status

    def _roster(self, peers):
        if len(self.bot_isolation) != 3 or any(b['running'] for b in self.bot_isolation):
            return None
        if len(self.rows) != len(peers):
            return None
        roster = {}
        for peer in peers:
            status = self._peer_status(peer)
            if not status or not status['ready']:
                return None
            local = status['player']
            # Online identity can replace URL ?Name=. Correlate the replicated
            # PlayerState identity with the actual server controller, never order.
            matches = [r for r in self.rows if r['player_id'] == local['player_id']
                       and r['player_name'] == local['player_name']]
            if len(matches) != 1 or not self._player_ready(matches[0]):
                return None
            row = matches[0]
            require(row['net_mode'] == 'DedicatedServer' and row['pawn_local_role'] == 'Authority'
                    and row['remote_player_controller_count'] == len(peers), 'Server role/count mismatch')
            validate_hud(status['hud'], local)
            roster[peer] = row
        require(len({p['player_id'] for p in roster.values()}) == len(peers), 'Duplicate player identity')
        return roster

    def _command(self, command_id, delta, token, expected='Applied'):
        result = self._command_result_report(self.bridge.call_function(
            'ApplyAuthorityHealthDeltaToPlayer', command_id, float(delta), token))
        validate_command(result, expected, expected == 'Applied')
        self.phase_commands.append(result)
        return result

    def _start_phase(self, phase, peers, roster):
        statuses = {p: self._peer_status(p) for p in peers}
        before = copy.deepcopy(roster)
        self.phase_commands = []
        self.restart_rejections = []
        prep = {'before': before, 'statuses_before': statuses,
                'world_before': before[peers[0]]['world_token']}
        self.preparation = prep
        if phase.startswith('travel_'):
            require(self.world.server_travel('/ShooterMaps/Maps/L_Expanse?NumBots=3'), 'ServerTravel rejected')
            return False
        if phase.startswith('respawn_'):
            target = 'A' if phase == 'respawn_a' else 'B0'
            require(self.bridge.call_function('RequestPlayerRestart', roster[target]['player_token']),
                    'Explicit player restart rejected')
            return False
        return True

    def _prepared(self, phase, peers, roster):
        before = self.preparation['before']
        if phase.startswith('travel_'):
            if roster[peers[0]]['world_token'] == self.preparation['world_before']:
                return False
            for peer in peers:
                old = self.preparation['statuses_before'][peer]
                current = self._peer_status(peer)
                if current['player']['world_token'] == old['player']['world_token']:
                    return False
                require(current['hud']['construct_count'] > old['hud']['construct_count']
                        and current['hud']['destruct_count'] > old['hud']['destruct_count'],
                        'Travel did not replace the HUD')
            for peer in peers:
                self._reject_stale(self._id(peer, 'oldworld'), before[peer]['player_token'])
            return True
        if phase.startswith('respawn_'):
            target = 'A' if phase == 'respawn_a' else 'B0'
            if roster[target]['pawn_path'] == before[target]['pawn_path']:
                return False
            current = self._peer_status(target)
            old = self.preparation['statuses_before'][target]
            if current['player']['pawn_path'] == old['player']['pawn_path']:
                return False
            require(current['hud']['health_bind_count'] > old['hud']['health_bind_count'], 'Respawn did not rebind')
            for peer in peers:
                if peer != target:
                    require(roster[peer]['pawn_path'] == before[peer]['pawn_path'], 'Respawn changed another player')
            return True
        return True

    def _id(self, peer, suffix):
        return self.run_id[:12] + '.' + str(self.index) + '.' + peer + '.' + suffix

    def _reject_stale(self, command_id, token):
        self._command(command_id, -1, token, 'RejectedInvalidPlayerToken')
        accepted = self.bridge.call_function('RequestPlayerRestart', token)
        require(accepted is False, 'Restart accepted a stale/foreign World token')
        self.restart_rejections.append({'token': token, 'accepted': accepted})

    def _make_packet(self, phase, peers, roster):
        before = self.preparation['before']
        health_deltas = deltas(phase)
        expected = {p: roster[p]['health'] for p in peers}
        event_floor = {p: self._peer_status(p)['hud']['visual_update_count'] for p in peers}
        command_ids = []
        if phase == 'authority':
            old = self._command_result_report(self.bridge.call_function(
                'ApplyAuthorityHealthDelta', self._id('both', 'ambiguous'), -1.0, True))
            validate_command(old, 'RejectedAmbiguousTarget', False)
            self.phase_commands.append(old)
            self._command(self._id('A', 'invalid'), -1, 'invalid-token', 'RejectedInvalidPlayerToken')
            self._reject_stale(self._id('A', 'foreignworld'), self._peer_status('A')['player']['player_token'])
        if phase == 'rejoin_b':
            old_b = next(row for row in self.history if row['phase'] == 'exit_b')['packet']['roster']['B0']
            require(roster['B1']['player_token'] != old_b['player_token']
                    and roster['B1']['pawn_path'] != old_b['pawn_path'], 'Rejoin reused B0 identity')
            self._reject_stale(self._id('B1', 'oldconnection'), old_b['player_token'])
        for peer, delta in health_deltas.items():
            wanted_before = 100 if delta < 0 else (90 if peer == 'A' else 80)
            require(near(roster[peer]['health'], wanted_before), 'Unexpected baseline for ' + peer)
            command_id = self._id(peer, 'health')
            result = self._command(command_id, delta, roster[peer]['player_token'])
            require(result['target_actor'] == roster[peer]['pawn_path']
                    and near(result['health_after'], wanted_before + delta), 'Wrong applied target/delta')
            self._command(command_id, delta, roster[peer]['player_token'], 'RejectedDuplicateCommand')
            others = [p for p in peers if p != peer]
            if others:
                self._command(command_id, delta, roster[others[0]]['player_token'], 'RejectedDuplicateCommand')
            expected[peer] = wanted_before + delta
            command_ids.append(command_id)
        for peer in peers:
            if peer not in health_deltas:
                require(near(expected[peer], 100), 'Uninvolved player Health changed')
        if phase == 'travel_two':
            for peer in peers:
                hud = self._peer_status(peer)['hud']
                require(hud['construct_count'] >= 3 and hud['destruct_count'] >= 2, 'Missing travel lifecycle')
        return {'run_id': self.run_id, 'phase_index': self.index, 'phase': phase,
                'server_world_token': roster[peers[0]]['world_token'], 'participants': peers,
                'roster': copy.deepcopy(roster), 'expected_health': expected,
                'client_worlds': {p: self._peer_status(p)['player']['world_token'] for p in peers},
                'event_floor': event_floor, 'changed_health': list(health_deltas),
                'command_ids': command_ids, 'server_before': before,
                'commands': copy.deepcopy(self.phase_commands)}

    def _server_tick(self):
        if self.server_ready:
            release = read_json(self.root / 'release.json')
            if release is not None:
                require(release.get('run_id') == self.run_id, 'Wrong final release')
                self._finish()
            return
        validate_hud(hud_state.snapshot())
        phase = PHASES[self.index]
        peers = participants(phase)
        if phase in ('join_b', 'rejoin_b'):
            peer = 'B0' if phase == 'join_b' else 'B1'
            atomic_write(self.root / ('launch-' + peer + '.json'), {'run_id': self.run_id, 'peer': peer})
        if self.packet is None:
            roster = self._roster(peers)
            if roster is None:
                return
            if self.preparation is None:
                if not self._start_phase(phase, peers, roster):
                    return
            elif not self._prepared(phase, peers, roster):
                return
            self.packet = self._make_packet(phase, peers, roster)
            atomic_write(self.root / 'phase.json', self.packet)
            ue.log('UEP_LYRA_NETWORK_PHASE ' + phase)
        acks = {}
        for peer in peers:
            ack = read_json(self.root / 'acks' / peer / (str(self.index) + '.json'))
            if ack is None:
                return
            validate_ack(self.packet, ack, peer)
            if phase == 'authority':
                validate_command(ack['authority_rejection'], 'RejectedNotAuthority', False)
            acks[peer] = ack
        if phase == 'damage_both':
            require(acks['B0']['observed_at_ns'] < acks['A']['observed_at_ns'], 'Expected B-before-A ACK order')
        if phase == 'heal_both':
            require(acks['A']['observed_at_ns'] < acks['B0']['observed_at_ns'], 'Expected A-before-B ACK order')
        if phase == 'exit_b':
            process_exit = read_json(self.root / 'exits' / 'B0.json')
            if process_exit is None or len(self.rows) != 1:
                return
            require(process_exit['run_id'] == self.run_id and process_exit['exit_code'] == 0,
                    'B0 did not exit cleanly')
            old = self.packet['roster']['B0']['player_token']
            self._reject_stale(self._id('B0', 'disconnected'), old)
        if phase != 'exit_b':
            roster = self._roster(peers)
            if roster is None:
                return
            for peer in peers:
                require(near(roster[peer]['health'], self.packet['expected_health'][peer]),
                        'Server Health diverged from client ACK')
        self.history.append({'phase': phase, 'packet': self.packet, 'acks': acks,
                             'server_after': copy.deepcopy(self.rows),
                             'commands': copy.deepcopy(self.phase_commands),
                             'restart_rejections': copy.deepcopy(self.restart_rejections),
                             'bot_isolation': copy.deepcopy(self.bot_isolation),
                             'statuses_before': self.preparation['statuses_before']})
        self.last_phase = self.index
        if phase == 'complete':
            validate_phase_names(self.history, 'server')
            atomic_write(self.root / 'ready-server.json', {'run_id': self.run_id})
            self.server_ready = True
            return
        self.index += 1
        self.packet = None
        self.preparation = None
        self.phase_started = time.monotonic()

    def _client_tick(self):
        if self.player is None or not self._player_ready(self.player):
            return
        packet = read_json(self.root / 'phase.json')
        if packet is None:
            return
        require(packet['run_id'] == self.run_id, 'Wrong run packet')
        if self.peer not in packet['participants']:
            return
        phase = packet['phase']
        if packet['phase_index'] == self.last_phase:
            if phase == 'complete':
                release = read_json(self.root / 'release.json')
                if release is not None:
                    require(release.get('run_id') == self.run_id, 'Wrong client release')
                    self._finish()
            return
        if self.player['world_token'] != packet['client_worlds'][self.peer]:
            return
        if not near(self.player['health'], packet['expected_health'][self.peer]):
            return
        hud = hud_state.snapshot()
        try:
            validate_hud(hud, self.player)
        except RuntimeError:
            return  # Delegate dispatch/rebinding may finish later in this tick.
        rejection = None
        predecessor = ('B0' if phase == 'damage_both' and self.peer == 'A' else
                       'A' if phase == 'heal_both' and self.peer == 'B0' else None)
        if predecessor and not (self.root / 'acks' / predecessor / (str(packet['phase_index']) + '.json')).is_file():
            return
        if phase == 'authority':
            rejection = self._command_result_report(self.bridge.call_function(
                'ApplyAuthorityHealthDeltaToPlayer', self.run_id[:12] + '.' + self.peer + '.deny',
                -10.0, self.player['player_token']))
            validate_command(rejection, 'RejectedNotAuthority', False)
        ack = {'run_id': self.run_id, 'peer': self.peer, 'phase_index': packet['phase_index'],
               'observed_at_ns': time.time_ns(),
               'phase': phase, 'server_world_token': packet['server_world_token'],
               'server_player_token': packet['roster'][self.peer]['player_token'],
               'command_ids': packet['command_ids'], 'player': copy.deepcopy(self.player),
               'hud': hud, 'authority_rejection': rejection}
        # Health reads must be corroborated by a new, correctly-owned delegate event.
        if self.peer in packet['changed_health'] and not any(
                e.get('event') == 'health_changed' and e.get('sequence', 0) > packet['event_floor'][self.peer]
                and near(e.get('health'), self.player['health']) for e in hud['health_events']):
            return
        validate_ack(packet, ack, self.peer)
        atomic_write(self.root / 'acks' / self.peer / (str(packet['phase_index']) + '.json'), ack)
        self.history.append({'phase': phase, 'packet': packet, 'ack': ack})
        self.last_phase = packet['phase_index']
        ue.log('UEP_LYRA_NETWORK_ACK ' + self.peer + ' ' + phase)
        if phase == 'exit_b' and self.peer == 'B0':
            self._finish()
        elif phase == 'complete':
            atomic_write(self.root / ('ready-' + self.peer + '.json'), {'run_id': self.run_id})

    def _finish(self, error=None):
        if self.finished:
            return
        if error is None:
            validate_phase_names(self.history, self.peer)
        report = {'schema_version': 5, 'network_schema_version': 1,
                  'status': 'failed' if error else 'passed', 'peer': self.peer, 'run_id': self.run_id,
                  'mode': self.mode, 'python_version': '.'.join(map(str, sys.version_info[:3])),
                  'gameplay_slice': {'enabled': True}, 'hud': hud_state.snapshot(),
                  'shutdown': None, 'phases': self.history, 'snapshot': self.player,
                  'players': (self.history[-1]['server_after'] if error is None and self.peer == 'server' and self.history else self.rows),
                  'error': error, 'elapsed_seconds': self._wall_elapsed()}
        self.finished = True
        if error is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        ue.log('UEP_LYRA_AWAITING_SHUTDOWN' if error is None else 'UEP_LYRA_NETWORK_FAILED')
        self.shutdown_binding()
        self._request_quit()

    def tick(self, delta_seconds):
        self.peer_frame_snapshots = {}  # Fresh once-per-frame, never stale fallback.
        try:
            if self.finished:
                return False
            now = time.monotonic()
            if self._wall_elapsed() > self.timeout_seconds:
                raise RuntimeError('Network total timeout: ' + str(self.index))
            if now < self.next_tick:
                return True
            self.next_tick = now + 0.1
            world = self._game_world()
            if not _is_valid(world) or not self._attach(world):
                return True
            self.rows = [self._snapshot_report(s) for s in self.bridge.call_function('CapturePlayerSnapshots')]
            if self.peer == 'server':
                self._isolate_bot_combat()
            self.player = self.rows[0] if self.mode == 'client' and len(self.rows) == 1 else None
            atomic_write(self.root / 'status' / (self.peer + '.json'), self._status())
            if self.peer == 'server':
                if now - self.phase_started > 180:
                    raise RuntimeError('Network phase timeout: ' + PHASES[self.index])
                self._server_tick()
            else:
                self._client_tick()
            return not self.finished
        except Exception:
            error = traceback.format_exc()
            ue.log_error(error)
            self._finish(error)
            return False


if not any(flag in sys.argv for flag in ('-UEPLyraWeaponNetwork', '-UEPEffectPadNetwork', '-UEPInventoryPadNetwork', '-UEPGrantGENetwork', '-UEPLauncherNetwork', '-UEPSpawnerNetwork', '-UEPTeleporterNetwork', '-UEPActionTouchNetwork', '-UEPHealAbilityNetwork')):
    runtime = NetworkProbe()
    ticker = ue.add_ticker(runtime.tick)
