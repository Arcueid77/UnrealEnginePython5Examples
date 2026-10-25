"""Native CommonUI focus/back/reopen evidence; no manual close as stimulus."""
import argparse,hashlib,json
from pathlib import Path
FORBIDDEN=('callbacks_replayed','focus_set_by_probe','manual_back_binding','manual_deactivate_before_back','manual_pop_before_back',
    'health_written','settings_written','physical_input_tested','network_acceptance','packaged_runtime','full_acceptance')
def require(value,message):
    if not value:raise ValueError(message)
def validate(report):
    require(report['status']=='passed' and report['error'] is None,'Native Back observation failed')
    require(report['native_mode']=='Standalone','Standalone UI owner required')
    for key in FORBIDDEN:require(report[key] is False,'UI Back fixture shortcut: '+key)
    for key in ('owned_widgets_unmounted_and_unrooted','class_selectors_restored','class_roots_restored','health_unchanged'):
        require(report[key] is True,'UI Back cleanup incomplete: '+key)
    require(report['profile'] in ('BlueprintFallback','Python'),'Unknown native UI profile')
    rows=report['cases'];require(len(rows)==2,'Two complete open/back/reopen cycles required')
    require([(r['profile'],r['cycle']) for r in rows]==[(report['profile'],i) for i in (0,1)],'Missing/duplicate UI profile or reopen cycle')
    for row in rows:
        for key in ('menu_options_native_focus','settings_native_focus','screen_profile_matches','back_profile_matches','menu_inactive_after_settings_push',
            'settings_closed_by_native_back','closed_settings_has_no_focus','world_unchanged','health_unchanged'):
            require(row[key] is True,'Native focus/back outcome differs: '+key)
        require(row['native_push_entry']=='CommonUIExtensions.PushContentToLayer_ForPlayer' and row['native_back_entry']=='CommonBoundActionButton.HandleButtonClicked' and row['native_back_text']=='Back','Real native layer/action binding required')
        require(row['menu_settings_selected_callbacks']==1 and row['menu_settings_other_callbacks']==0,'Wrong settings routing profile')
        require(row['back_selected_click_callbacks']==1 and row['back_other_click_callbacks']==0,'Wrong native Back-button click profile')
    return dict(status='passed',native_back_actions=2,profile_reopen_cycles=1,full_acceptance=False)
def outcome(report):
    validate(report);return [{k:v for k,v in row.items() if k not in ('profile','world')} for row in report['cases']]
def compare(directories,*,verify_frozen=True):
    cases={}
    for directory in directories:
        root=Path(directory);read=lambda n:json.loads((root/n).read_text(encoding='utf-8-sig'))
        summary=read('summary.json');report=read('failure.json')
        require(summary['status']=='passed' and summary['process']['exit_code']==summary['external_gate']['exit_code']==0,'Native UI process or independent gate failed')
        require(summary['cpp_compile_executed'] is False and summary['cook_package_executed'] is False,'UI Back must reuse the existing build')
        require(summary['profile']==report['profile'] and report['profile'] not in cases,'Missing/mixed native profile')
        if verify_frozen:
            require(summary['hashes'],'Frozen native UI inputs missing')
            for item in summary['hashes']:require(hashlib.sha256(Path(item['path']).read_bytes()).hexdigest().upper()==item['sha256'].upper(),'Native UI input changed: '+item['path'])
        cases[report['profile']]=outcome(report)
    require(set(cases)=={'BlueprintFallback','Python'},'Both isolated profiles required')
    require(cases['BlueprintFallback']==cases['Python'],'Native focus/back/reopen outcomes differ')
    return dict(status='passed',native_back_actions=4,actual_clean_native_processes=2,outcome=cases['Python'],full_acceptance=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--report');group.add_argument('--directories',nargs=2);parser.add_argument('--result');args=parser.parse_args()
    if args.report:print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding='utf-8-sig')))))
    else:
        require(args.result,'UI comparison result path required');result=compare(args.directories)
        Path(args.result).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='outcome'}))
