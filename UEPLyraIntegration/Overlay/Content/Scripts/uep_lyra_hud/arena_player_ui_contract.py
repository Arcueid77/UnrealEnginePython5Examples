"""Gate native registry callbacks, not just opaque-handle pointer validity."""
import argparse,json
from collections import Counter
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

def registrations(rows):return Counter((v['data'],v['tag'],v['priority'],v['context']) for v in rows)

def counts(value,mode,ended):
    expected=dict(python_begin=int(mode=='Python'),python_end=int(mode=='Python' and ended),fallback_begin=int(mode=='BlueprintFallback'),fallback_end=int(mode=='BlueprintFallback' and ended),registrations=int(mode=='Python'),unregistrations=int(mode=='Python' and ended))
    require(value==expected,'selected component lifecycle Profile differs')

def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Arena player UI native observation failed')
    require(r['mode'] in ('Baseline','Python','BlueprintFallback'),'unknown component Profile')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','lifecycle_callbacks_replayed','registry_replaced'):
        require(r[key] is False,'Arena player UI overclaim: '+key)
    require(r['cleanup_complete'] and r['observer_callback_native'] and r['native_component_destruction'],'native observer/lifecycle cleanup missing')
    require(r['natural_components'] and len(r['owned_components'])==2,'real Arena components and two independent owned lifecycles required')
    for row in r['natural_components']:
        require(row['owner_is_playerstate'] and row['handle_valid'],'original natural PlayerState registration missing')
        counts(row['counts'],r['mode'],False)
    initial=r['initial_registry'];final=r['final_registry'];events=r['owned_events']
    require(len(initial)>=len(r['natural_components']) and registrations(initial)==registrations(final),'natural registry changed after owned destruction')
    require([v['action'] for v in events]==[0,0,1,1],'two native additions followed by independent removals required')
    for row in initial+final+events:
        require(row['data'] and row['tag']=='TopDownArena.ExtensionPoint.Players' and row['priority']==-1 and row['context'] is None and row['handle_valid'],'native extension Data/tag/priority/context differs')
    require(all(v['data']==r['owned_owner'] for v in events),'owned registration Data is not the actual PlayerState')
    for row in r['owned_components']:
        require(row['owner']==r['owned_owner'] and row['handle_valid_before'] and row['handle_valid_after_unregister'],'original retained opaque handle state differs')
        counts(row['counts_after'],r['mode'],True)
    require(r['remaining_after_first_destroy']==len(initial)+1 and r['remaining_after_second_destroy']==len(initial),'native independent handle removal differs')
    return dict(status='passed',mode=r['mode'],natural_components=len(r['natural_components']),owned_component_lifecycles=2,native_registry_events=4,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
