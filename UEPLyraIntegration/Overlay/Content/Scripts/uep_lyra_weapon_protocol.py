"""Fail-closed report contracts for real weapon input/replication evidence."""

PHASES = ('join_a', 'join_b', 'fire_a', 'fire_b', 'reload_a', 'empty_b', 'reload_b',
          'switch_a', 'fire_switched_a', 'respawn_a', 'fire_respawn_a', 'travel_one',
          'fire_travel_b', 'travel_two', 'exit_b', 'fire_a_solo', 'rejoin_b', 'fire_b1', 'complete')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def validate_reports(reports, run_id, combat_hud=False, debug_spread=False, production_reticles=False, reticle_hosts=False,
                     ability_progress=False, ability_failure=False, dash_cooldown=False, respawn_timer=False, quickbar_slots=False, nameplates=False):
    require(not debug_spread or combat_hud, 'Debug spread requires combat HUD lane')
    require(not production_reticles or combat_hud, 'Production reticles require combat HUD lane')
    require(not reticle_hosts or production_reticles, 'Reticle hosts require production reticle lane')
    require(not ability_progress or combat_hud, 'Ability progress requires combat HUD lane')
    require(not ability_failure or combat_hud, 'Ability failure requires combat HUD lane')
    require(not dash_cooldown or combat_hud, 'Dash requires combat HUD lane')
    require(not respawn_timer or combat_hud, 'Respawn requires combat HUD lane')
    require(not quickbar_slots or combat_hud, 'Quickbar requires combat HUD lane')
    require(not nameplates or combat_hud, 'Nameplates require combat HUD lane')
    require(set(reports) == {'server', 'A', 'B0', 'B1'}, 'Need dedicated server, A, B0 and rejoined B1')
    for peer, report in reports.items():
        require(report['run_id'] == run_id and report['peer'] == peer and report['network_schema_version'] == 4,
                'Wrong report identity/schema')
        require(report['status'] == 'passed' and report['shutdown']['status'] == 'passed', 'Process/shutdown failed')
        require(report.get('nameplate_slice', {}).get('enabled', False) is nameplates, 'Wrong nameplate validation lane')
        if nameplates:
            from uep_lyra_nameplate_protocol import validate_scopes as validate_nameplate_scopes, validate_comparator_roots
            validate_nameplate_scopes(report['shutdown']['nameplate_observers'], peer)
            if peer != 'server':
                validate_comparator_roots(report['nameplate_comparator_roots'], final=True)
        require(report.get('combat_hud_slice', {}).get('enabled', False) is combat_hud,
                'Wrong combat HUD validation lane')
        require(report.get('debug_spread_slice', {}).get('enabled', False) is debug_spread, 'Wrong debug spread validation lane')
        require(report.get('production_reticle_slice', {}).get('enabled', False) is production_reticles, 'Wrong production reticle validation lane')
        require(report.get('reticle_host_slice', {}).get('enabled', False) is reticle_hosts, 'Wrong reticle host validation lane')
        require(report.get('ability_progress_slice', {}).get('enabled', False) is ability_progress, 'Wrong ability progress validation lane')
        if ability_progress:
            from uep_lyra_ability_progress_protocol import validate_scopes
            validate_scopes(report['shutdown']['ability_progress_observers'], peer)
        require(report.get('ability_failure_slice', {}).get('enabled', False) is ability_failure, 'Wrong ability failure validation lane')
        if ability_failure:
            from uep_lyra_ability_failure_protocol import validate_scopes as validate_failure_scopes
            validate_failure_scopes(report['shutdown']['ability_failure_observers'], peer)
        require(report.get('dash_cooldown_slice', {}).get('enabled', False) is dash_cooldown, 'Wrong Dash validation lane')
        if dash_cooldown:
            from uep_lyra_dash_protocol import validate_scopes as validate_dash_scopes
            validate_dash_scopes(report['shutdown']['dash_cooldown_observers'], peer)
        require(report.get('respawn_timer_slice', {}).get('enabled', False) is respawn_timer, 'Wrong respawn validation lane')
        if respawn_timer:
            from uep_lyra_respawn_protocol import validate_scopes as validate_respawn_scopes
            validate_respawn_scopes(report['shutdown']['respawn_timer_observers'], peer)
        if combat_hud and (report.get('screenshot_queue') is not None or respawn_timer):
            from uep_lyra_network_screenshots import validate_queue
            validate_queue(report['screenshot_queue'], report['combat_hud_slice']['images'], peer)
        require(report.get('quickbar_slots_slice', {}).get('enabled', False) is quickbar_slots, 'Wrong quickbar validation lane')
        if quickbar_slots:
            from uep_lyra_quickbar_protocol import validate_scopes as validate_quickbar_scopes
            validate_quickbar_scopes(report['shutdown']['quickbar_slot_observers'], peer)
        if reticle_hosts:
            hosts = report['shutdown']['reticle_host_observers']
            require(all(type(hosts[key]) is int and hosts[key] >= 0 for key in ('active_count', 'scopes_created', 'scopes_closed')),
                    'Invalid production host counters')
            require(hosts['active_count'] == 0 and hosts['scopes_created'] == hosts['scopes_closed'] and not hosts['errors'],
                    'Production reticle host scope leak/error')
            require(hosts['scopes_created'] == 0 if peer == 'server' else hosts['scopes_created'] > 0,
                    'Dedicated server UI or missing client host scope')
        if production_reticles:
            reticles = report['shutdown']['weapon_reticle_observers']
            require(reticles['active_count'] == 0 and reticles['scopes_created'] == reticles['scopes_closed']
                    and not reticles['errors'], 'Production reticle scope leak/error')
        final = report['shutdown']['weapon_observer']
        require(final['active_count'] == 0 and not final['ticker_active'] and not final['errors']
                and final['subscribed'] == final['unsubscribed'] and final['active_scopes'] == 0
                and final['scope_created'] == final['scope_closed'], 'Weapon observer leak/error')
        expected = (PHASES if peer in ('server', 'A') else
                    PHASES[1:15] if peer == 'B0' else PHASES[16:])
        require(tuple(row['phase'] for row in report['phases']) == expected, 'Missing/reordered weapon phases: ' + peer)
    for row in reports['server']['phases']:
        packet = row['packet']
        require(packet['run_id'] == run_id and row['phase'] == packet['phase'], 'Foreign packet')
        for peer, ack in row['acks'].items():
            require(ack['run_id'] == run_id and ack['peer'] == peer and ack['phase'] == row['phase']
                    and ack['phase_index'] == packet['phase_index'], 'Wrong ACK')
            hud, weapon = ack['weapon_hud'], ack['weapon']
            require(hud['profile'] == 'Python' and hud['class'] == 'W_WeaponAmmoAndName_C', 'Wrong production presenter')
            require(hud['controller'] == ack['player']['controller_path'], 'HUD crossed player ownership')
            expected = {'magazine': str(weapon['magazine']), 'spare': format(weapon['spare'], ','), 'visibility': 0}
            require(hud['python'] == hud['blueprint'] == hud['native'] == expected, 'BP/Python/native HUD mismatch')
            require(ack['weapon_observer']['source'] == 'read-only-frame-sampler' and not ack['weapon_observer']['errors'],
                    'Observer failure or misleading source')
            require(ack['weapon_observer']['active_scopes'] == 1
                    and ack['weapon_observer']['message_source'] == 'native-QuickBar-and-possession-signals', 'Missing native message scope')
            server_row = row['server_after'].get(peer)
            if server_row:
                require(server_row['player_id'] == ack['player']['player_id'], 'Server/client player mismatch')
                require(all(server_row['weapon'][key] == weapon[key]
                            for key in ('magazine', 'spare', 'maximum', 'definition', 'slot')), 'Replication mismatch')
            before = packet['roster'][peer]['weapon']
            if combat_hud:
                from uep_lyra_combat_hud_protocol import validate_combat_ack
                validate_combat_ack(row, peer, ack)
            if debug_spread:
                require('debug_spread' in ack['combat_hud'], 'Missing debug spread checkpoint')
            if production_reticles:
                from uep_lyra_combat_hud_protocol import validate_production_reticle
                require('production_reticle' in ack['combat_hud'], 'Missing production reticle checkpoint')
                validate_production_reticle(ack['combat_hud']['production_reticle'], ack)
            if reticle_hosts:
                from uep_lyra_combat_hud_protocol import validate_reticle_host
                require('reticle_host' in ack['combat_hud'], 'Missing production reticle host checkpoint')
                validate_reticle_host(ack['combat_hud']['reticle_host'], ack)
            if ability_progress:
                from uep_lyra_ability_progress_protocol import validate_progress
                require('ability_progress' in ack['combat_hud'], 'Missing ability progress checkpoint')
                validate_progress(ack['combat_hud']['ability_progress'], ack)
            if ability_failure:
                from uep_lyra_ability_failure_protocol import validate_failure
                require('ability_failure' in ack['combat_hud'], 'Missing ability failure checkpoint')
                validate_failure(ack['combat_hud']['ability_failure'], ack)
            if dash_cooldown:
                from uep_lyra_dash_protocol import validate_dash
                require('dash_cooldown' in ack['combat_hud'], 'Missing Dash checkpoint')
                validate_dash(ack['combat_hud']['dash_cooldown'], ack)
            if respawn_timer:
                from uep_lyra_respawn_protocol import validate_respawn
                require('respawn_timer' in ack['combat_hud'], 'Missing respawn checkpoint')
                validate_respawn(ack['combat_hud']['respawn_timer'], ack)
            if quickbar_slots:
                from uep_lyra_quickbar_protocol import validate_quickbar
                require('quickbar_slots' in ack['combat_hud'], 'Missing quickbar checkpoint')
                validate_quickbar(ack['combat_hud']['quickbar_slots'], ack)
            phase = row['phase']
            if packet['target'] != peer:
                require(all(before[key] == weapon[key] for key in ('magazine', 'spare', 'maximum', 'slot')),
                        'Other client ammo changed')
            elif phase.startswith('fire_') or phase == 'empty_b':
                aim = ack['aim_rotation']
                require(abs(aim['pitch'] - 80.0) < 0.001 and abs(aim['roll']) < 0.001,
                        'Firing aim must point up, not roll the camera')
                require(0 <= weapon['magazine'] < before['magazine'] and weapon['spare'] == before['spare'], 'No firing consumption')
                require(ack['input_frames'] > packet['statuses_before'][peer]['input_frames'], 'No native firing input')
                if phase == 'empty_b':
                    require(weapon['magazine'] == 0, 'No empty-magazine proof')
            elif phase.startswith('reload_'):
                require(weapon['magazine'] == weapon['maximum'] and weapon['magazine'] > before['magazine']
                        and weapon['spare'] < before['spare']
                        and weapon['magazine'] + weapon['spare'] == before['magazine'] + before['spare'], 'Reload failed')
            elif phase == 'switch_a':
                require(weapon['slot'] != before['slot'], 'No native weapon switch')
                require(ack['weapon_observer']['native_signals'] > packet['statuses_before'][peer]['weapon_observer']['native_signals'],
                        'Switch did not receive a native message')
        if row['phase'].startswith('travel_'):
            for peer in row['acks']:
                require(row['acks'][peer]['player']['world_token'] != packet['statuses_before'][peer]['player']['world_token'],
                        'World did not travel')
                require(row['acks'][peer]['weapon_observer']['unsubscribed'] > packet['statuses_before'][peer]['weapon_observer']['unsubscribed'],
                        'Travel did not detach old weapon observers')
        if row['phase'] == 'respawn_a':
            require(row['acks']['A']['player']['pawn_path'] != packet['statuses_before']['A']['player']['pawn_path'], 'No Pawn replacement')
    if debug_spread:
        require(any(ack['combat_hud']['debug_spread']['peak_angle'] > 0.01
                    for row in reports['server']['phases'] for ack in row['acks'].values()), 'No nonzero native weapon spread observed')
    if production_reticles:
        kinds = {ack['combat_hud']['production_reticle']['kind'] for row in reports['server']['phases'] for ack in row['acks'].values()}
        require({'Pistol', 'Rifle'} <= kinds, 'No native pistol/rifle production reticle switch')
    if nameplates:
        from uep_lyra_nameplate_protocol import validate_history as validate_nameplate_history
        validate_nameplate_history(reports)
    return {'status': 'passed', 'phase_count': len(PHASES), 'clients': 2, 'rejoin_tested': True,
            'real_fire_reload': True, 'blueprint_python_native_parity': True, 'sampling_source_declared': True,
            'combat_hud_acceptance': combat_hud, 'debug_spread_acceptance': debug_spread,
            'production_reticle_acceptance': production_reticles, 'reticle_host_acceptance': reticle_hosts,
            'ability_progress_acceptance': ability_progress,
            'ability_failure_acceptance': ability_failure,
            'dash_cooldown_acceptance': dash_cooldown,
            'respawn_timer_acceptance': respawn_timer,
            'quickbar_slots_acceptance': quickbar_slots,
            'nameplate_acceptance': nameplates,
            'native_interaction_producer_tested': False, 'replicated_duration_message_tested': False,
            'physical_touch_tested': False}
