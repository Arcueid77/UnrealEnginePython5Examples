"""Default native cycle, inherited mode policy, real score messages and getter ABI."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
from uep_lyra_weapons.scoring_base_contract import CASES,EXPECTED
from .arena_phases_contract import validate as validate_cycle,validate_log
CLOCK=[(False,120.,0.),(True,-1.,0.),(True,0.,0.),(True,.5,.5),(True,60.,60.),(True,120.,120.)]
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['mode'] in ('Baseline','Python','BlueprintFallback'),'Arena mode validation failed');validate_cycle(r['cycle'])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','python_subscription_roots_added','native_proxy_cancelled_by_fixture','actual_round_properties_written'):
        require(r[k] is False,'Arena mode overclaim: '+k)
    require(r['cleanup_complete'] and r['scores_restored'] and r['owned_actors_destroyed'] and r['owned_component_destroyed'] and r['pause_restored'],'mode owned cleanup incomplete')
    require(len(r['natural_components'])==2 and r['natural_local_user_count']>=1 and r['natural_local_player_count']==r['natural_local_user_count'],'actual Arena family/local-user startup missing')
    if r['mode']!='Baseline':
        p='python_' if r['mode']=='Python' else 'fallback_';other='fallback_' if r['mode']=='Python' else 'python_'
        require(all(v['counts'][p+'begin']==1 and v['counts'][p+'ready']==1 and v['counts'][p+'warmup']>=1 and v['counts'][other+'begin']==0 for v in r['natural_components']),'static parent or base-owned startup gates missed')
        local=next(v for v in r['natural_components'] if v['class'].endswith('SpawnLocalPlayers_C'));require(local['counts'][p+'localbegin']==local['counts'][p+'localspawn']==1,'child startup/local-user gates missed')
    require(r['fixture_native_begin'] and r['fixture_native_message_proxies']==2,'owned native Begin did not create both typed listeners')
    rows=r['message_cases'];require([v['name'] for v in rows]==[c[0] for c in CASES],'native score message cases missing/reordered')
    recipients=r['scoring_recipients'];require(recipients==3,'original two native scorers plus one owned scorer expected')
    for row in rows:
        expected=[v//2*recipients for v in EXPECTED[row['name']]];require(row['delta']==expected,'score order/partial-cast/native message result differs: '+row['name'])
    require(len(r['clock_cases'])==len(CLOCK),'typed getter cases missing')
    for row,(playing,offset,expected) in zip(r['clock_cases'],CLOCK):require(row['playing'] is playing and row['offset']==offset and abs(row['remaining']-expected)<.0001,'named SecondsRemaining output/clamp differs')
    require(r['native_proxy_gi_refs_released'] and r['engine_gc_frames']>=3 and r['owned_fixture_started_phase_after_cycle_only'],'original message lifetime or fixture phase boundary differs')
    return dict(status='passed',mode=r['mode'],native_score_messages=len(rows),native_clock_cases=len(CLOCK),native_default_round_cycle=True,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);p.add_argument('--log',required=True);a=p.parse_args();result=validate(json.loads(Path(a.report).read_text(encoding='utf-8-sig')));validate_log(Path(a.log).read_text(encoding='utf-8-sig'));print(json.dumps(result))
