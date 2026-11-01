"""Native spawn/name/destruction facts; random draws stay in the native RNG."""
import argparse
import json
from pathlib import Path
import re
from .message_validation_contract import require


def validate(r):
    require(r['status']=='passed' and r['error'] is None,'bot runtime/finalizer failed')
    require(r['profile'] in ('Python','NativeFallback') and r['family'] in ('TDM','CP'),'explicit production bot family/profile required')
    require(r['natural_component_count']==1 and r['natural_bot_count']==3,'natural experience native bot creation absent')
    selected='python_' if r['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_'
    require(r['natural_metrics'][selected+'create']==1 and r['natural_metrics'][selected+'name']==3,'natural creation/name routes missing')
    require(r['metrics'][selected+'create']==8 and r['metrics'][selected+'name']==9 and r['metrics'][selected+'remove']==9,'native policy entry counts differ')
    require(all(r['metrics'][other+k]==0 for k in ('create','name','remove')),'wrong native bot policy executed')
    cases=r['cases'];require([x['name'] for x in cases]==['no_controller','default','url_one','url_zero','url_negative','name_exhaustion'],'bot precedence/name cases missing')
    require([x['added'] for x in cases]==[0,2,1,0,0,3],'native default/URL/controller precedence differs')
    require(set(cases[1]['names'])=={'UEPFixture-A','UEPFixture-B'},'native name swap-removal or non-repetition differs')
    require(cases[2]['names']==['UEPFixture-Only'],'single native name selection differs')
    exhausted=cases[5]['names'];require(set(exhausted[:2])=={'UEPFixture-First','UEPFixture-Second'},'native exhausted names repeat/shift')
    require(re.fullmatch(r'Tinplate (\d+)',exhausted[2]) and 260<=int(exhausted[2].split()[-1])<=360,'native fallback name range differs')
    require(len(r['removals'])==9 and all(x['before']-x['after']==1 and x['removed_controllers']==1 for x in r['removals']),'native removal list/destruction differs')
    require(r['native_death_callbacks']==9 and r['empty_remove_did_not_select'],'native health self-destruction/empty removal differs')
    require(all(r[k] for k in ('configuration_restored','selectors_restored','observer_scope_closed','native_component_destroyed','python_names_cleared')),'bot fixture/lifecycle cleanup incomplete')
    require(not any(r[k] for k in ('global_rng_replaced','health_attribute_writes','score_stat_writes','native_spawn_or_destroy_replaced')),'native low-level flow was replaced')
    if r['profile']=='Python':require(r['python_names_before_teardown']==2,'nonempty Python state teardown not exercised')


def compare(native,python):
    validate(native);validate(python)
    require(native['profile']=='NativeFallback' and python['profile']=='Python' and native['family']==python['family'],'wrong bot comparison pair')
    require([x['added'] for x in native['cases']]==[x['added'] for x in python['cases']],'native/Python spawn count differs')
    require([(x['before'],x['after']) for x in native['removals']]==[(x['before'],x['after']) for x in python['removals']],'native/Python removal cardinality differs')
    return dict(status='passed',family=native['family'],native_spawn_name_and_removal=True,exact_rng_sequence_claim=False,editor_pie_override_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--python',type=Path,required=True);a=p.parse_args()
    print(json.dumps(compare(json.loads(a.native.read_text(encoding='utf-8-sig')),json.loads(a.python.read_text(encoding='utf-8-sig'))),indent=2))
