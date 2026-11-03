"""Recheck only a failed pure dependency gate on an unchanged successful run."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence,require
from inspect_native_package_dependencies import inspect
from check_hardening_log import validate as log_gate
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.hardening_validation_contract import validate

def review(directory,cook_directory):
    directory,cook_directory=directory.resolve(),cook_directory.resolve()
    require(directory.is_relative_to(REPO/'.build') and cook_directory.is_relative_to(REPO/'.build'),'owned closed run and cook required')
    summary_path=directory/'summary.json';summary=load(summary_path);cook=load(cook_directory/'summary.json')
    require(summary['status']=='failed' and 'Packaged CPython receipt and actual runtime home exited 1' in summary['error'] and summary['mode']=='Exceptions','only the known pure dependency gate failure may be reviewed')
    require(cook['status']=='passed' and summary['process']['exit_code']==0 and summary['packaged_runtime'],'successful actual packaged process required')
    for key in ('contract','log_gate'):require(summary[key]['exit_code']==0,'previous independent native gate failed')
    validate(load(directory/'runtime.json'));log_gate((directory/'runtime.log').read_text(encoding='utf-8-sig'),13)
    tool=Path(__file__).with_name('inspect_native_package_dependencies.py')
    for row in summary['hashes']:
        if Path(row['path']).resolve()!=tool.resolve():require(sha(Path(row['path']))==row['sha256'],'frozen runtime input changed')
    game=Path(cook['packaged_executable']);require(Path(summary['process']['executable'])==game,'reviewed process used another executable')
    for row in cook['products']:require(sha(Path(row['path']))==row['sha256'],'cooked package changed')
    loaded=summary['loaded_python'];require(loaded['actual_loaded_module'] and loaded['inside_package'] and loaded['source_engine_modules_loaded']==0 and sha(Path(loaded['path']))==loaded['sha256'],'actual loaded runtime evidence differs')
    build_row,=[r for r in cook['hashes'] if Path(r['path']).name=='summary.json'];build=load(Path(build_row['path']))
    receipt=next(Path(r['path']) for r in build['products'] if Path(r['path']).name=='LyraGame.target')
    report=inspect(game.parents[3],Path('F:/UnrealEngine'),receipt,directory/'runtime.log',game.parent)
    dependencies=directory/'dependencies-review02.json';result=directory/'summary-reviewed.json'
    require(not dependencies.exists() and not result.exists(),'fresh dependency-review evidence required')
    dependencies.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    reviewed=dict(summary,status='passed',error=None,pure_dependency_review=True,original_summary=evidence(summary_path),
        dependency_report=evidence(dependencies),dependency_checker=evidence(tool),native_process_rerun=False,
        review_scope='Only exact UAT INI UTF-8 BOM/newline normalization is accepted; all original native/runtime/package hashes and passed gates rechecked.')
    result.write_text(json.dumps(reviewed,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='passed',native_process_rerun=False,receipt_python_files=report['receipt_python_files'],ini_normalizations=len(report['staging_line_ending_normalizations']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--cook-directory',type=Path,required=True)
    a=p.parse_args();print(json.dumps(review(a.directory,a.cook_directory)))
