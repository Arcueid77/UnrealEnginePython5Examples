"""Real Pawn collision transitions and retained native Timeline arbitration."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
STAGES=('one-enter','mixed','capture-one','empty','capture-two','final-empty')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native point-state run failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','overlap_callbacks_replayed','timeline_callbacks_replayed','pawn_arrays_written_by_fixture','health_properties_written','timeline_update_finish_rpc_vfx_audio_business_migrated'):require(r[k] is False,'point-state scope overclaim: '+k)
    require(r['natural_map_volumes']>0 and r['natural_map_python_ready']==r['natural_map_volumes'],'real map experience-ready initialization did not reach Python')
    require([x['profile'] for x in r['cases']]==list(PROFILES),'physical source/Python comparison incomplete')
    for row in r['cases']:
        require(row['ready_entries']==1 and abs(row['native_rate']-1.)<.0001,'native ready/register/rate differs')
        require([s['name'] for s in row['stages']]==list(STAGES),'physical scenario incomplete');a,b,c,d,e,f=row['stages']
        require(a['teams']==[1] and a['point_owner']==-1 and a['playing'],'single enemy did not start native capture')
        require(set(b['teams'])=={1,2} and b['point_owner']==-1 and b['reversing'],'mixed teams did not contest/reverse native clock')
        require(c['owner']==c['point_owner']==1 and c['teams']==[1],'natural forward completion did not capture team1')
        require(not d['pawns'] and d['owner']==d['point_owner']==1,'empty point did not preserve existing ownership')
        require(e['owner']==e['point_owner']==2 and e['teams']==[2],'enemy recapture did not reach native finish')
        require(not f['pawns'] and f['owner']==f['point_owner']==2 and row['final_enter_entries']>=3 and row['final_exit_entries']>=3,'real overlap enter/exit delivery or final owner differs')
    for k in ('owned_actors_destroyed','source_scoring_arrays_restored','original_health_unchanged','production_profiles_restored'):require(r[k] is True,'point-state cleanup absent: '+k)
    return dict(status='passed',physical_profile_scenarios=2,actual_overlap_stages=12,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
