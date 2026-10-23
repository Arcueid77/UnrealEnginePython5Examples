"""Real NULL-provider duplicate join rejection and subsequent UI retry."""
import argparse
import json
from pathlib import Path
from .session_entry_contract import CLIENT_TRUE, HOST_TRUE, FALSE_FIELDS


def require(value,message):
    if not value:raise RuntimeError(message)


def validate_peer(report):
    require(report['status']=='passed' and report['error'] is None,'Join failure peer failed')
    for key in FALSE_FIELDS:
        if key!='failed_join_error_ui_natively_tested':require(report[key] is False,'Join scope overclaim: '+key)
    if report['role']=='host':
        for key in HOST_TRUE:require(report[key] is True,'Missing host observation: '+key)
        require(report['native_destination_mode']=='ListenServer','Native listen host missing')
    else:
        require(report['role']=='client' and report['profile'] in ('BlueprintFallback','Python'),'Unknown join client')
        for key in CLIENT_TRUE:require(report[key] is True,'Initial actual native join missing: '+key)
        for key in ('failed_join_error_ui_natively_tested','duplicate_row_uses_actual_advertised_result',
                    'native_duplicate_join_rejected','native_failure_ftext_history_preserved','native_spinner_popped_after_failure',
                    'native_acknowledgement_closed_error_dialog','failure_cleanup_destroyed_owned_named_session',
                    'native_retry_rejoined_same_host','initial_row_not_reentered_by_other_join_notifications','exclusive_selected_profile_calls'):
            require(report[key] is True,'Missing duplicate join observation: '+key)
        require(report['native_join_notification_sequence']==[True,False,True],'Native success/reject/retry sequence differs')
        require(report['native_failure_error_id']=='UnknownError','NULL provider result must retain its actual native error id')
        require(report['duplicate_prepared_calls']==report['duplicate_completion_calls']==2,'Duplicate or missing entry continuation')
        require(report['native_destination_mode']=='Client','Actual native client travel missing')
    return True


def validate(directory):
    root=Path(directory);host=json.loads((root/'host.json').read_text(encoding='utf-8-sig'));validate_peer(host)
    clients=[json.loads((root/(p+'.json')).read_text(encoding='utf-8-sig')) for p in ('BlueprintFallback','Python')]
    for report in clients:
        validate_peer(report)
        require(report['native_destination_level']==host['native_destination_level'] and report['native_destination_experience']==host['native_destination_experience'],'Client joined a different host Experience')
    require(clients[0]['failure_state']==clients[1]['failure_state'],'Original/Python error FText or native result differs')
    return dict(status='passed',owned_native_processes=3,actual_join_successes=4,native_duplicate_join_failures=2,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    print(json.dumps(validate(parser.parse_args().directory)))
