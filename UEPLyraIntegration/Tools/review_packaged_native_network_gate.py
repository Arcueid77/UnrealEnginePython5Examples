"""Review unchanged successful native peers with the listen-topology contract."""
import argparse
import json
from pathlib import Path
import re
from collect_native_message_acceptance import REPO,load,sha,evidence,require
from check_packaged_native_network import validate

def review(directory):
    directory=directory.resolve();require(directory.is_relative_to(REPO/'.build'),'owned closed native run required')
    original=directory/'summary.json';summary=load(original);lane=summary['lanes']['rule']
    require(summary['status']=='failed' and 'prediction/authority gate exited 1' in summary['error'] and summary['packaged_authority_mode']=='ListenServer','only the known dedicated/listen independent gate difference may be reviewed')
    require(set(lane['processes'])=={'server','A','B0'} and all(p['exit_code']==0 for p in lane['processes'].values()),'all three original native processes must have exited cleanly')
    for row in summary['hashes']:require(sha(Path(row['path']))==row['sha256'],'frozen native network/package input changed')
    reports={peer:load(directory/'rule'/(peer+'.json')) for peer in ('server','A','B0')}
    result=validate(reports,reports['server']['rule_family'])
    for peer in reports:
        text=(directory/'rule'/(peer+'.log')).read_text(encoding='utf-8-sig')
        require(re.search(r'Goodbye Python.*UEP_NATIVE_RULE_NETWORK_SHUTDOWN_PASSED.*Log file closed',text,re.S) is not None,'normal native network shutdown missing')
        require(re.search(r'Fatal error:|Assertion failed|Unhandled Exception|Ensure condition failed|Traceback|Log\w+:\s*Error:',text) is None,'unexpected native network diagnostic')
        dependency=load(directory/'rule'/(peer+'-dependencies.json'))
        require(dependency['status']=='passed' and dependency['runtime_home_inside_package'],'original peer dependency gate failed')
        for row in dependency['dependency_files']:
            package=Path(lane['processes'][peer]['executable']).parents[3]
            require(sha(package/row['relative_path'])==row['sha256'],'packaged peer dependency changed')
    output=directory/'summary-reviewed.json';require(not output.exists(),'fresh independent review required')
    updated=dict(summary,status='passed',error=None,actual_native_rule_network=True,pure_network_contract_review=True,native_process_rerun=False,
        original_summary=evidence(original),network_checker=evidence(Path(__file__).with_name('check_packaged_native_network.py')),
        independent_result=result,review_scope='Preserve raw peers; assert listen UI and local cosmetic completion while retaining native ownership, damage, respawn, RPC, observer, exit and client-view checks.')
    output.write_text(json.dumps(updated,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='passed',native_process_rerun=False,independent_result=result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();print(json.dumps(review(a.directory)))
