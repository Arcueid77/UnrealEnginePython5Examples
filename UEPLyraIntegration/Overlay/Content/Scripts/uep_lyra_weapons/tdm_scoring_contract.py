"""Native TDM multi-output ABI, notifications, natural timers and real PostGame."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
COUNTDOWN_CASES=tuple((p,a,b,w) for p in PROFILES for a,b,w in ((4,4,0),(5,3,1),(2,6,2)))


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native TDM run failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callback_replayed','timer_callbacks_replayed','health_properties_written'):require(r[k] is False,'TDM scope overclaim: '+k)
    require(r['controlled_victory_receiver_used_for_decision_matrix'] is True,'controlled decision receiver must be explicit')
    require(r['natural_startup']['python_Begin']==1 and r['natural_startup']['python_GameStarted']==1,'natural experience/phase delegate did not run TDM Python startup')
    rows=r['query_cases'];require(Counter((x['profile'],x['score']) for x in rows)==Counter((p,s) for p in PROFILES for s in (14,15,16)),'score matrix incomplete')
    for x in rows:require(x['outputs']==[x['score'],15,x['score']==15] and x['native_target_notify_count']==1,'multi-output score/equality/target RepNotify differs')
    require(len(r['countdown_cases'])==6,'native countdown matrix incomplete')
    for x,case in zip(r['countdown_cases'],COUNTDOWN_CASES):require(x['profile']==case[0] and x['scores']==list(case[1:3]) and x['winners']==[case[3]] and x['notifications']==[1.,0.] and x['time']==0. and not x['timer_active'] and not x['handle_valid'] and x['gate_entries']==1 and x['cached_scores']==list(case[1:3]),'native timer/RepNotify/expiry decision differs')
    require(len(r['damage_cases'])==2 and all(x['after_apply']-x['initial_count']==1 and x['after_remove']==x['after_apply'] and x['fixture_effects_restored'] for x in r['damage_cases']),'actual original immunity apply/tag-removal behavior or fixture cleanup differs')
    require(len(r['cue_cases'])==2 and all(x['stored_tag'] and x['actual_manager_actors']==1 and x['cleared'] for x in r['cue_cases']),'actual looping message Cue add/remove differs')
    require(len(r['message_cases'])==4 and all(x['actual_winners']==[x['winner']] and x['team_scores'][x['winner']-1]==5 for x in r['message_cases']),'real elimination callback did not reach exact-score victory')
    require(len(r['restart_cases'])==2 and all(x['pawn_still_valid'] and x['entries']==1 for x in r['restart_cases']),'native RestartPlayer route differs')
    x=r['actual_victory'];require(x['winning_team']==2 and x['phase_active'] and x['cue_tag']=='GameplayCue.ShooterGame.UserMessage.MatchDecided' and x['manager_cue_count']==1 and x['python_victory_entries']>0,'actual native PostGame/Cue/victory integration differs')
    for k in ('owned_actors_destroyed','owned_components_destroyed','diagnostic_sender_root_removed','native_scores_restored','production_profiles_restored'):require(r[k] is True,'TDM cleanup absent: '+k)
    return dict(status='passed',native_query_cases=6,native_countdown_cases=6,real_elimination_cases=4,native_postgame_cases=1,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
