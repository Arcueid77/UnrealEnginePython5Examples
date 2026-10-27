"""Verify the original visible/packaged weapon example, without broader visual claims."""
import ast
import re
from pathlib import Path

from audit_reload_cleanup_acceptance import (frozen, inspect as inspect_cleanup,
    log_gate, require, weapon_gate)
from audit_ui_navigation_acceptance import read, sha
from prepare_current_runtime_package import verify_rows

REQUIREMENT = ('A visible and packaged weapon/ammo example proves native signal plus read-only sampled '
               'change updates, safe subscription removal and native authority ownership.')
BASE = '.build/LyraValidation/BlueprintPython/20261028-weapon-example'
CALLS = {
    'weapon_observer': {'GetActiveSlotItem','GetOwningPlayer','GetStatTagStackCount'},
    'ammo_mixin': {'Conv_IntToText','FindFragmentByClass','GetDynamicMaterial','GetLocalPlayerSubsystem',
        'GetStatTagStackCount','InjectInputVectorForAction','SetBrush','SetScalarParameterValue',
        'SetText','SetTextureParameterValue','SetVisibility'},
}


def presenter_calls(sources):
    require(set(sources) == set(CALLS), 'Both production presenter/sampler modules required')
    result=[]
    for module,source in sorted(sources.items()):
        names=set()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):
                continue
            require(node.func.attr not in ('set_property','set_property_by_name','execute_console_command'),
                    'Unreviewed production native mutation path')
            if node.func.attr == 'call_function':
                require(node.args and isinstance(node.args[0],ast.Constant) and
                        isinstance(node.args[0].value,str), 'Dynamic native call needs explicit review')
                names.add(node.args[0].value)
        require(names == CALLS[module], 'Unreviewed native presenter call; authority writes are excluded')
        result.append(dict(module=module,native_functions=sorted(names)))
    return result


def package_identity(summary,payload,build):
    require(summary.get('status') == 'passed' and summary.get('packaged_runtime') is True and
            summary.get('cpp_compile_executed') is False and summary.get('cook_package_executed') is False,
            'Completed derived packaged runtime required')
    process=summary['process'];executable=Path(process['executable'])
    require(process['exit_code'] == 0 and process['pid'] > 0 and executable.name == 'LyraGame.exe' and
            executable.resolve() == Path(payload['packaged_executable']).resolve() and
            '-basedir='+str(executable.parent) in process['arguments'], 'Actual inner Game process identity differs')
    require(payload['status'] == 'passed' and payload['base_archive_unchanged'] is True and
            payload['reused_cooked_candidates'] == 246 and payload['reused_overlay_assets'] >= 460 and
            payload['reused_runtime_maps'] >= 12, 'Unchanged original cooked content proof absent')
    native,=[r for r in build['products'] if Path(r['path']).name == 'LyraGame.exe']
    require(build['status'] == 'passed' and build['no_engine_changes_requested'] is True and
            build['process']['exit_code'] == 0 and
            native['sha256'].upper() == payload['current_executable_sha256'].upper(),
            'Packaged executable is not the protected current-source Game build')


def visual_gate(document,expected):
    require(document.get('status') == 'reviewed' and document.get('pixel_diff_executed') is False and
            document.get('full_visual_acceptance') is False, 'Bounded direct image review required')
    require(document['images'] == expected and all(r['paired_ammo_text'] and r['three_counter_styles_visible'] and
            r['shader_preparation_overlay_absent'] for r in document['images']), 'Visible ammo/counter evidence incomplete')


def inspect(repo,current,initial):
    repo=Path(repo);root=repo/BASE
    cleanup=inspect_cleanup(repo,current,initial)
    # This rechecks the current-source native two-owner and callback protocol,
    # retaining its Editor-game configuration and original execution date.
    network=cleanup['runs'][1]
    require(network['protocol']['blueprint_python_native_parity'] is True and
            network['protocol']['sampling_source_declared'] is True, 'Native owner/replication parity absent')
    scripts=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts/uep_lyra_hud'
    calls=presenter_calls({m:(scripts/(m+'.py')).read_text(encoding='utf-8-sig') for m in CALLS})
    visible=root/'Visible01';summary=read(visible/'summary.json')
    require(summary['status'] == 'passed' and summary['process']['exit_code'] == 0 and
            '-RenderOffscreen' in summary['process']['arguments'], 'Rendered Editor comparison failed')
    count=frozen(summary,sha);weapon_gate(read(visible/'weapon.json'))
    log_gate((visible/'weapon.log').read_text(encoding='utf-8-sig'),
        'UEP_WEAPON_HUD_DIFFERENTIAL_PASSED','UEP_WEAPON_HUD_SHUTDOWN_PASSED')
    package=root/'Packaged01';packed=read(package/'summary.json');payload=read(package/'Payload/summary.json')
    build=read(root/'GameBuild01/summary.json')
    package_identity(packed,payload,build)
    build_log=(root/'GameBuild01/build.log').read_text(encoding='utf-8-sig')
    require(re.findall(r'\[\d+/\d+\]\s+(Compile|Link|WriteMetadata)',build_log) ==
            ['Compile','Compile','Compile','Link','WriteMetadata'] and 'Result: Succeeded' in build_log and
            not re.search(r'(?im)(?:error|warning) (?:C\d+|LNK\d+)',build_log), 'Actual incremental Game actions/diagnostics differ')
    require(Path(packed['process']['executable']).stat().st_size > 100_000_000, 'Bootstrap executable is insufficient')
    for rows in (packed['hashes'],payload['hashes'],payload['products'],build['hashes'],build['engine_inputs'],build['products']):
        verify_rows(rows)
    require(sha(packed['payload_summary']['path']) == packed['payload_summary']['sha256'].upper(), 'Prepared payload changed')
    weapon_gate(read(package/'weapon.json'))
    log_gate((package/'weapon.log').read_text(encoding='utf-8-sig'),
        'UEP_WEAPON_HUD_DIFFERENTIAL_PASSED','UEP_WEAPON_HUD_SHUTDOWN_PASSED')
    images=[]
    for name,folder,width,height in (('Editor',visible,1280,720),('Packaged',package,1440,900)):
        from struct import unpack
        path=folder/'weapon.png';header=path.read_bytes()[:24]
        require(header[:8] == b'\x89PNG\r\n\x1a\n' and unpack('>II',header[16:24]) == (width,height), 'Actual image dimensions differ')
        images.append(dict(runtime=name,path=path.relative_to(repo).as_posix(),sha256=sha(path),
            width=width,height=height,paired_ammo_text=True,three_counter_styles_visible=True,
            shader_preparation_overlay_absent=True))
    visual_gate(read(root/'visual-review.json'),images)
    runs=[]
    for name,folder,data in (('visible',visible,summary),('packaged',package,packed)):
        runs.append(dict(name=name,directory=folder.relative_to(repo).as_posix(),summary_sha256=sha(folder/'summary.json'),
            pid=data['process']['pid'],exit_code=0,report_sha256=sha(folder/'weapon.json'),log_sha256=sha(folder/'weapon.log')))
    return dict(status='passed',criterion=REQUIREMENT,completion_proven=True,runs=runs,
        visual_review_sha256=sha(root/'visual-review.json'),images=images,production_presenter_calls=calls,
        current_visible_frozen_inputs=count,current_packaged_executable_sha256=payload['current_executable_sha256'],
        current_game_build=dict(summary_sha256=sha(root/'GameBuild01/summary.json'),pid=build['process']['pid'],
            exit_code=0,compile_actions=3,link_actions=1,metadata_actions=1,duration_seconds=build['process']['duration_seconds']),
        payload_summary_sha256=sha(package/'Payload/summary.json'),
        current_project_python_files=next(r['current_python_files'] for r in payload['script_payloads'] if r['label']=='project'),
        current_core_python_files=next(r['current_python_files'] for r in payload['script_payloads'] if r['label']=='core'),
        reused_current_editor_network_proof=network,paired_state_comparisons_per_runtime=38,
        weapon_scenarios_per_runtime=42,controlled_new_widget_reload_cycles_per_runtime=3,
        native_gameplay_authority_retained=True,production_ammo_stat_writes=False,
        cpp_source_changed=False,cpp_compile_executed=True,cook_package_executed=False,
        full_regression_executed=False,full_migration_acceptance_proven=False,
        limits=['The package is an independent current Game/Python snapshot over byte-identical previously cooked assets; no fresh cook is claimed.',
                'Native owner/replication and live slot/possession signals reuse the nineteen-phase current-SDK Editor-game run; packaged networking is not claimed.',
                'Direct image review covers paired initial ammo text and three counter styles only; no pixel parity or every gameplay visual transition claim.',
                'Only the exact original visible/packaged weapon-example criterion is accepted; Batch1A visual and full candidate/Experience requirements remain separate.'])


def verify_documentation(document,current,initial,repo):
    require(document.get('criterion') == REQUIREMENT and document.get('completion_proven') is True,
            'Exact original visible/packaged weapon-example requirement required')
    expected=inspect(repo,current,initial)
    require(document.get('review') == expected, 'Recorded weapon example differs from source/runtime proof')
    return {k:expected[k] for k in ('status','criterion','current_packaged_executable_sha256',
        'paired_state_comparisons_per_runtime','weapon_scenarios_per_runtime','native_gameplay_authority_retained')}
