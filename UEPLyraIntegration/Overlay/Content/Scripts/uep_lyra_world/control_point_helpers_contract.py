"""Actual construction, counter activation and CP scoring helper evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require,close

PLAN=(([100.,70.,35.],5.),([20.,40.,6.],2.25),([-12.,8.,-2.],.75))


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native control point helper run failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','construction_replayed','overlap_replayed','timeline_callbacks_replayed','remaining_volume_business_migrated','health_properties_written'):require(r[k] is False,'volume helper scope overclaim: '+k)
    require(r['natural_map_volumes']>0 and r['natural_map_python_construction']>=r['natural_map_volumes'],'original CP map did not naturally construct Python volume helpers')
    require(len(r['pairs'])==3,'native construction matrix incomplete')
    for row,(area,duration) in zip(r['pairs'],PLAN):
        require(row['area']==area and row['constructor_entries']==[1,1] and row['paired_native_state_matches'],'actual natural constructor pair differs')
        require(row['fixture_niagara_scalability_disabled_and_solo'] is True,'fixture Niagara scalability/solo override must be explicit')
        for state in row['initial_states']:
            require(close(state['scale'],[a/10. for a in area]) and close(state['location'],[0.,0.,area[2]*5.+1.]),'source relative scale/height differs')
            require(close(state['offset'],[area[0]*5.,area[1]*5.,-area[0]*5.,-area[1]*5.]) and state['ribbon']==0. and abs(state['lifetime']-duration)<.0001,'actual Niagara initial values differ')
        require(row['counter_check_entries']==[2,2],'both native counter checks required')
        observations=row['counter_activation_observations'];require(len(observations)==2,'native activation reference missing')
        signatures=[]
        for x in observations:
            require(x['registered'] and x['system'] and not x['before'],'registered inactive fixture counter required')
            require(x['after_first']==x['after_second']==x['after_direct_native'],'helper state differs from direct native Activate in same fixture')
            signatures.append([x['after_first'],x['after_second'],x['after_direct_native']])
        require(signatures[0]==signatures[1],'original and Python activation outcomes differ')
        python=observations[1]['helper_evidence'];require(python['activations']==(1 if observations[1]['after_first'] else 2),'Python must activate only while inactive')
    require(any(x['after_first'] for row in r['pairs'] for x in row['counter_activation_observations']),'at least one actual active counter case required')
    require(len(r['helper_cases'])==6 and Counter(x['profile'] for x in r['helper_cases'])==Counter(BlueprintFallback=3,Python=3),'native scoring helper matrix incomplete')
    for x in r['helper_cases']:require(x['recaptured']==2 and x['contested']==-1 and x['recapture_entries']==x['contest_entries']==1,'actual CP scoring delegation differs')
    for k in ('owned_actors_destroyed','scoring_arrays_restored','original_health_unchanged','production_profiles_restored'):require(r[k] is True,'volume helper cleanup absent: '+k)
    return dict(status='passed',native_constructor_pairs=3,native_scoring_helper_cases=6,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
