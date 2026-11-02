"""Close the last six policies against their actual bounded native lifecycles."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO, SCRIPTS, load, sha, evidence, require

sys.path.insert(0, str(SCRIPTS))
from uep_lyra_native.rule_validation_contract import validate as runtime_gate
from uep_lyra_native.attribute_validation_contract import validate as attribute_gate
from uep_lyra_native.rule_network_contract import validate as network_gate
from uep_lyra_native.world_validation_contract import validate as world_gate
from uep_lyra_native.tag_stack_cost_network_contract import validate as prediction_gate


def closed(path):
    summary = load(path / 'summary.json')
    require(summary['status'] == 'passed' and summary.get('error') is None,
            'closed rule validation failed: ' + str(path))
    for row in summary.get('hashes', []):
        p = Path(row['path'])
        if p.is_relative_to(path / 'Inputs'):
            require(sha(p) == row['sha256'], 'archived rule input changed: ' + str(p))
    archived = path / 'Inputs/Overlay/Content/Scripts/uep_lyra_native/rule_policies.py'
    require(sha(archived) == sha(SCRIPTS / 'uep_lyra_native/rule_policies.py'),
            'accepted rule policy changed')
    return summary


def collect(root, output):
    root, output = root.resolve(), output.resolve()
    require(root.is_relative_to(REPO / '.build') and output.is_relative_to(REPO / 'Demos'),
            'owned rule evidence and ledger output required')
    work = root / '20261102-CPP19'
    build = load(work / 'Build02BodyRepair/summary.json')
    require(build['status'] == 'built_requires_native_acceptance' and build['error'] is None,
            'last-six native build failed')
    for row in build['products']:
        require(sha(Path(row['path'])) == row['sha256'], 'current rule binary changed')
    build_plan = load(work / 'Build02BodyRepair/Plan/plan.json')
    for row in build_plan['protected']:
        require(sha(Path(row['path'])) == row['sha256'], 'protected original/native input changed: ' + row['path'])
    closed(work / 'Boundaries02')
    boundary = load(work / 'Boundaries02/runtime.json')
    require(boundary['status'] == 'passed' and boundary['counts'] == dict(
        Device=56, Replay=132, Audio=52, Damage=256, Attribute=48, Pawn=56)
        and all(boundary[k] for k in ('int64_exact', 'trace_bounded',
            'unknown_operation_uses_native', 'roots_restored')), 'typed rule matrix failed')
    runs, raw = {}, {}
    names = ('DeviceNative03', 'DevicePython01', 'ReplayNative02', 'ReplayPython01',
             'AudioNative01', 'AudioPython01', 'DamageNative01', 'DamagePython01',
             'PawnNative01', 'PawnPython01', 'DefaultPawn01')
    for name in names:
        closed(work / name)
        raw[name] = load(work / name / 'runtime.json')
        runs[name] = runtime_gate(raw[name])
    require(raw['PawnNative01']['pawn'] == raw['PawnPython01']['pawn'],
            'actual native/Python Pawn data, classes or restart permissions differ')
    attributes = {}
    attribute_root = root / '20261102-CPP23'
    for name in ('AttributeNative02', 'AttributePython01', 'DefaultAttribute01'):
        closed(attribute_root / name)
        attributes[name] = attribute_gate(load(attribute_root / name / 'runtime.json'))
    networks = {}
    for family in ('Damage', 'Pawn'):
        path = work / (family + 'Network01')
        summary = closed(path)
        reports = {peer: load(path / 'rule' / (peer + '.json')) for peer in ('server', 'A', 'B0')}
        networks[family] = network_gate(reports, family)
        for peer in reports:
            require(summary['lanes']['rule']['processes'][peer]['exit_code'] == 0,
                    family + ' peer did not exit cleanly')
    closed(work / 'DefaultFrontend01')
    default_frontend = world_gate(load(work / 'DefaultFrontend01/runtime.json'))
    pistol_path = work / 'DefaultPistolNetwork01'
    pistol_summary = closed(pistol_path)
    pistol_reports = {peer: load(pistol_path / 'pistol' / (peer + '.json'))
                     for peer in ('server', 'A', 'B0')}
    prediction = prediction_gate(pistol_reports['server'],
                                {peer: pistol_reports[peer] for peer in ('A', 'B0')})
    for peer in pistol_reports:
        require(pistol_summary['weapons']['pistol']['processes'][peer]['exit_code'] == 0,
                'default original weapon peer did not exit cleanly')
    dependency = load(root / '20261102-CPP20/ReplayDependency02/summary.json')
    require(dependency['status'] == 'built_requires_native_acceptance' and dependency['error'] is None
            and dependency['engine_files_modified'] is False,
            'private current-engine replay dependency failed')
    for row in dependency['products']:
        require(sha(Path(row['path'])) == row['sha256'], 'private replay dependency changed')
    dependency_plan = load(root / '20261102-CPP20/ReplayDependency02/Plan/plan.json')
    for row in dependency_plan['protected']:
        require(sha(Path(row['path'])) == row['sha256'], 'original engine replay input changed')
    promotion = load(work / 'Assets02Promote/assets.json')
    require(promotion['status'] == 'passed' and promotion['new_defaults_enabled'],
            'last-six defaults not promoted')
    shared_evidence = [evidence(work / p) for p in (
        'Build02BodyRepair/summary.json', 'Boundaries02/summary.json',
        'Assets02Promote/summary.json', 'DefaultPawn01/summary.json',
        'DefaultFrontend01/summary.json', 'DefaultPistolNetwork01/summary.json')]
    shared_evidence.append(evidence(attribute_root / 'DefaultAttribute01/summary.json'))
    common = dict(schema_version=1, status='accepted', accepted=True,
                  target='UE5.8.1 / CPython3.11 / Win64 Development',
                  previous_blueprint_and_cpp_policies_retained=True,
                  engine_full_compile_executed=False, sdk_or_bridge_rebuild_executed=False,
                  cook_package_executed=False, physical_input_tested=False,
                  default_profile_promoted=True, cpp09_actual_window_stage_preserved=True,
                  protected_original_and_native_inputs_verified=len(build_plan['protected']),
                  default_offline_frontend=default_frontend,
                  compile_partition=dict(uht_modules=['LyraGame'],
                      lyra_compiled_units=[1, 2, 3], topdown_compiled_units=[1],
                      body_repair_reused_lyra_units=[1, 2], body_repair_reused_uht=True))
    def row(batch, candidate, cases, family, **details):
        return dict(common, batch=batch, candidates=[candidate], typed_boundary_cases=cases,
                    actual_native_and_python=[runs[family + p] for p in (
                        'Native03' if family == 'Device' else 'Native02' if family == 'Replay' else 'Native01',
                        'Python01')], evidence=shared_evidence + [
                            evidence(work / (family + p) / 'summary.json') for p in (
                                'Native03' if family == 'Device' else 'Native02' if family == 'Replay' else 'Native01',
                                'Python01')], **details)
    ledgers = {
        'CPP19': row('CPP19', 'CPP-025', 56, 'Device',
            native_device_connection_and_pairing_callback_inputs_supplied_by_fixture=True,
            unrelated_users_filtered_duplicate_ticker_coalesced_and_traits_restored=True,
            physical_device_disconnect_tested=False,
            retained_failed_fixture_attempts=['DeviceNative01/02 used widget.GetWorld, which the SDK did not expose. Ownership is now checked through the original native GetOwningPlayer.'],
            native_weak_ticker_dialog_delegate_lifetimes_retained=True),
        'CPP20': row('CPP20', 'CPP-026', 132, 'Replay',
            native_memory_retention_limits=[0, 1, 2, 5], temporary_streams_per_profile=16,
            actual_requery_delete_failure_stop_and_cleanup=True,
            keep_and_live_markers_checked_by_typed_context_only=True,
            invalid_negative_retention_rejected_before_delete_in_python=True,
            existing_user_recordings_touched=False, gameplay_replay_playback_tested=False,
            private_current_engine_module_compiled_sources=1,
            engine_module_manifest_and_binaries_unchanged=True,
            retained_failed_fixture_attempts=['ReplayNative01 found the old 5.8.0 memory-streamer DLL absent from the current 5.8.1 manifest; it was not loaded or registered. A private current-source module is compiled into the advancing stage only.','ReplayDependency01 compiled successfully but lacked NetworkReplayStreaming/Json import libraries. ReplayDependency02 reuses that object and relinks with those imports.'],
            private_dependency_evidence=evidence(root / '20261102-CPP20/ReplayDependency02/summary.json')),
        'CPP21': row('CPP21', 'CPP-027', 52, 'Audio',
            native_dynamic_range_and_loading_mix_calls_verified=True,
            readonly_mix_arrays_and_loading_state_guards_verified=True,
            audible_output_tested=False),
        'CPP22': row('CPP22', 'CPP-028', 256, 'Damage',
            actual_native_damage_effect_respects_enemy_and_friendly_rules=True,
            actual_authority_and_two_client_damage=networks['Damage'],
            default_original_weapon_prediction_damage_and_replication=prediction,
            native_damage_execution_gas_tags_and_replication_retained=True),
        'CPP23': dict(common, batch='CPP23', candidates=['CPP-029'], typed_boundary_cases=48,
            native_gas_clamp_and_two_local_player_input=attributes,
            base_values_written_by_fixture_and_restored_before_input=True,
            original_input_phase_kept_separate_from_attribute_mutation_fixture=True,
            retained_failed_fixture_attempts=['AttributeNative01 assumed a neutral character must return Unhandled. SceneViewport can return Handled with a zero headless extent; the private fixture now verifies no bomb or attribute change, then independently enters the real Enhanced Input action.'],
            evidence=shared_evidence + [evidence(attribute_root / (n + '/summary.json'))
                for n in ('AttributeNative02', 'AttributePython01')]),
        'CPP24': row('CPP24', 'CPP-030', 56, 'Pawn',
            actual_player_state_and_experience_pawn_data_and_permissions_verified=True,
            actual_authority_and_two_client_restart=networks['Pawn'],
            native_restart_lifecycle_asset_loading_and_spawn_ownership_retained=True)
    }
    ledgers['CPP22']['evidence'].append(evidence(work / 'DamageNetwork01/summary.json'))
    ledgers['CPP24']['evidence'].append(evidence(work / 'PawnNetwork01/summary.json'))
    for batch, ledger in ledgers.items():
        path = output / (batch + '-acceptance.json')
        require(not path.exists(), 'fresh rule acceptance ledger required')
        path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8', newline='\n')
    return dict(status='accepted', batches=list(ledgers), typed_boundary_cases=600,
                network_authority_trials=8, independent_client_views=16)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(collect(a.root, a.output), indent=2))
