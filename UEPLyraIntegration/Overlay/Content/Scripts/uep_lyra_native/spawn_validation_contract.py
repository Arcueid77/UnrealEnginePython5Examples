"""Native collision/claim facts, deterministic choice cases, and real restart."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require

NAMES=('tdm_far','tdm_tie','tdm_max_pair','claimed_fallback','unclaimed_priority',
       'no_candidates','spectator','spectator_empty','fallback_empty','fallback_partial','fallback_full')


def validate(r):
    require(r['status']=='passed' and r['error'] is None,'spawning runtime/finalizer failed')
    selected='python_' if r['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_'
    require(r['natural_component_count']==1 and r['natural_metrics'][selected+'choose']>=4 and r['natural_metrics'][selected+'tdm']>=4,'natural GameMode spawning bypassed selected rules')
    require(r['metrics'][other+'choose']==r['metrics'][other+'tdm']==0,'wrong spawning implementation executed')
    require([c['name'] for c in r['cases']]==list(NAMES),'spawn policy branches incomplete')
    expected=['B','A','A','B','B',None,'A',None,'A','partial',None]
    require([c['chosen'] for c in r['cases']]==expected,'native farthest/tie/claim/fallback choice differs')
    require(r['cases'][6]['claimed_after']==[False],'spectator claimed a start')
    require(r['physics_states']==dict(empty=0,partial=1,full=2),'actual native occupancy groups incomplete')
    require(r['native_restart_executed'] and r['native_restart_new_pawn_valid'] and r['native_restart_choose_delta']>=1,'ordinary native RestartPlayer did not enter policy')
    require(all(r[k] for k in ('fixture_actors_destroyed','player_state_flags_restored','pawn_positions_restored','selectors_restored','private_cache_not_written')),'spawning fixture/cache cleanup incomplete')
    require(not any(r[k] for k in ('physics_query_replaced','native_rng_replaced','native_claim_timer_replaced','cached_player_starts_overwritten')),'native mechanics replaced')


def compare(native,python):
    validate(native);validate(python)
    require(native['profile']=='NativeFallback' and python['profile']=='Python','wrong spawning pair')
    for key in ('cases','physics_states'):require(native[key]==python[key],'native/Python spawning result differs: '+key)
    return dict(status='passed',policy_cases=len(NAMES),native_occupancy_claims_and_restart=True,exact_rng_sequence_claim=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--python',type=Path,required=True);a=p.parse_args();print(json.dumps(compare(json.loads(a.native.read_text(encoding='utf-8-sig')),json.loads(a.python.read_text(encoding='utf-8-sig'))),indent=2))
