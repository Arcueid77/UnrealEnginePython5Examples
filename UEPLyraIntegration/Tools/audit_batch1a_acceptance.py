"""Recheck five directly reviewed BP/Python views over the native weapon protocol."""
from pathlib import Path
import sys

from audit_reload_cleanup_acceptance import frozen, log_gate, require
from audit_ui_navigation_acceptance import read, sha

REQUIREMENT = ('Batch 1A has original-BP/Python state and visual comparisons for weapon switching, '
    'firing, reload, empty ammo and Pawn replacement. One server and two clients prove that '
    'ammo/UI state never crosses local-player ownership.')
BASE = '.build/LyraValidation/BlueprintPython/20261028-batch1a-visual'


def native_matches(reports, visuals):
    for peer, visual in visuals.items():
        phases={r['phase']:r for r in reports[peer]['phases']}
        for capture in visual['captures']:
            ack=phases[capture['phase']]['ack']
            require(capture['native'] == ack['weapon'] and capture['controller'] == ack['player']['controller_path'] and
                    capture['pawn'] == ack['player']['pawn_path'] and capture['world'] == ack['player']['world_token'] and
                    capture['player_id'] == ack['player']['player_id'] and
                    capture['production_widget'] == ack['weapon_hud']['widget'],
                    'Visual pair crossed actual native player/item/production-widget identity')


def inspect(repo,current,initial):
    repo=Path(repo);root=repo/BASE;folder=root/'Native02/Network'
    require(len(current['assets']) == 246 and [(r['path'],r['version']) for r in current['assets']] ==
            [(r['path'],r['version']) for r in initial['assets']], 'Original migration scope changed')
    summary=read(folder/'summary.json')
    require(summary['status'] == 'passed' and summary['error'] is None and not summary['cpp_compile_executed'] and
            not summary['cook_package_executed'] and not summary['combat_hud'], 'Completed focused native weapon run required')
    count=frozen(summary,sha)
    processes=summary['processes']
    require(set(processes) == {'server','A','B0','B1'} and len({p['pid'] for p in processes.values()}) == 4 and
            all(p['pid'] > 0 and p['exit_code'] == 0 for p in processes.values()), 'Four actual completed native peers required')
    scripts=repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts'
    sys.path.insert(0,str(scripts))
    from uep_lyra_weapon_protocol import validate_reports
    from uep_lyra_batch1a_visual_contract import validate
    reports={p:read(folder/(p+'.json')) for p in ('server','A','B0','B1')}
    visuals={p:read(folder/('batch1a-'+p+'.json')) for p in ('server','A','B0','B1')}
    protocol=validate_reports(reports,summary['run_id'])
    require(protocol == summary['protocol_validation'] and protocol['phase_count'] == 19 and
            protocol['blueprint_python_native_parity'] and protocol['rejoin_tested'], 'Native owner/protocol proof differs')
    visual=validate(visuals,summary['run_id']);native_matches(reports,visuals)
    a={r['phase']:r for r in visuals['A']['captures']}
    require(a['fire_a']['pawn'] != a['respawn_a']['pawn'] and a['fire_a']['definition'] != a['switch_a']['definition'] and
            a['fire_a']['native']['magazine'] < a['reload_a']['native']['magazine'] and
            visuals['B0']['captures'][0]['native']['magazine'] == 0, 'Actual fire/reload/switch/empty/Pawn transitions missing')
    control=root/'Native02/control-provenance.json';provenance=read(control)
    for row in (provenance['original'],provenance['derived']):require(sha(row['path']) == row['sha256'].upper(), 'Frozen derived network control changed')
    original=Path(provenance['original']['path']).read_bytes().decode('utf-8-sig')
    anchor="$arguments+='-UEPLyraWeaponNetwork'"
    require(original.count(anchor) == 1, 'Network control injection anchor changed')
    derived=original.replace('$PSScriptRoot',"'"+str(repo/'Validation').replace("'","''")+"'")
    derived=derived.replace(anchor,anchor+"\n        $arguments+=@('-UEPLyraBatch1AVisual','-ini:Engine:[Python]:ImportModules=uep_lyra_batch1a_visual')")
    derived=derived.replace("'-ResX=640','-ResY=360'","'-ResX=1280','-ResY=720'")
    require(Path(provenance['derived']['path']).read_bytes() == derived.encode('utf-8'), 'Undeclared change to existing native producer control')
    source=scripts/'uep_lyra_batch1a_visual.py'
    source_text=source.read_bytes().decode('utf-8-sig')
    require(all(s not in source_text for s in ('AddStatTagStack','RemoveStatTagStack','SetActiveSlotIndex','ForceNetUpdate')),
            'Visual adapter gained gameplay-state writes')
    previous=root/'Native01';partial=read(previous/'visual-review.json')
    require(partial['status'] == 'partial_visual_capture_requires_relayout' and not partial['original_requirement_accepted'],
            'Keep the first partially obscured visual result unaccepted')
    archives=read(previous/'source-archives.json');require(len(archives) == 2, 'Both retired source copies must remain')
    for row in archives:
        require(sha(row['archive']) == row['sha256'].upper(), 'Retired exact visual adapter bytes changed')
        expected=Path(row['archive']).read_bytes().decode('utf-8-sig').replace(
            'X=130.0+column*610.0','X=850.0+column*400.0').replace('self.pair(controller,PANEL,220,panel=True)',
            'self.pair(controller,PANEL,500,panel=True)').replace('self.pair(controller,path,350)','self.pair(controller,path,660)')
        require(source_text == expected, 'Recapture changed more than test-only UI coordinates')
    for row in partial['images']:require(sha(row['path']) == row['sha256'].upper(), 'First raw image changed')
    reviewed=read(root/'visual-review.json')
    require(reviewed['status'] == 'reviewed' and reviewed['whole_frame_pixel_diff'] is False and
            reviewed['audio_acceptance'] is False and len(reviewed['images']) == 5, 'Five direct component image reviews required')
    images=[]
    from struct import unpack
    for row,review in zip(visual['images'],reviewed['images']):
        path=Path(row['path']);header=path.read_bytes()[:24]
        require(path.resolve().parent == folder.resolve() and path.name == 'batch1a-'+row['peer']+'-'+row['phase']+'.png' and
                header[:8] == b'\x89PNG\r\n\x1a\n' and unpack('>II',header[16:24]) == (1280,720), 'Actual native visual file differs')
        require(review['peer'] == row['peer'] and review['phase'] == row['phase'] and review['sha256'] == sha(path) and
                all(review[k] is True for k in ('paired_ammo_visible','paired_counter_visible','component_values_agree')),
                'Recorded image review lacks clear paired presenters')
        images.append(dict(peer=row['peer'],phase=row['phase'],path=path.relative_to(repo).as_posix(),sha256=sha(path)))
    peers=[]
    for peer,process in sorted(processes.items()):
        require('-UEPLyraBatch1AVisual' in process['arguments'] and '-ini:Engine:[Python]:ImportModules=uep_lyra_batch1a_visual' in process['arguments'],
                'Visual hook was not explicitly enabled')
        log_gate((folder/(peer+'.log')).read_text(encoding='utf-8-sig'),'Goodbye Python','UEP_LYRA_HUD_SHUTDOWN_PASSED')
        peers.append(dict(peer=peer,pid=process['pid'],exit_code=0,report_sha256=sha(folder/(peer+'.json')),
            visual_report_sha256=sha(folder/('batch1a-'+peer+'.json')),log_sha256=sha(folder/(peer+'.log')),
            visual_widgets_created=visuals[peer]['widgets_created'],visual_widgets_closed=visuals[peer]['widgets_closed']))
    return dict(status='passed',criterion=REQUIREMENT,completion_proven=True,directory=folder.relative_to(repo).as_posix(),
        summary_sha256=sha(folder/'summary.json'),current_frozen_input_records=count,native_peers=peers,
        native_protocol=protocol,visual_checkpoint_pairs=5,images=images,visual_review_sha256=sha(root/'visual-review.json'),
        control_provenance_sha256=sha(control),preserved_partial_visual_review_sha256=sha(previous/'visual-review.json'),
        exact_retired_source_archives_sha256=sha(previous/'source-archives.json'),production_policy_or_assets_changed=False,
        cpp_compile_executed=False,cook_package_executed=False,full_regression_executed=False,full_migration_acceptance_proven=False,
        limits=['Compare test-owned original-BP-left/Python-right panels and active counter style over actual local native weapon state.',
                'Keep the real shipped production HUD and the unchanged nineteen-phase native input/server/replication producer.',
                'Direct review covers five component checkpoints;no whole-frame pixel equality,hardware input or audio acceptance is claimed.',
                'NoSound TapIDs warnings remain in native logs. The first obscured capture remains unaccepted and exact source bytes are archived.',
                'Accept only the exact original Batch1A requirement. Candidate,RC and full two-Experience requirements stay separate.'])


def verify_documentation(document,current,initial,repo):
    require(document.get('criterion') == REQUIREMENT and document.get('completion_proven') is True,'Exact original Batch1A requirement required')
    expected=inspect(repo,current,initial)
    require(document.get('review') == expected,'Recorded Batch1A evidence differs')
    return {k:expected[k] for k in ('status','criterion','visual_checkpoint_pairs','summary_sha256')}
