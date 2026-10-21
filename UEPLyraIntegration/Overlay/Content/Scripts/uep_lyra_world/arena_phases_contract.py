"""Require the original default-duration phase cycle and a real restarted round."""
import argparse,json,re
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
def phase_groups(events):
    groups=[]
    for event in events:
        if not groups or groups[-1][0]['phase']!=event['phase']:groups.append([])
        groups[-1].append(event)
    return groups
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['mode'] in ('Baseline','Python','BlueprintFallback'),'Arena natural phase cycle failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','callbacks_replayed','phases_started_by_fixture','round_properties_written','time_dilation_changed','native_delays_replaced','manual_travel_requested'):
        require(r[key] is False,'Arena phase overclaim: '+key)
    require(r['cleanup_complete'] and r['selectors_restored'] and r['all_classes_unrooted'],'phase observer cleanup incomplete')
    events=[e for e in r['events'] if e['method']=='K2_ActivateAbility' and e['stage']=='before'];groups=phase_groups(events);require([g[0]['phase'] for g in groups]==['warmup','playing','postgame','warmup'] and [len(g) for g in groups]==[2,1,2,2],'source concurrent phase groups/full restart missing')
    require(all(e['authority'] for e in events),'phase ability was not native authority')
    first,playing,post,restarted=[g[0] for g in groups];require(2.95<=playing['game_seconds']-first['game_seconds']<=3.5,'default3s warmup changed');require(119.8<=post['game_seconds']-playing['game_seconds']<=120.6,'default120s round changed')
    require(restarted['real_seconds']-post['real_seconds']>=9.9 and restarted['game_seconds']>=post['game_seconds']+9.9 and restarted['frame']>post['frame'],'default10s postgame and source seamless-travel clock continuity missing')
    require(r['last_postgame_seconds']>=post['game_seconds']+9.7,'natural postgame did not reach original native wait')
    require(r['default_durations']==dict(warmup=3.,postgame=10.,round=120.),'original phase/round defaults differ')
    require(r['warmup_effect_with_registered_handles_observed'] and r['playing_warmup_effect_removed'] and r['natural_ready_widget_seen'] and r['natural_ready_widget_removed'],'original global effect/Cue lifecycle missing')
    ends=[e for e in r['events'] if e['method']=='K2_OnEndAbility' and e['stage']=='after'];require(any(e['phase']=='warmup' for e in ends) and any(e['phase']=='playing' for e in ends),'native GAS phase cancellation/end callbacks missing')
    if r['mode']!='Baseline':
        prefix='python_' if r['mode']=='Python' else 'fallback_';other='fallback_' if r['mode']=='Python' else 'python_'
        for phase in ('warmup','playing','postgame'):
            row=next(e for e in r['events'] if e['phase']==phase and e['method']=='K2_ActivateAbility' and e['stage']=='after');require(row['counts'][prefix+'activate']==1 and row['counts'][other+'activate']==0,'selected natural phase Profile did not execute')
        resumed=[e for e in r['events'] if e['method']=='AfterWait' and e['stage']=='after'];require({e['phase'] for e in resumed}=={'warmup','postgame'} and all(e['counts'][prefix+'after']==1 for e in resumed),'original native Delay did not dispatch selected continuation Profile')
    return dict(status='passed',mode=r['mode'],natural_round_seconds=120.,warmup_seconds=3.,postgame_seconds=10.,native_restart=True,parallel_phase_counts=[len(g) for g in groups],full_acceptance=False)
def validate_log(text):
    require(re.search(r'(?s)UEP_ARENA_PHASES_ENTER postgame.*ProcessServerTravel:.*SeamlessTravel finished.*UEP_ARENA_PHASES_ENTER warmup',text) is not None,'native seamless travel did not finish before restarted warmup')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);p.add_argument('--log',required=True);args=p.parse_args();result=validate(json.loads(Path(args.report).read_text(encoding='utf-8-sig')));validate_log(Path(args.log).read_text(encoding='utf-8-sig'));print(json.dumps(result))
