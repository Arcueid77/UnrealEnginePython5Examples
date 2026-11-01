"""Gate the native callback fixture separately from actual damage/network proof."""
import argparse
import json
from pathlib import Path

KINDS=('streak','chain','assist')
PHASES=('initial','before','equal','after')


def require(value,message):
    if not value:raise AssertionError(message)


def validate(report):
    require(report['status']=='passed' and report['error'] is None,'runtime/finalizer failed')
    require(report['profile'] in ('Python','NativeFallback'),'unsupported profile')
    require([p['name'] for p in report['phases']]==list(PHASES),'boundary phases incomplete')
    require(report['world_mode']=='Standalone' and report['synthetic_native_messages'],'explicit fixture scope required')
    require(not report['actual_damage_or_network_acceptance'],'message fixture cannot certify real damage/network')
    require(report['nested_damage_sent'],'nested assist broadcast not exercised')
    require(report['scope_closed'] and report['callbacks_after_destroy']==0,'native callback cleanup failed')
    require(report['selectors_restored'] and report['profiles_restored'],'profile cleanup failed')
    require(set(report['end_play'])==set(KINDS) and all(v==[True] for v in report['end_play'].values()),'one native EndPlay and empty Python state required')
    require(report['window']==4.5 and report['step']==1/64,'actual candidate clock/configuration changed')
    for phase in report['phases'][1:]:
        require(phase['clock']==phase['expected_clock'],'native fixed-step boundary was not reached exactly')
    for kind,row in report['metrics'].items():
        selected='python_' if report['profile']=='Python' else 'native_'
        other='native_' if selected=='python_' else 'python_'
        require(row[selected+'eliminations']>0 and row[other+'eliminations']==0,'wrong rule implementation executed: '+kind)
        if kind=='assist':require(row[selected+'damage']>0 and row[other+'damage']==0,'wrong damage implementation executed')
    initial=report['phases'][0]['emissions']
    assists=[e for e in initial if e['verb']=='Lyra.Assist.Message']
    require(len(assists)==1 and assists[0]['instigator']=='C' and assists[0]['target']=='D','assist attribution or post-broadcast clear differs')
    require(assists[0]['magnitude']==0.30000001192092896,'native float damage accumulation differs')
    require(assists[0]['instigator_tags']==[] and assists[0]['target_tags']==['Lyra.Damage.Message'],'native assist payload defaults/copies differ')
    require(any(e['verb'].endswith('EliminationStreak.5') and e['magnitude']==5 for e in initial),'actual configured streak threshold missing')
    equal=report['phases'][2]['emissions']
    require(any('.EliminationChain.' in e['verb'] and e['instigator']=='B' and e['magnitude']==3 for e in equal),'equal-window native chain did not continue')
    after=report['phases'][3]['emissions']
    require(not any('.EliminationChain.' in e['verb'] and e['instigator']=='C' for e in after),'after-window native chain did not reset')
    return dict(status='passed',profile=report['profile'],native_callback_fixture=True,full_acceptance=False)


def compare(native,python):
    validate(native);validate(python)
    require(native['profile']=='NativeFallback' and python['profile']=='Python','native/Python pair required')
    for key in ('inputs','thresholds','window','step'):
        require(native[key]==python[key],'source-bound fixture inputs differ: '+key)
    for a,b in zip(native['phases'],python['phases']):
        require(a['name']==b['name'] and a['emissions']==b['emissions'],'native/Python payload or broadcast order differs: '+a['name'])
    return dict(status='passed',paired_phases=len(PHASES),native_callback_fixture=True,actual_damage_or_network_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',required=True);p.add_argument('--python',required=True);a=p.parse_args()
    print(json.dumps(compare(json.loads(Path(a.native).read_text(encoding='utf-8-sig')),json.loads(Path(a.python).read_text(encoding='utf-8-sig'))),indent=2))
