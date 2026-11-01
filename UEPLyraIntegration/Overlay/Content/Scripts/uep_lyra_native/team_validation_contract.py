"""Real native component, policy edges, native team notifications, and restoration."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require

CASES=('tie','smaller','inactive','spectator','four_teams','empty')


def validate(r):
    require(r['status']=='passed' and r['error'] is None,'team runtime/finalizer failed')
    require(r['profile'] in ('Python','NativeFallback') and r['family'] in ('Two','Four'),'explicit team mode/family required')
    require(r['world_mode']=='Standalone' and r['natural_component_count']==1,'one natural team component required')
    require(len(r['configured_teams'])==(2 if r['family']=='Two' else 4),'actual original team map differs')
    counts=r['natural_team_counts'];require(max(counts.values())-min(counts.values())<=1,'natural startup assignment unbalanced')
    selected='python_' if r['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_'
    natural_minimum=4 if r['family']=='Two' else 1
    require(r['natural_metrics'][selected+'choose']>=natural_minimum and r['natural_metrics'][selected+'least']>=natural_minimum,'natural experience/player initialization bypassed policy')
    require(r['metrics'][other+'choose']==r['metrics'][other+'least']==0,'wrong team rule implementation executed')
    require([c['name'] for c in r['cases']]==list(CASES),'team branch coverage incomplete')
    first,second=sorted(int(k) for k in r['configured_teams'])[:2]
    third=r['four_team_ids'][2]
    require([c['least'] for c in r['cases']]==[first,second,first,None,third,-1],'native team selection differs')
    require([c.get('chosen') for c in r['cases']]==[first,second,first,-1,None,-1],'native assignment/spectator handling differs')
    require(r['cases'][3]['least_calls']==0,'spectator path queried population')
    require([c['events'] for c in r['cases']]==[
        [[0,-1,first]],[[1,-1,second]],[[2,-1,first]],[[0,second,-1]],[],[[3,second,-1]]], 'native team-change delegate sequence differs')
    require(all(r[k] for k in ('fixture_state_restored','team_configuration_restored','selectors_restored','observer_scope_closed')),'team fixture cleanup incomplete')
    require(not r['native_teams_or_experience_callbacks_replaced'],'native creation/lifecycle must remain')
    if r['family']=='Four':require(r['temporary_player_states_created']==3 and r['temporary_player_states_removed'],'native temporary PlayerState lifecycle incomplete')


def compare(native,python):
    validate(native);validate(python)
    require(native['profile']=='NativeFallback' and python['profile']=='Python' and native['family']==python['family'],'wrong team comparison pair')
    for key in ('cases','configured_teams','natural_team_counts'):
        require(native[key]==python[key],'native/Python team result differs: '+key)
    return dict(status='passed',family=native['family'],cases=len(CASES),native_setter_notifications_equal=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--python',type=Path,required=True);a=p.parse_args()
    print(json.dumps(compare(json.loads(a.native.read_text(encoding='utf-8-sig')),json.loads(a.python.read_text(encoding='utf-8-sig'))),indent=2))
