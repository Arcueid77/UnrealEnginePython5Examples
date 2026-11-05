"""Extend the complete original package inventory with native-test VM observers."""
import argparse
import json
from pathlib import Path
from plan_migration_package import inspect,sha

def plan(stage,overlay,manifest,fixtures,configuration='Development'):
    result=inspect(stage,overlay,manifest,configuration);report=json.loads(fixtures.read_text(encoding='utf-8-sig'))
    if report['status']!='passed' or report['fixture_count']!=3 or not report['production_assets_unchanged']:raise ValueError('Closed three-observer fixture authoring required')
    rows=[]
    for row in report['assets']:
        p=stage/row['relative_path']
        if sha(p).upper()!=row['sha256'].upper():raise ValueError('Typed validation fixture changed')
        rows.append(dict(relative_path=row['relative_path'],sha256=row['sha256'],stage=str(p)))
    result['validation_fixture_assets']=rows
    directory='/Game/UEPValidation'
    if directory not in result['proposed_always_cook_directories']:
        result['proposed_always_cook_directories'].append(directory);result['proposed_cook_directory_paths'].append(dict(virtual_directory=directory,physical_directory=str(stage/'Content/UEPValidation')))
    result['native_hardening_scope']=True;return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('stage','overlay','manifest','fixtures','result'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--configuration', choices=('Development','Shipping'), default='Development')
    a=p.parse_args();r=plan(a.stage.resolve(),a.overlay.resolve(),a.manifest.resolve(),a.fixtures.resolve(),a.configuration);a.result.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(dict(status='passed',configuration=a.configuration,candidates=len(r['candidate_assets']),overlay_assets=len(r['accepted_overlay_assets']),native_observers=3)))
