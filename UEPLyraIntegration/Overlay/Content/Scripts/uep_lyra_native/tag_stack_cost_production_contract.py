"""All configured item-cost consumers, retaining the original saved subobjects."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['configured_consumers']==5 and len(report['cases'])==20,'configured item-cost matrix incomplete')
    require(len({r['ability'] for r in report['cases']})==5 and {r['profile'] for r in report['cases']}=={'Python','NativeCostFallback'},'configured consumer/profile scope differs')
    for r in report['cases']:
        n=r['available'];require(r['outcome']==dict(can_pay=n>0,before=n,after=max(0,n-1),failure_tags=[] if n else ['Ability.ActivateFail.Cost']),'configured item-cost original result differs')
    require(report['original_cost_subobjects_preserved'] and report['fixture_actors_removed'] and report['class_roots_restored'] and not report['fixtures_saved'] and not report['natural_unused_prototype_activation_claimed'],'configured consumer proof/cleanup/scope differs')
    return dict(status='passed',configured_consumers=5,native_cost_cases=20,profiles=2,natural_unused_prototype_activation_claimed=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);a=p.parse_args();print(json.dumps(validate(json.loads(a.report.read_text(encoding='utf-8-sig'))),indent=2))
