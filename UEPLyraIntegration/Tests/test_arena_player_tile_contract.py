import copy,unittest
from uep_lyra_hud.arena_player_tile_contract import COLORS,PLAN,validate

def report(mode='Python'):
    counts={p+k:0 for p in ('python_','fallback_') for k in ('configure','monitor','team')};counts['payloads']=[[False,-1]]
    if mode!='Baseline':
        p='python_' if mode=='Python' else 'fallback_';counts.update({p+'configure':3,p+'monitor':4,p+'team':6})
    row=dict(name='Player',expected_name='Player',expected_target='PS0',proxy_active=True,stats=[dict(attribute=a,target='PS0') for a in ('BombsRemaining','BombRange','MovementSpeed')],counts=counts,team=4,tint=COLORS[4],visible=True,native_owner='PlayerController0',native_parent='NativeDynamicEntryBox')
    cases=[]
    for name in PLAN:
        c=copy.deepcopy(row);c['case']=name
        if name.startswith('team-'):c['team']=int(name[-1]);c['tint']=COLORS[c['team']]
        if name in ('repeat-configure','unset-monitor'):c.update(previous_proxy_cancelled=True,replacement_distinct=True,observed_team=-1)
        if name=='old-target-change':c.update(old_target_really_changed_team=True,callback_count_unchanged=True)
        cases.append(c)
    return dict(status='passed',error=None,mode=mode,full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,team_callbacks_replayed=False,native_delegate_broadcast_by_fixture=False,child_stat_business_migrated=False,cleanup_complete=True,team_restored=True,typed_bp_caller=True,natural_tiles=[row],cases=cases,owned_observers_cancelled=True,owned_widget_removed=True)

class ArenaPlayerTileContractTests(unittest.TestCase):
    def test_baseline_and_both_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertEqual(validate(report(mode))['native_cases'],9)
    def test_unset_team_must_preserve_previous_tint(self):
        r=report();r['cases'][6]['tint']=COLORS[1]
        with self.assertRaises(RuntimeError):validate(r)
    def test_old_target_stale_callback_or_live_previous_proxy_rejected(self):
        for index,key in ((5,'previous_proxy_cancelled'),(7,'callback_count_unchanged')):
            r=report();r['cases'][index][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_native_child_payload_color_or_profile_rejected(self):
        for mutation in ('attribute','tint','profile'):
            r=report()
            if mutation=='attribute':r['cases'][0]['stats'][0]['attribute']='BombRange'
            elif mutation=='tint':r['cases'][2]['tint']=COLORS[1]
            else:r['cases'][0]['counts']['fallback_configure']=1
            with self.subTest(mutation=mutation),self.assertRaises(RuntimeError):validate(r)
    def test_replay_missing_case_or_unrestored_team_rejected(self):
        for key in ('team_callbacks_replayed','team_restored'):
            r=report();r[key]=not r[key]
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
