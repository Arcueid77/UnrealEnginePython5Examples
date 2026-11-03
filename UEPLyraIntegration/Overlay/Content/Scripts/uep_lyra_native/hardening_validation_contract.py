"""Closed native hardening evidence with deliberate faults kept explicit."""
import argparse
import json
from pathlib import Path

def validate(r):
    assert r['status']=='passed' and r['error'] is None
    assert r['declarations_restored'] and r['selector_restored'] and r['owned_cases_released'] and r['subscriptions_closed']
    assert not r['physical_input_tested'] and not r['cpp_compile_executed']
    if r['mode']=='Exceptions':
        assert len(r['cases'])==13 and {v['kind'] for v in r['cases']}=={'native_damage_policy','native_item_cost_check','native_item_cost_apply','native_reward_settlement','native_reset_abort'}
        assert all(v['callbacks']==1 and v['recovered'] for v in r['cases'])
        return dict(status='passed',actual_native_exception_cases=13,recovered=True,no_duplicate_native_payment_or_reward=True,native_reset_ends_on_exception=True,subscriptions_closed=True)
    if r['mode']=='Benchmark':
        assert [v['family'] for v in r['benchmarks']]==['Damage','Pawn']
        for row in r['benchmarks']:
            assert row['order_interleaved'] and row['batch_calls']==300 and row['python_to_native_ratio']>0
            for mode in ('native','python'):assert row[mode]['samples']==12 and row[mode]['calls']==3600 and row[mode]['median_ns_per_call']>0
        return dict(status='passed',timed_native_and_python_calls=14400,scope=r['timing_scope'])
    assert r['mode']=='Soak' and r['runtime_elapsed_seconds']>=r['duration_requested']>=60
    assert r['queries']>=r['duration_requested']*20 and r['native_resets']==r['completed_respawns']>=int(r['duration_requested']/20)-2
    assert r['native_player_state_preserved'] and all(v['same_player_state'] and v['old']!=v['new'] for v in r['respawns'])
    samples=r['post_gc_samples'];assert len(samples)>=int(r['duration_requested']/11)-1
    assert all(s[k]<=128 for s in samples for k in ('rule_trace','world_trace','reset_trace'))
    assert max(s['contexts'] for s in samples)<=8
    return dict(status='passed',sustained_seconds=r['runtime_elapsed_seconds'],native_reset_respawns=r['completed_respawns'],native_queries=r['queries'],long_soak=r['duration_requested']>=1200)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
