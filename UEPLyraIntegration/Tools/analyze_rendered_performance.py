"""Independent closed native CSV/process CPU gate and paired comparison."""
import argparse
import csv
import itertools
import json
import math
from pathlib import Path
import statistics
from collect_native_message_acceptance import REPO, load, sha, evidence, require


def percentile(values, quantile):
    values = sorted(values)
    return values[min(len(values)-1, math.ceil(quantile*len(values))-1)]


def frames(path):
    with path.open(encoding='utf-8-sig', newline='') as source:
        rows = list(csv.reader(source))
    headers = [(i, row) for i, row in enumerate(rows) if 'FrameTime' in row and 'GameThreadTime' in row]
    require(bool(headers), 'native profiler header missing')
    header_index, first_header = headers[0]
    header = headers[-1][1]
    # The native writer discovers extra counters while capturing and emits
    # the complete header again at the end (HasHeaderRowAtEnd=1). Existing
    # column positions remain stable; early rows omit only later counters.
    require(header[:len(first_header)] == first_header, 'native CSV reordered existing counters')
    required = ('FrameTime', 'GameThreadTime', 'RenderThreadTime', 'GPUTime')
    require(all(header.count(key) == 1 for key in required), 'unambiguous actual native frame/thread/GPU columns required')
    indices = {key: header.index(key) for key in required}
    data = []
    for row in rows[header_index+1:]:
        if not max(indices.values()) < len(row) <= len(header):
            continue
        try:
            value = {key: float(row[index]) for key, index in indices.items()}
        except ValueError:
            continue
        if value['FrameTime'] > 0:
            require(all(math.isfinite(v) and v >= 0 for v in value.values()), 'invalid native profiler sample')
            data.append(value)
    require(len(data) >= 14, 'native rendered frame sample is too short')
    raw_count = len(data)
    data = data[2:-2]  # Capture commands straddle frame boundaries, outside inference.
    require(statistics.median(row['GPUTime'] for row in data) > .01 and
            statistics.median(row['RenderThreadTime'] for row in data) > .01, 'GPU rendering was absent or skipped')
    return data, raw_count


def frame_stats(data):
    times = [r['FrameTime'] for r in data]
    worst = sorted(times, reverse=True)[:max(1, math.ceil(len(times)*.01))]
    return dict(frames=len(times), fps=1000/statistics.mean(times), one_percent_low_fps=1000/statistics.mean(worst),
        mean_frame_ms=statistics.mean(times), p95_frame_ms=percentile(times, .95), p99_frame_ms=percentile(times, .99),
        mean_game_thread_ms=statistics.mean(r['GameThreadTime'] for r in data),
        mean_render_thread_ms=statistics.mean(r['RenderThreadTime'] for r in data),
        mean_gpu_ms=statistics.mean(r['GPUTime'] for r in data))


def paired_interval(values):
    # Four independent AB/BA block pairs, not thousands of correlated frames.
    means = [statistics.mean(v) for v in itertools.product(values, repeat=len(values))]
    return dict(pairs=len(values), paired_mean=statistics.mean(values), bootstrap_95_low=percentile(means, .025),
                bootstrap_95_high=percentile(means, .975), values=values,
                inference='descriptive paired block bootstrap; small local sample, not a universal confidence guarantee')


def analyze(directory):
    directory = directory.resolve()
    require(directory.is_relative_to(REPO/'.build'), 'owned closed rendered evidence required')
    summary, report = load(directory/'summary.json'), load(directory/'runtime.json')
    require(summary['status'] == report['status'] == 'passed' and summary['error'] is None and report['error'] is None and
            summary['process']['exit_code'] == 0 and report['selector_restored'], 'native rendered process did not close cleanly')
    require(summary['loaded_python']['inside_package'] and summary['loaded_python']['actual_loaded_module'], 'actual packaged CPython missing')
    for row in summary['hashes']:
        require(sha(Path(row['path'])) == row['sha256'], 'frozen native rendered input changed: '+row['path'])
    require(report['viewport'] == [1920, 1080] and report['blueprint_layer_fixed'] == 'Python' and
            report['actual_rendering_requested'] and not report['physical_input_tested'], 'comparison scene/render/scope differs')
    log = (directory/'runtime.log').read_text(encoding='utf-8-sig')
    require('Using Forced RHI: D3D12' in log and 'NVIDIA GeForce RTX 3080' in log and
            'UEP_RENDERED_PERFORMANCE_SHUTDOWN_PASSED' in log, 'hardware rendering or native shutdown missing')
    require(all(not row['running'] for row in report['bot_isolation']) and len(report['bot_isolation']) == 3, 'three stable isolated bots required')
    pilot = report['pilot']
    expected_order = ('Native', 'Python', 'Python', 'Native') if pilot else ('Native', 'Python', 'Python', 'Native', 'Python', 'Native', 'Native', 'Python')
    workloads = ('Scene',) if pilot else ('Scene', 'RuleStress')
    require([(r['workload'], r['profile']) for r in report['blocks']] == [(w, p) for w in workloads for p in expected_order], 'balanced paired profile matrix missing')
    blocks, sources, raw_frames = [], [], {}
    for row in report['blocks']:
        require(row['selected_profile'] == ('NativeGameplayFallback' if row['profile'] == 'Native' else 'Python') and
                row['settings'] == report['settings'] and row['owner_pawn_unchanged'], 'profile/settings/fixed pawn drifted')
        require(row['wall_seconds'] >= report['capture_seconds'] and row['wall_seconds'] < report['capture_seconds']+2 and
                row['frames'] >= (10 if pilot else 100), 'measured block duration/frame population invalid')
        require(row['requests_per_frame'] == (0 if row['workload'] == 'Scene' else 200) and
                row['query_pairs']*2 == row['requests_per_frame']*row['frames'], 'fixed per-frame native query workload differs')
        before, after = row['before_counters'], row['after_counters']
        if row['profile'] == 'Native':
            require(after['native_admissions'] > before['native_admissions'] and
                    after['rule_applications'] == before['rule_applications'] and after['camera_choices'] == before['camera_choices'], 'native fallback did not own the measured world route')
        else:
            require(after['camera_choices'] > before['camera_choices'] and
                    after['rule_applications']-before['rule_applications'] >= row['query_pairs'], 'Python world rules did not drive actual measured callbacks')
        path = directory/'Captures'/row['csv_basename']
        data, count = frames(path)
        require(abs(count-row['frames']) <= 6, 'native CSV and independent ticker frame counts disagree')
        result = frame_stats(data)
        cpu = 100*row['process_cpu_seconds']/row['wall_seconds']/report['logical_processors']
        require(0 <= cpu <= 100 and abs(cpu-row['cpu_machine_percent']) < 1e-6, 'Windows process CPU arithmetic differs')
        samples = [r for r in summary['os_samples'] if row['started_unix_ms'] <= r['unix_ms'] <= row['ended_unix_ms']]
        require(len(samples) >= 3, 'independent OS CPU samples missing inside the actual block')
        first, last = samples[0], samples[-1]
        os_cpu = 100*(last['cpu_seconds']-first['cpu_seconds'])/((last['unix_ms']-first['unix_ms'])/1000)/report['logical_processors']
        require(abs(os_cpu-cpu) <= max(5., cpu*.3), 'independent Windows CPU observation contradicts runtime CPU')
        result.update(index=row['index'], workload=row['workload'], profile=row['profile'], cpu_machine_percent=cpu,
            cpu_one_core_equivalent_percent=cpu*report['logical_processors'], independent_os_cpu_machine_percent=os_cpu,
            process_cpu_seconds=row['process_cpu_seconds'], ticker_frames=row['frames'],
            process_cpu_ms_per_frame=1000*row['process_cpu_seconds']/row['frames'],
            requests_per_frame=row['requests_per_frame'], query_pairs=row['query_pairs'], wall_seconds=row['wall_seconds'])
        blocks.append(result)
        raw_frames[row['index']] = data
        sources.append(evidence(path))
    comparisons = {}
    for workload in workloads:
        subset = [r for r in blocks if r['workload'] == workload]
        sides = {}
        for profile in ('Native', 'Python'):
            selected = [r for r in subset if r['profile'] == profile]
            sides[profile] = frame_stats([f for r in selected for f in raw_frames[r['index']]])
            sides[profile]['cpu_machine_percent'] = sum(r['cpu_machine_percent']*r['wall_seconds'] for r in selected)/sum(r['wall_seconds'] for r in selected)
            sides[profile]['process_cpu_ms_per_frame'] = 1000*sum(r['process_cpu_seconds'] for r in selected)/sum(r['ticker_frames'] for r in selected)
        deltas = {'fps_percent': [], 'cpu_percentage_points': [], 'game_thread_ms': []}
        for i in range(0, len(subset), 2):
            pair = {r['profile']: r for r in subset[i:i+2]}
            n, p = pair['Native'], pair['Python']
            deltas['fps_percent'].append(100*(p['fps']/n['fps']-1))
            deltas['cpu_percentage_points'].append(p['cpu_machine_percent']-n['cpu_machine_percent'])
            deltas['game_thread_ms'].append(p['mean_game_thread_ms']-n['mean_game_thread_ms'])
        comparisons[workload] = dict(native=sides['Native'], python=sides['Python'], paired={k: paired_interval(v) for k, v in deltas.items()})
    return dict(schema_version=1, status='passed' if pilot else 'accepted', group='H05', pilot=pilot,
        analysis_tool=evidence(Path(__file__)),
        comparison_scope=report['comparison_scope'], hardware=summary['hardware'], settings=report['settings'], viewport=report['viewport'],
        successful_native_process=True, actual_D3D12_GPU_frames_verified=True, logical_processors=report['logical_processors'],
        cpu_normalization='process user+kernel CPU time / elapsed wall time / 16 logical processors; 0-100 percent of whole machine',
        fps_definition='1000 / mean native CSV frame time; two frames trimmed at each capture boundary',
        one_percent_low_definition='1000 / mean slowest ceil(1 percent) native frame times',
        source_engine_or_original_project_modified=False, cpp_compile_executed=False, cook_package_executed=False, physical_input_tested=False,
        normal_scene_is_fixed_noncombat=True, other_blueprint_and_native_mixin_implementations_fixed=True,
        stress_scope='200 additional reflected native Damage/Pawn queries per frame; a synthetic stress workload, not normal player activity',
        universal_fps_or_full_game_migration_performance_claimed=False, blocks=blocks, comparisons=comparisons,
        evidence=[evidence(directory/'summary.json'), evidence(directory/'runtime.json')]+sources)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'fresh independent frame/CPU analysis required')
    result = analyze(args.directory)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: result[k] for k in ('status', 'pilot', 'comparisons')}))
