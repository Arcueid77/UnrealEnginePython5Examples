"""Native shared scorer messages, exact channels, partial casts and real reset."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
CASES=(('enemy','Lyra.Elimination.Message','ps0','ps1'),('friendly','Lyra.Elimination.Message','ps0','ps0'),('null','Lyra.Elimination.Message','null','ps1'),('pawn-source','Lyra.Elimination.Message','pawn0','ps1'),('pawn-target','Lyra.Elimination.Message','ps0','pawn1'),('assist','Lyra.Assist.Message','ps0','null'),('assist-pawn','Lyra.Assist.Message','pawn0','ps1'),('wrong-channel','Lyra.Damage.Taken.Message','ps0','ps1'))
EXPECTED=dict(enemy=[2,0,0,0,2,0,2,0],friendly=[0]*8,null=[0]*8,**{'pawn-source':[0,0,0,0,0,0,2,0],'pawn-target':[2,0,0,0,0,0,2,0], 'assist':[0,0,2,0,0,0,0,0],'assist-pawn':[0]*8,'wrong-channel':[0]*8})


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','native scoring base run failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','python_subscription_roots_added','native_proxy_cancelled_by_fixture','health_properties_written'):require(report[k] is False,'scoring scope overclaim: '+k)
    require(report['natural_child_begin_python']==1 and report['natural_child_warmup_python']>=1,'real TDM parent startup/static call did not reach base-owned Python gates')
    rows=report['message_cases'];require(Counter((r['profile'],r['name']) for r in rows)==Counter((p,c[0]) for p in PROFILES for c in CASES),'paired scoring matrix incomplete')
    for row in rows:
        require(row['delta']==EXPECTED[row['name']],'native team/player score or partial-cast sequence differs: '+row['name'])
        callback=dict(elimination=int(row['name'] in ('enemy','friendly','null','pawn-source','pawn-target')),assist=int(row['name'] in ('assist','assist-pawn')))
        require(row['fixture_callbacks']==callback and row['real_child_callbacks']==callback,'native exact channel callback delivery differs')
    require(len(report['lifetime_cases'])==2 and all(r['native_proxies']==2 and r['gi_refs_released'] and r['engine_gc_frames']>=3 for r in report['lifetime_cases']),'source scoring proxy lifetime differs')
    require(len(report['warmup_cases'])==2 and all(r['spawner_available'] and r['grenade_destroyed'] and r['callback_entries']==1 for r in report['warmup_cases']),'native warmup cleanup differs')
    require(len(report['reset_cases'])==2 and all(r['old_pawn']!=r['new_pawn'] and r['health']>0 and r['death']==0 and r['native_asc_bound'] and r['callback_entries']==1+r['spawning_skip_calls'] for r in report['reset_cases']),'real native reset/ASC recovery differs')
    require(report['spawning_skip_cases'] and all(r['tag_present'] and r['same_pawn'] for r in report['spawning_skip_cases']),'original spawning-tag reset skip not verified')
    for k in ('owned_native_proxy_gi_refs_released','owned_actors_destroyed','owned_components_destroyed','diagnostic_sender_root_removed','actual_tdm_target_score_restored'):require(report[k] is True,'scoring cleanup absent: '+k)
    return dict(status='passed',native_message_cases=16,native_player_resets=2,native_warmup_cases=2,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
