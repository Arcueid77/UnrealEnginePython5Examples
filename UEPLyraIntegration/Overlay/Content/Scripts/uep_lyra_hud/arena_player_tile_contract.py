"""Native Configure, team broadcast, replacement and child payload parity."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
COLORS={1:[1.,.1,.1,1.],2:[.1,.1,1.,1.],3:[.1,1.,.1,1.],4:[1.,1.,.1,1.]}
PLAN=['initial-configure','team-1','team-2','team-3','team-4','repeat-configure','unset-monitor','old-target-change','restore-configure']
def near(a,b):return len(a)==len(b) and all(abs(x-y)<.00001 for x,y in zip(a,b))
def selected(counts,mode):
    prefix='python_' if mode=='Python' else 'fallback_';other='fallback_' if mode=='Python' else 'python_'
    if mode!='Baseline':
        require(counts[prefix+'configure']>=1 and counts[prefix+'monitor']>=1 and counts[prefix+'team']>=1,'selected tile Profile missed native dispatch')
        require(all(counts[other+k]==0 for k in ('configure','monitor','team')),'wrong tile Profile executed')
def payload(row):
    require(row['name']==row['expected_name'] and row['proxy_active'],'native name/observer mismatch')
    require([v['attribute'] for v in row['stats']]==['BombsRemaining','BombRange','MovementSpeed'],'original child attribute literals differ')
    require(all(v['target']==row['expected_target'] for v in row['stats']),'child stat target differs from actual PlayerState')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['mode'] in ('Baseline','Python','BlueprintFallback'),'Arena tile observation failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','team_callbacks_replayed','native_delegate_broadcast_by_fixture','child_stat_business_migrated'):
        require(r[key] is False,'Arena tile overclaim: '+key)
    require(r['cleanup_complete'] and r['team_restored'] and r['typed_bp_caller'] and r['natural_tiles'],'native UI/owned cleanup or team restoration missing')
    for row in r['natural_tiles']:
        payload(row);selected(row['counts'],r['mode']);require(row['visible'] and row['native_owner'] and near(row['tint'],COLORS[row['team']]),'actual Arena tile color/visibility differs')
    cases=r['cases'];require([v['case'] for v in cases]==PLAN,'native tile cases missing/reordered')
    for row in cases:payload(row);selected(row['counts'],r['mode'])
    for row in [cases[0]]+cases[1:6]+[cases[-1]]:require(near(row['tint'],COLORS[row['team']]),'original team color differs')
    require(cases[5]['previous_proxy_cancelled'] and cases[5]['replacement_distinct'],'repeat Configure did not replace old native observer')
    require(cases[6]['previous_proxy_cancelled'] and cases[6]['observed_team']==-1 and near(cases[6]['tint'],cases[5]['tint']),'unset native team event changed tint or retained old listener')
    require(cases[7]['old_target_really_changed_team'] and cases[7]['callback_count_unchanged'] and near(cases[7]['tint'],cases[6]['tint']),'cancelled old target still changed tile')
    if r['mode']!='Baseline':
        prefix='python_' if r['mode']=='Python' else 'fallback_';require(cases[-1]['counts'][prefix+'configure']==3 and cases[-1]['counts'][prefix+'monitor']==4,'native Configure/Monitor call count differs')
        require(cases[6]['counts']['payloads'][-1]==[False,-1],'unset native observer payload missing')
    require(r['owned_observers_cancelled'] and r['owned_widget_removed'],'owned native widget/observer cleanup missing')
    return dict(status='passed',mode=r['mode'],natural_tiles=len(r['natural_tiles']),native_cases=len(cases),full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
