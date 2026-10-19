"""Real CP registration/capture/query/palette/timer and phase evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .hero_burst_cue_contract import require,close

PROFILES=('BlueprintFallback','Python')
TIMER_CASES=tuple((p,owners,w) for p in PROFILES for owners,w in (([1,2,-1],0),([1,1,2],1),([2,2,1],2)))


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native CP run failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callback_replayed','timer_callback_replayed','physical_capture_overlap_tested','health_properties_written'):require(r[k] is False,'CP scope overclaim: '+k)
    require(r['controlled_victory_receiver_for_intermediate_timer_cases'] is True,'controlled CP decision receiver must be explicit')
    require(r['natural_startup']['python_Begin']==1 and r['natural_startup']['python_GameStarted']==1 and r['actual_point_count']>0 and r['natural_startup']['python_Register']>0,'actual CP experience/startup/volume registration absent')
    require(len(r['array_cases'])==2,'array matrix incomplete')
    for x in r['array_cases']:require(x['point_count']==3 and x['initial']==[-1,-1,-1] and x['recaptured']==[2,-1,-1] and x['contested']==[-1,-1,-1],'source duplicate/first-index array semantics differ')
    require(len(r['capture_cases'])==2 and all(x['owners']==[2] and x['stat_deltas']==[0,2] and x['native_gate_entries']==1 for x in r['capture_cases']),'typed Pawn array capture/first-team/stat semantics differ')
    require(len(r['query_cases'])==12,'CP query matrix incomplete')
    for x in r['query_cases']:
        expected=([1,0,3] if x['team']==-1 else [1,1,2]) if x['kind']=='status' else [x['score'],5,x['score']>=5]
        require(x['outputs']==expected,'source CP query outputs differ')
    require(len(r['palette_cases'])==2,'palette matrix incomplete')
    for x in r['palette_cases']:require(x['index']==2 and x['cached_teams']==[7,8] and close(x['colors'],[[.2,.4,.6,.8],[.7,.5,.3,1.],[.2,.4,.6,.8]]),'source palette cache/assignment order differs')
    require(len(r['timer_cases'])==6,'native CP timer matrix incomplete')
    for x,case in zip(r['timer_cases'],TIMER_CASES):
        expected=case[2];require(x['ticks']==1 and not x['timer_active'] and not x['handle_valid'],'native scoring timer dispatch/cleanup differs')
        require(x['scores']==([0,0] if expected==0 else [1,0] if expected==1 else [0,1]) and x['leading']==(9 if expected==0 else expected) and x['winners']==([] if expected==0 else [expected]),'native majority/tie/leading/victory semantics differ')
    require(len(r['cue_cases'])==2 and all(x['manager_actor_count']==1 and x['cleared'] for x in r['cue_cases']),'CP message Cue manager integration differs')
    x=r['actual_victory'];require(x['winner']==2 and x['phase_active'] and x['manager_cue_count']==1 and not x['timer_active'] and not x['handle_valid'],'actual CP PostGame/Cue/stop-timer integration differs')
    for k in ('owned_actors_destroyed','owned_components_destroyed','native_scores_restored','production_profiles_restored'):require(r[k] is True,'CP cleanup absent: '+k)
    return dict(status='passed',native_capture_api_cases=2,native_query_cases=12,native_timer_cases=6,actual_cp_postgame_cases=1,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
