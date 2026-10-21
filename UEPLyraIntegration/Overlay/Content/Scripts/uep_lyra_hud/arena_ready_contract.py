"""Actual Arena warmup/Cue and native Construct-driven animation playback."""
import argparse,json,math
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','phase_or_cue_callbacks_replayed','phase_timers_changed','python_animation_clock_added')

def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Arena ready observation failed')
    require(r['mode'] in ('Baseline','Python','BlueprintFallback'),'unknown Arena ready observation mode')
    for k in FALSE_FIELDS:require(r[k] is False,'Arena ready overclaim: '+k)
    require(r['owned_widgets_removed_and_roots_selectors_restored'],'Arena widget/selector/root cleanup differs')
    require(r['natural_cues'] and r['natural_widgets'] and r['owned_widgets'],'actual Arena Cue/widget/native construct missing')
    require(any(v['Warmup'] for v in r['phase_samples']) and any(v['Playing'] for v in r['phase_samples']),'original warmup/playing phase transition missing')
    for row in r['natural_cues']:
        counts=row['parent_policy_after'];require(row['not_rooted'] and counts is not None and counts['python_start']>=1 and counts['creates']>=1 and counts['adds']>=1 and counts['python_remove']>=1 and counts['removals']>=1,'real parent Cue widget creation/removal missing')
    for row in r['natural_widgets']+r['owned_widgets']:
        samples=[row['first']]+row['samples'];require(len(samples)>=3 and any(v['playing'] and v['forward'] and v['in_viewport'] for v in samples),'native visible forward animation missing')
        require(max(v['position'] for v in samples)>.2 and all(math.isfinite(v['position']) for v in samples),'native animation clock did not advance')
        if r['mode']!='Baseline':
            c=row['counts_after'];require(c['python_constructs']==int(r['mode']=='Python') and c['fallback_constructs']==int(r['mode']=='BlueprintFallback') and c['plays']==int(r['mode']=='Python'),'selected widget Construct Profile did not execute once')
    for row in r['natural_widgets']:require(row['removed_at_playing'] and not row['samples'][-1]['in_viewport'],'real Cue removal did not remove natural widget')
    for row in r['owned_widgets']:require(row['native_animation_finished'] and not row['samples'][-1]['playing'] and max(v['position'] for v in row['samples'])>=row['first']['animation_end']-.1,'owned full native animation did not finish')
    return dict(status='passed',mode=r['mode'],natural_cues=len(r['natural_cues']),natural_widgets=len(r['natural_widgets']),owned_widget_animations=len(r['owned_widgets']),full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
