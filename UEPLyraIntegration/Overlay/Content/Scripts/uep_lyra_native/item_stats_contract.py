"""Require actual native inventory callbacks, not fabricated stat application."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require


def validate(report):
    require(report['status']=='passed' and report['error'] is None,'native initial-stat matrix failed')
    require(len(report['production_cases'])==20 and len(report['boundary_cases'])==10 and len(report['detached_cases'])==2,'initial-stat definition/boundary matrix incomplete')
    for key in ('production_cases','boundary_cases'):
        rows=report[key];require({r['profile'] for r in rows}=={'Python','NativeFallback'} and all(r['selected_calls']==1 for r in rows),'native/Python initial-stat route mismatch')
        for name in {r['name'] for r in rows}:require(len({json.dumps(r['values'],sort_keys=True) for r in rows if r['name']==name})==1,'native/Python initial-stat values differ')
    require(report['handled_python_callback_no_native_replay'] and report['native_inventory_creation_used'],'native initial-stat creation or no-replay guard missing')
    require(report['profile_overrides_cleared'] and report['class_roots_restored'] and report['fixture_actor_destroyed'],'initial-stat fixture cleanup failed')
    require(not report['direct_policy_calls'] and not report['fixture_assets_saved'] and not report['native_replication_replaced'],'initial-stat matrix bypassed production callbacks')
    return dict(status='passed',profiles=2,production_creation_cases=20,boundary_creation_cases=10,missing_definition_cases=2,handled_callback_no_native_replay=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);a=p.parse_args();print(json.dumps(validate(json.loads(a.report.read_text(encoding='utf-8-sig'))),indent=2))
