"""Real-input two-client weapon acceptance, never writes ammo or inventory.

Native Enhanced Input -> Lyra abilities -> authoritative ammo/replication is
the producer. Files only coordinate phases. The actual Python HUD is compared
with an additional original-BP panel reading the same player's native item.
"""

import copy
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.structs import Geometry

from uep_lyra_network import NetworkProbe
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_screenshots import FrameScreenshotQueue
from uep_lyra_network_protocol import require, validate_hud
from uep_lyra_weapon_protocol import PHASES
from uep_lyra_weapon_input import aim_above_players, aim_snapshot
from uep_lyra_hud import weapon_observer, state as hud_state
from uep_lyra_hud.ammo_mixin import MAGAZINE_AMMO, SPARE_AMMO, MAGAZINE_SIZE, RELOAD_EVENT, _stat
from uep_lyra_hud.shutdown_validation import defer_until_shutdown


PANEL = '/ShooterCore/UserInterface/HUD/W_WeaponAmmoAndName.W_WeaponAmmoAndName_C'


def peers_for(phase):
    if phase in ('join_a', 'fire_a_solo'):
        return ['A']
    return ['A', 'B1' if phase in ('rejoin_b', 'fire_b1', 'complete') else 'B0']


def target_for(phase):
    if phase in ('fire_a', 'reload_a', 'switch_a', 'fire_switched_a', 'respawn_a', 'fire_respawn_a', 'fire_a_solo'):
        return 'A'
    if phase in ('fire_b', 'empty_b', 'reload_b', 'fire_travel_b'):
        return 'B0'
    return 'B1' if phase == 'fire_b1' else None


def weapon_state(controller):
    quickbar = controller.get_component_by_type(ue.find_class('LyraQuickBarComponent'))
    if quickbar is None:
        return None
    item = quickbar.call_function('GetActiveSlotItem')
    if item is None or item.ItemDef is None:
        return None
    slots = quickbar.call_function('GetSlots')
    return {'item': item.get_path_name(), 'definition': item.ItemDef.get_name(),
            'magazine': _stat(item, MAGAZINE_AMMO), 'spare': _stat(item, SPARE_AMMO),
            'maximum': _stat(item, MAGAZINE_SIZE), 'slot': quickbar.call_function('GetActiveSlotIndex'),
            'slots': [entry.get_path_name() if entry else None for entry in slots]}


def counts(value):
    return (value['magazine'], value['spare'], value['maximum'], value['slot'], value['definition'],
            tuple(bool(item) for item in value['slots']))


def panel_state(widget):
    return {'magazine': str(widget.AmmoLeftInMagazineWidget.call_function('GetText')),
            'spare': str(widget.TotalCountWidget.call_function('GetText')),
            'visibility': int(widget.VerticalBoxForHiding.call_function('GetVisibility'))}


class WeaponNetworkProbe(NetworkProbe):
    def __init__(self):
        super().__init__()
        self.baseline = None
        self.baseline_world = None
        self.command_seen = -1
        self.action = None
        self.action_started = 0
        self.input_frames = 0
        self.input_history = []
        self.current_weapon = None
        self.current_hud = None
        self.stable_since = None
        self.last_observation = None
        self.action_names = ('IA_Weapon_Fire', 'IA_Weapon_Fire_Auto')
        self.combat_hud_enabled = '-UEPLyraCombatHUD' in sys.argv
        self.debug_spread_enabled = '-UEPLyraDebugSpread' in sys.argv
        self.production_reticles_enabled = '-UEPLyraProductionReticles' in sys.argv
        self.reticle_hosts_enabled = '-UEPLyraReticleHosts' in sys.argv
        self.ability_progress_enabled = '-UEPLyraAbilityProgress' in sys.argv
        self.ability_progress = None
        self.ability_failure_enabled = '-UEPLyraAbilityFailure' in sys.argv
        self.ability_failure = None
        self.dash_enabled = '-UEPLyraDashCooldown' in sys.argv
        self.dash = None
        self.respawn_enabled = '-UEPLyraRespawnTimer' in sys.argv
        self.respawn = None
        self.quickbar_slots_enabled = '-UEPLyraQuickBarSlots' in sys.argv
        self.quickbar_slots = None
        self.nameplates_enabled = '-UEPLyraNameplates' in sys.argv
        self.nameplates = None
        self.current_nameplates = None
        self.nameplate_captures = set()
        self.nameplate_retirement_seen = -1
        self.nameplate_retirements = []
        if self.nameplates_enabled and self.peer != 'server':
            from uep_lyra_nameplate_probe import NameplateProbe
            self.nameplates = NameplateProbe()
        self.combat_hud = None
        self.current_combat_hud = None
        self.combat_images = []
        self.screenshots = FrameScreenshotQueue(self._emit_screenshot)
        self.progress_captures = set()
        self.failure_captures = set()
        self.dash_captures = set()
        self.respawn_captures = set()
        self.readiness_reason = 'starting'
        self.readiness_history = []
        self.readiness_key = None
        if self.combat_hud_enabled and self.peer != 'server':
            from uep_lyra_combat_hud_probe import CombatHUDProbe
            self.combat_hud = CombatHUDProbe(debug_spread=self.debug_spread_enabled, reticle_hosts=self.reticle_hosts_enabled)
        if self.ability_progress_enabled and self.peer != 'server':
            from uep_lyra_ability_progress_probe import AbilityProgressProbe
            self.ability_progress = AbilityProgressProbe()
        if self.ability_failure_enabled and self.peer != 'server':
            from uep_lyra_ability_failure_probe import AbilityFailureProbe
            self.ability_failure = AbilityFailureProbe(self.peer)
        if self.dash_enabled and self.peer != 'server':
            from uep_lyra_dash_probe import DashCooldownProbe
            self.dash = DashCooldownProbe()
        if self.respawn_enabled and self.peer != 'server':
            from uep_lyra_respawn_probe import RespawnTimerProbe
            self.respawn = RespawnTimerProbe()
        if self.quickbar_slots_enabled and self.peer != 'server':
            from uep_lyra_quickbar_probe import QuickBarSlotsProbe
            self.quickbar_slots = QuickBarSlotsProbe()

    def _status(self):
        result = super()._status()
        result.update(weapon=copy.deepcopy(self.current_weapon), weapon_hud=copy.deepcopy(self.current_hud),
                      weapon_observer=weapon_observer.snapshot(), input_frames=self.input_frames)
        if self.combat_hud_enabled:
            result['combat_hud'] = copy.deepcopy(self.current_combat_hud)
        if self.nameplates_enabled:
            result['nameplates'] = copy.deepcopy(self.current_nameplates)
        if self.peer != 'server':
            detail = {'reason': self.readiness_reason,
                      'world_token': self.player['world_token'] if self.player else None,
                      'player_id': self.player['player_id'] if self.player else None,
                      'phase_index': self.last_phase,
                      'duration': copy.deepcopy(self.ability_progress.debug) if self.ability_progress is not None else None,
                      'failure': copy.deepcopy(self.ability_failure.debug) if self.ability_failure is not None else None,
                      'dash': copy.deepcopy(self.dash.debug) if self.dash is not None else None,
                      'respawn': copy.deepcopy(self.respawn.debug) if self.respawn is not None else None,
                      'quickbar_slots': copy.deepcopy(self.quickbar_slots.debug) if self.quickbar_slots is not None else None}
            result['readiness_detail'] = detail
            key = (detail['reason'], detail['world_token'], detail['player_id'])
            if key != self.readiness_key:
                self.readiness_key = key
                self.readiness_history.append(detail)
                atomic_write(self.root / ('readiness-' + self.peer + '.json'), self.readiness_history)
        if self.peer != 'server':
            result['ready'] = result['ready'] and self.current_weapon is not None and self.current_hud is not None
            if self.combat_hud_enabled:
                result['ready'] = result['ready'] and self.current_combat_hud is not None
        return result

    def _actual_hud(self, controller):
        matches = []
        for entry in weapon_observer.snapshot()['active_widgets']:
            obj = ue.find_object(entry)
            if (obj is not None and obj.get_class().get_name() == 'W_WeaponAmmoAndName_C'
                    and obj.call_function('GetOwningPlayer') == controller):
                matches.append(obj)
        require(len(matches) <= 1, 'Multiple production weapon panels own this controller')
        return matches[0] if matches else None

    def _observe_client(self):
        self.current_nameplates = None
        self.current_combat_hud = None
        self.readiness_reason = 'player-not-ready'
        if self.player is None or not self._player_ready(self.player):
            self.current_weapon = self.current_hud = None
            return
        controller = ue.find_object(self.player['controller_path'])
        self.current_weapon = weapon_state(controller)
        widget = self._actual_hud(controller)
        self.readiness_reason = 'native-weapon-or-production-panel-unavailable'
        if widget is None or self.current_weapon is None:
            self.current_hud = None
            return
        if self.baseline_world != self.player['world_token']:
            if self.baseline is not None and self.baseline.is_valid():
                self.baseline.RemoveFromParent()
                self.baseline.remove_from_root()
            self.baseline = controller.create_widget(ue.load_class(PANEL))
            # This invisible test-owned widget is not retained by a viewport.
            # A Python UObject wrapper alone does not survive native GC.
            self.baseline.add_to_root()
            ue.set_mixin_profile(self.baseline, 'BlueprintFallback')
            # It is not added to the UI: only the actual shipped panel is shown.
            self.baseline_world = self.player['world_token']
        self.baseline.call_function('Tick', Geometry(), 0.016)
        actual, original = panel_state(widget), panel_state(self.baseline)
        expected = {'magazine': str(self.current_weapon['magazine']),
                    'spare': format(self.current_weapon['spare'], ','), 'visibility': 0}
        # A change can be observed between the native replication and sampler
        # callbacks in one frame. Wait for convergence, never overwrite the HUD.
        self.current_hud = ({'python': actual, 'blueprint': original, 'native': expected,
                             'widget': widget.get_path_name(), 'controller': controller.get_path_name(),
                             'profile': ue.get_mixin_profile(widget), 'class': widget.get_class().get_name()}
                            if actual == original == expected else None)
        self.readiness_reason = 'weapon-panel-mismatch' if self.current_hud is None else 'ready'
        if self.combat_hud is not None and self.current_hud is not None:
            self.current_combat_hud = self.combat_hud.observe(controller, self.player, self.current_weapon)
            if self.current_combat_hud is None:
                self.readiness_reason = 'combat-presentation-not-converged'
            if (self.production_reticles_enabled and self.current_combat_hud is not None
                    and 'production_reticle' not in self.current_combat_hud):
                self.current_combat_hud = None
                self.readiness_reason = 'production-reticle-unavailable'
            if self.ability_progress is not None and self.current_combat_hud is not None:
                duration = self.ability_progress.observe(controller, self.player)
                if duration is None:
                    self.current_combat_hud = None
                    self.readiness_reason = 'ability-progress-not-converged'
                else:
                    self.current_combat_hud['ability_progress'] = duration
                    capture = (self.peer, duration['phase'])
                    if (duration['phase'] in ('join_b', 'rejoin_b') and duration['python']['visibility'] == 0
                            and duration['automatic_tick_delta'] > 1 and capture not in self.progress_captures):
                        image = str(self.root / ('ability-progress-' + self.peer + '-' + duration['phase'] + '.png'))
                        self._queue_screenshot(image, controller)
                        self.progress_captures.add(capture)
            if self.ability_failure is not None and self.current_combat_hud is not None:
                feedback = self.ability_failure.observe(controller, self.player)
                if feedback is None:
                    self.current_combat_hud = None
                    self.readiness_reason = 'ability-failure-not-converged'
                else:
                    self.current_combat_hud['ability_failure'] = feedback
                    capture = (self.peer, feedback['phase'])
                    if (feedback['phase'] in ('join_b', 'rejoin_b') and feedback['python']['visibility'] == 3 and
                            feedback['phase_elapsed'] > 0.35 and capture not in self.failure_captures):
                        image = str(self.root / ('ability-failure-' + self.peer + '-' + feedback['phase'] + '.png'))
                        self._queue_screenshot(image, controller)
                        self.failure_captures.add(capture)
            if self.dash is not None and self.current_combat_hud is not None:
                cooldown = self.dash.observe(controller, self.player)
                if cooldown is None:
                    self.current_combat_hud = None
                    self.readiness_reason = 'dash-not-converged'
                else:
                    self.current_combat_hud['dash_cooldown'] = cooldown
                    capture = (self.peer, cooldown['phase'])
                    if (cooldown['phase'] in ('join_b', 'rejoin_b') and cooldown['python']['charging'] and
                            0.2 < cooldown['python']['fill'] < 0.6 and capture not in self.dash_captures):
                        image = str(self.root / ('dash-' + self.peer + '-' + cooldown['phase'] + '.png'))
                        self._queue_screenshot(image, controller)
                        self.dash_captures.add(capture)
            if self.respawn is not None and self.current_combat_hud is not None:
                countdown = self.respawn.observe(controller, self.player)
                if countdown is None:
                    self.current_combat_hud = None
                    self.readiness_reason = 'respawn-not-converged'
                else:
                    self.current_combat_hud['respawn_timer'] = countdown
                    capture = (self.peer, countdown['phase'])
                    if (countdown['phase'] in ('join_b', 'rejoin_b') and countdown['python']['visibility'] == 0 and
                            countdown['phase_elapsed'] > 2.0 and countdown['python']['respawning'] and
                            capture not in self.respawn_captures):
                        image = str(self.root / ('respawn-' + self.peer + '-' + countdown['phase'] + '.png'))
                        self._queue_screenshot(image, controller)
                        self.respawn_captures.add(capture)
            if self.quickbar_slots is not None and self.current_combat_hud is not None:
                quickbar = self.quickbar_slots.observe(controller, self.player)
                if quickbar is None:
                    self.current_combat_hud = None
                    self.readiness_reason = 'quickbar-slots-not-converged'
                else:
                    self.current_combat_hud['quickbar_slots'] = quickbar
        if self.nameplates is not None and self.current_hud is not None:
            self.current_nameplates = self.nameplates.observe(controller, self.player)
            if self.current_nameplates is None:
                self.current_hud = None
                self.readiness_reason = 'nameplates-not-converged: ' + repr(self.nameplates.debug)
            elif self.player['world_token'] not in self.nameplate_captures:
                self.nameplate_captures.add(self.player['world_token'])
                self._queue_screenshot(str(self.root / ('nameplates-' + self.peer + '-' + str(len(self.nameplate_captures)) + '.png')), controller)

    def _server_roster(self, peers):
        roster = self._roster(peers)
        if roster is None:
            return None
        for peer, row in roster.items():
            weapon = weapon_state(ue.find_object(row['controller_path']))
            status = self._peer_status(peer)
            if status is None:
                return None  # Peer may be publishing its next complete snapshot.
            client = status['weapon']
            if weapon is None or client is None or counts(weapon) != counts(client):
                return None
            row['weapon'] = weapon
        return roster

    def _server_tick(self):
        if self.server_ready:
            release = read_json(self.root / 'release.json')
            if release is not None:
                require(release['run_id'] == self.run_id, 'Foreign release')
                self._finish()
            return
        phase = PHASES[self.index]
        peers = peers_for(phase)
        if phase in ('join_b', 'rejoin_b'):
            peer = 'B0' if phase == 'join_b' else 'B1'
            atomic_write(self.root / ('launch-' + peer + '.json'), {'run_id': self.run_id, 'peer': peer})
        roster = self._server_roster(peers)
        if self.packet is None:
            if roster is None:
                return
            if self.preparation is None:
                self.preparation = {'roster': copy.deepcopy(roster), 'statuses': {p: self._peer_status(p) for p in peers}}
                if phase == 'switch_a' and sum(bool(item) for item in roster['A']['weapon']['slots']) < 2:
                    controller = ue.find_object(roster['A']['controller_path'])
                    pawn = controller.get_controlled_pawn()
                    pads, = self.gameplay_statics.call_function('GetAllActorsOfClass', self.world, ue.find_class('LyraWeaponSpawner'))
                    pad = next((obj for obj in pads if obj.bIsWeaponAvailable and obj.WeaponDefinition is not None
                                and 'Rifle' in obj.WeaponDefinition.InventoryItemDefinition.get_name()), None)
                    require(pad is not None, 'No available native rifle pickup on the map')
                    # Exercise the existing authoritative pickup entry (including
                    # BP GiveWeapon, native inventory/equipment and replication).
                    # This is fixture setup, not a claim of walking/overlap input.
                    pad.call_function('AttemptPickUpWeapon', pawn)
                    quickbar = controller.get_component_by_type(ue.find_class('LyraQuickBarComponent'))
                    require(sum(item is not None for item in quickbar.call_function('GetSlots')) >= 2,
                            'Native pickup did not grant a second weapon')
                    quickbar.call_function('SetActiveSlotIndex', roster['A']['weapon']['slot'])
                    self.preparation['pickup'] = {'actor': pad.get_path_name(), 'entry': 'AttemptPickUpWeapon',
                                                   'physical_overlap_tested': False, 'inventory_written_by_probe': False}
                    return
                if phase.startswith('travel_'):
                    require(self.world.server_travel('/ShooterMaps/Maps/L_Expanse?NumBots=3'), 'Travel rejected')
                    return
                if phase == 'respawn_a':
                    require(self.bridge.call_function('RequestPlayerRestart', roster['A']['player_token']), 'Restart rejected')
                    if self.nameplates_enabled:
                        # Controller::Reset unpossesses but does not destroy
                        # the old Pawn. Exercise real Source EndPlay explicitly,
                        # rather than pretending this helper is a death ability.
                        from uep_lyra_network_restart import retire_old_pawn
                        self.preparation['old_pawn_retirement'] = retire_old_pawn(roster['A']['pawn_path'])
                        old_player_id = self.preparation['statuses']['A']['player']['player_id']
                        client_paths = {}
                        for peer in peers:
                            candidates = [item['pawn'] for item in self.preparation['statuses'][peer]['nameplates']['descriptors'] if item['player_id'] == old_player_id]
                            require(len(candidates) == 1, 'Cannot identify the old replicated Pawn in client nameplates')
                            client_paths[peer] = candidates[0]
                        atomic_write(self.root / 'nameplate-retirement.json', {'run_id': self.run_id, 'phase_index': self.index,
                                     'pawns': client_paths})
                    return
            before = self.preparation['roster']
            if phase.startswith('travel_'):
                if roster[peers[0]]['world_token'] == before[peers[0]]['world_token']:
                    return
                if any(self._peer_status(p)['player']['world_token'] == self.preparation['statuses'][p]['player']['world_token'] for p in peers):
                    return
            if phase == 'respawn_a' and (roster['A']['pawn_path'] == before['A']['pawn_path']
                                       or self._peer_status('A')['player']['pawn_path'] == self.preparation['statuses']['A']['player']['pawn_path']):
                return
            self.packet = {'run_id': self.run_id, 'phase_index': self.index, 'phase': phase, 'participants': peers,
                           'target': target_for(phase), 'roster': copy.deepcopy(roster),
                           'before': copy.deepcopy(before), 'statuses_before': self.preparation['statuses'],
                           'pickup_setup': self.preparation.get('pickup')}
            if self.nameplates_enabled and phase == 'respawn_a':
                self.packet['old_pawn_retirement'] = self.preparation['old_pawn_retirement']
            atomic_write(self.root / 'phase.json', self.packet)
            ue.log('UEP_LYRA_WEAPON_NETWORK_PHASE ' + phase)
        acks = {peer: read_json(self.root / 'acks' / peer / (str(self.index) + '.json')) for peer in peers}
        if any(ack is None for ack in acks.values()):
            return
        if phase == 'exit_b':
            if not (self.root / 'exits' / 'B0.json').is_file() or len(self.rows) != 1:
                return
            roster = self._server_roster(['A'])
        if roster is None:
            return
        for peer, ack in acks.items():
            require(ack['run_id'] == self.run_id and ack['phase_index'] == self.index
                    and ack['peer'] == peer, 'Stale/misattributed ACK')
            if peer in roster:
                if counts(ack['weapon']) != counts(roster[peer]['weapon']):
                    return
            baseline = self.packet['roster'][peer]['weapon']
            value = ack['weapon']
            if peer != self.packet['target']:
                require(counts(value) == counts(baseline), 'Uninvolved player ammo changed')
            elif phase.startswith('fire_'):
                require(0 <= value['magazine'] <= baseline['magazine'] - 1
                        and value['spare'] == baseline['spare'], 'Native fire did not consume magazine ammo only')
                require(ack['input_frames'] > self.packet['statuses_before'][peer]['input_frames'], 'No real fire input')
            elif phase.startswith('reload_'):
                require(value['magazine'] == value['maximum'] and value['magazine'] > baseline['magazine']
                        and value['spare'] < baseline['spare']
                        and value['magazine'] + value['spare'] == baseline['magazine'] + baseline['spare'], 'Native reload conservation failed')
            elif phase == 'empty_b':
                require(value['magazine'] == 0 and value['spare'] == baseline['spare'], 'Empty magazine was not reached by firing')
            elif phase == 'switch_a':
                require(value['slot'] != baseline['slot'] and value['item'] != baseline['item'], 'Native quickbar RPC did not switch item')
        self.history.append({'phase': phase, 'packet': self.packet, 'acks': acks,
                             'server_after': copy.deepcopy(roster)})
        if self.nameplates_enabled:
            from uep_lyra_nameplate_probe import server_observation
            self.history[-1]['nameplate_server'] = server_observation()
        self.last_phase = self.index
        if phase == 'complete':
            atomic_write(self.root / 'ready-server.json', {'run_id': self.run_id})
            self.server_ready = True
            return
        self.index += 1
        self.packet = self.preparation = None
        self.phase_started = time.monotonic()

    def _drive_input(self):
        if self.action != 'fire' or self.player is None:
            return
        controller = ue.find_object(self.player['controller_path'])
        value = weapon_state(controller)
        if value is None:
            return
        # Stop immediately at the observed goal. No SetStat/RemoveStat calls.
        if value['magazine'] <= self.fire_goal:
            self.action = None
            self.stable_since = time.monotonic()
            return
        # Both Lyra fire intents are mapped to the same physical trigger; the
        # equipped weapon chooses which ability it owns. Inject one frame.
        # Resolve after travel: Python wrappers do not root UE assets. Pulses
        # provide release edges for semiautomatic weapons as a user would.
        pressed = (time.monotonic() - self.action_started) % 0.30 < 0.12
        if self.combat_hud is not None:
            self.combat_hud.fire(pressed)
        else:
            for name in self.action_names:
                action = ue.load_object(ue.find_class('InputAction'), '/Game/Input/Actions/' + name + '.' + name)
                require(action.is_valid(), 'Native input action failed to load')
                controller.inject_enhanced_input_for_action(action, pressed)
        self.input_frames += 1

    def _client_tick(self):
        if self.nameplates_enabled:
            retirement = read_json(self.root / 'nameplate-retirement.json')
            if retirement is not None and retirement['phase_index'] > self.nameplate_retirement_seen and self.peer in retirement['pawns']:
                require(retirement['run_id'] == self.run_id, 'Foreign nameplate retirement command')
                from uep_lyra_network_restart import retire_client_sources
                from uep_lyra_hud.nameplate_source_mixin import CLASS as SOURCE_CLASS
                value = retire_client_sources(retirement['pawns'][self.peer], ue.load_class(SOURCE_CLASS))
                value['phase_index'] = retirement['phase_index']
                self.nameplate_retirements.append(value)
                self.nameplate_retirement_seen = retirement['phase_index']
        self._observe_client()
        if self.current_nameplates is not None:
            self.current_nameplates['fixture_source_retirements'] = copy.deepcopy(self.nameplate_retirements)
        atomic_write(self.root / 'status' / (self.peer + '.json'), self._status())
        if (self.current_weapon is None or self.current_hud is None
                or (self.combat_hud_enabled and self.current_combat_hud is None)):
            return
        packet = read_json(self.root / 'phase.json')
        if packet is None or self.peer not in packet['participants']:
            return
        require(packet['run_id'] == self.run_id, 'Wrong run packet')
        phase = packet['phase']
        if packet['phase_index'] == self.last_phase:
            if phase == 'complete' and (self.root / 'release.json').is_file():
                self._finish()
            return
        if packet['phase_index'] != self.command_seen:
            self.command_seen = packet['phase_index']
            self.stable_since = time.monotonic()
            self.action = None
            if self.ability_progress is not None:
                self.ability_progress.begin(phase)
            if self.ability_failure is not None:
                self.ability_failure.begin(phase)
            if self.dash is not None:
                self.dash.begin(phase)
            if self.respawn is not None:
                self.respawn.begin(phase)
            if packet['target'] == self.peer:
                controller = ue.find_object(self.player['controller_path'])
                if phase.startswith('fire_') or phase == 'empty_b':
                    self.fire_goal = 0 if phase == 'empty_b' else max(0, self.current_weapon['magazine'] - 3)
                    self.action = 'fire'
                    if self.combat_hud is not None:
                        self.combat_hud.select_fire_profile(phase)
                    # Fire into the sky so human/bot health cannot confound ammo ownership.
                    aim_above_players(controller)
                elif phase.startswith('reload_'):
                    self._actual_hud(controller).call_function(RELOAD_EVENT)
                    self.action = 'reload'
                elif phase == 'switch_a':
                    quickbar = controller.get_component_by_type(ue.find_class('LyraQuickBarComponent'))
                    slots = self.current_weapon['slots']
                    next_slot = next((i for i, item in enumerate(slots) if item and i != self.current_weapon['slot']), None)
                    require(next_slot is not None, 'No second native weapon available')
                    quickbar.call_function('SetActiveSlotIndex', next_slot)
                    self.action = 'switch'
            self.action_started = time.monotonic()
        if self.action == 'reload' and self.current_weapon['magazine'] == self.current_weapon['maximum']:
            self.action = None
            self.stable_since = time.monotonic()
        if self.action == 'switch' and self.current_weapon['slot'] != packet['roster'][self.peer]['weapon']['slot']:
            self.action = None
            self.stable_since = time.monotonic()
        require(time.monotonic() - self.action_started < 100, 'Weapon action timeout: ' + phase + ' ' + repr(self.current_weapon))
        if self.action is not None or time.monotonic() - self.stable_since < 0.7:
            return
        if self.ability_progress is not None and not self.ability_progress.completed:
            return
        if self.ability_failure is not None and not self.ability_failure.completed:
            return
        if self.dash is not None and not self.dash.completed:
            return
        if self.respawn is not None and not self.respawn.completed:
            return
        require(self.current_hud['profile'] == 'Python' and not weapon_observer.snapshot()['errors'], 'Production Python HUD failed')
        ack = {'run_id': self.run_id, 'peer': self.peer, 'phase_index': packet['phase_index'], 'phase': phase,
               'player': copy.deepcopy(self.player), 'weapon': copy.deepcopy(self.current_weapon),
               'weapon_hud': copy.deepcopy(self.current_hud), 'weapon_observer': weapon_observer.snapshot(),
               'input_frames': self.input_frames,
               'aim_rotation': aim_snapshot(ue.find_object(self.player['controller_path']))}
        if self.combat_hud_enabled:
            ack['combat_hud'] = copy.deepcopy(self.current_combat_hud)
            if packet['target'] == self.peer and (phase.startswith('fire_') or phase == 'empty_b'):
                image = str(self.root / ('combat-' + self.peer + '-' + phase + '.png'))
                self._queue_screenshot(image, ue.find_object(self.player['controller_path']))
        if self.nameplates_enabled:
            ack['nameplates'] = copy.deepcopy(self.current_nameplates)
        atomic_write(self.root / 'acks' / self.peer / (str(packet['phase_index']) + '.json'), ack)
        self.history.append({'phase': phase, 'packet': packet, 'ack': ack})
        self.last_phase = packet['phase_index']
        ue.log('UEP_LYRA_WEAPON_NETWORK_ACK ' + self.peer + ' ' + phase)
        if phase == 'exit_b' and self.peer == 'B0':
            self._finish()
        elif phase == 'complete':
            atomic_write(self.root / ('ready-' + self.peer + '.json'), {'run_id': self.run_id})

    def _finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        if self.combat_hud is not None:
            self.combat_hud.close()
        if self.ability_progress is not None:
            self.ability_progress.close()
        if self.ability_failure is not None:
            self.ability_failure.close()
        if self.dash is not None:
            self.dash.close()
        if self.respawn is not None:
            self.respawn.close()
        if self.quickbar_slots is not None:
            self.quickbar_slots.close()
        if self.nameplates is not None:
            self.nameplates.close(final=True)
        if self.baseline is not None and self.baseline.is_valid():
            self.baseline.remove_from_root()
        self.baseline = None
        report = {'schema_version': 5, 'network_schema_version': 4, 'status': 'failed' if error else 'passed',
                  'peer': self.peer, 'run_id': self.run_id, 'mode': self.mode, 'phases': self.history,
                  'hud': hud_state.snapshot(), 'weapon_observer': weapon_observer.snapshot(), 'shutdown': None,
                  'gameplay_slice': {'enabled': True}, 'error': error, 'elapsed_seconds': self._wall_elapsed()}
        report['combat_hud_slice'] = {'enabled': self.combat_hud_enabled,
                                      'physical_touch_tested': False, 'inventory_written': False,
                                      'images': self.combat_images}
        report['screenshot_queue'] = self.screenshots.snapshot()
        report['debug_spread_slice'] = {'enabled': self.debug_spread_enabled}
        report['production_reticle_slice'] = {'enabled': self.production_reticles_enabled}
        report['reticle_host_slice'] = {'enabled': self.reticle_hosts_enabled}
        report['ability_progress_slice'] = {'enabled': self.ability_progress_enabled,
                                          'synthetic_local_messages': True,
                                          'native_interaction_producer_tested': False,
                                          'replicated_duration_message_tested': False}
        report['ability_failure_slice'] = {'enabled': self.ability_failure_enabled, 'synthetic_local_messages': True,
                                          'native_ability_producer_tested': False, 'replicated_failure_message_tested': False}
        from uep_lyra_hud import ability_failure_mixin
        report['ability_failure_observers'] = ability_failure_mixin.snapshot()
        report['dash_cooldown_slice'] = {'enabled': self.dash_enabled, 'synthetic_local_messages': True,
                                        'native_dash_producer_tested': False, 'replicated_duration_message_tested': False}
        from uep_lyra_hud import dash_cooldown_mixin
        report['dash_cooldown_observers'] = dash_cooldown_mixin.snapshot()
        report['respawn_timer_slice'] = {'enabled': self.respawn_enabled, 'synthetic_local_messages': True,
                                        'native_respawn_producer_tested': False, 'replicated_message_tested': False}
        from uep_lyra_hud import respawn_timer_mixin
        report['respawn_timer_observers'] = respawn_timer_mixin.snapshot()
        report['quickbar_slots_slice'] = {'enabled': self.quickbar_slots_enabled, 'synthetic_local_messages': False,
                                         'external_named_query_migrated': True, 'bp_initialization_parity_tested': False}
        from uep_lyra_hud import quickbar_slot_mixin
        report['quickbar_slot_observers'] = quickbar_slot_mixin.snapshot()
        from uep_lyra_hud import weapon_reticle_mixin
        report['weapon_reticle_observers'] = weapon_reticle_mixin.snapshot()
        from uep_lyra_hud import reticle_host_mixin
        report['reticle_host_observers'] = reticle_host_mixin.snapshot()
        from uep_lyra_hud import ability_progress_mixin
        report['ability_progress_observers'] = ability_progress_mixin.snapshot()
        report['readiness_history'] = self.readiness_history
        report['nameplate_slice'] = {'enabled': self.nameplates_enabled, 'synthetic_messages': False,
            'native_state_written': False, 'projection_parity_tested': False, 'production_lifecycle_replayed': False}
        if self.nameplates_enabled:
            from uep_lyra_nameplate_probe import server_observation
            from uep_lyra_nameplate_placement import read_placement
            from uep_lyra_hud import nameplate_source_mixin, nameplate_manager_mixin, nameplate_mixin
            report['nameplate_observers'] = {'sources': nameplate_source_mixin.snapshot(),
                'managers': nameplate_manager_mixin.snapshot(), 'widgets': nameplate_mixin.snapshot(),
                'native_placement': read_placement()}
            if self.nameplates is not None:
                report['nameplate_comparator_roots'] = self.nameplates.root_evidence()
        if error is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        ue.log('UEP_LYRA_AWAITING_SHUTDOWN' if error is None else 'UEP_LYRA_WEAPON_NETWORK_FAILED')
        self.shutdown_binding()
        self._request_quit()

    def _queue_screenshot(self, image, controller):
        self.screenshots.request(image, self.world, controller)
        self.combat_images.append(image)

    def _emit_screenshot(self, image, world, controller):
        require(world.is_valid() and controller.is_valid(), 'Screenshot crossed destroyed world/controller')
        ue.find_class('KismetSystemLibrary').get_cdo().call_function('ExecuteConsoleCommand', world,
            'Shot SHOWUI -nosuffix filename="' + image + '"', controller)

    def tick(self, delta):
        self.peer_frame_snapshots = {}  # All decisions use one peer snapshot.
        try:
            if self.finished:
                return False
            self.screenshots.drain_one()  # Once per native frame, before readiness can enqueue.
            self._drive_input()
            now = time.monotonic()
            require(self._wall_elapsed() < 900, 'Weapon network total timeout')
            if now < self.next_tick:
                return True
            self.next_tick = now + 0.05
            world = self._game_world()
            if world is None or not self._attach(world):
                return True
            self.rows = [self._snapshot_report(s) for s in self.bridge.call_function('CapturePlayerSnapshots')]
            self.player = self.rows[0] if self.peer != 'server' and len(self.rows) == 1 else None
            if self.peer == 'server':
                self._isolate_bot_combat()
                require(now - self.phase_started < 140, 'Weapon phase timeout: ' + PHASES[self.index])
                self._server_tick()
            else:
                self._client_tick()
            atomic_write(self.root / 'status' / (self.peer + '.json'), self._status())
            return not self.finished
        except Exception:
            detail = traceback.format_exc()
            ue.log_error(detail)
            self._finish(detail)
            return False


runtime = WeaponNetworkProbe()
ticker = ue.add_ticker(runtime.tick)
