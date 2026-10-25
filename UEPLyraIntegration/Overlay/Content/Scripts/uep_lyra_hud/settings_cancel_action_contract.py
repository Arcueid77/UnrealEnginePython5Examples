"""Native represented Cancel action must revert dirty settings without saving."""
import argparse,hashlib,json,math
from pathlib import Path
FORBIDDEN=('cancel_api_called_by_probe','apply_api_called_by_probe','callbacks_replayed','settings_setter_called_by_probe','configuration_store_written_by_python','physical_input_tested','full_acceptance','network_acceptance','packaged_runtime')
def require(value,message):
    if not value:raise ValueError(message)
def near(a,b):return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<.0001
def click(receipt):
    require('cancel' in receipt['label'].casefold() and receipt['native_entry']=='CommonBoundActionButton.HandleButtonClicked' and receipt['profile_matches'],'Actual represented Cancel button required')
    require(receipt['selected_clicks']==1 and receipt['other_clicks']==0,'Wrong Cancel click profile')
def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['profile'] in ('BlueprintFallback','Python'),'Native Cancel lane failed')
    require(report['native_mode']=='Standalone' and report['saved_path_owned'],'Owned native UI/file context required')
    for key in FORBIDDEN:require(report[key] is False,'Cancel fixture shortcut: '+key)
    for key in ('owned_widgets_unmounted_and_unrooted','class_selectors_restored','class_roots_restored','health_unchanged','scalar_fixture_unmounted_and_unrooted'):
        require(report[key] is True,'Cancel cleanup incomplete: '+key)
    rows=report['cases'];require(len(rows)==2 and [r['cycle'] for r in rows]==[0,1],'Two native dirty/cancel/reopen cycles required')
    for row in rows:
        require(row['profile']==report['profile'] and row['menu_options_native_focus'] and row['settings_native_focus'],'Native menu/settings ownership or focus differs')
        initial,target=row['initial'],row['target'];require(not near(initial,target),'Scalar input must actually change value')
        pointer=row['pointer'];require(pointer['entry']=='SSlider.OnMouseButtonDown' and pointer['handled'] and pointer['selected_callbacks']>0 and pointer['other_callbacks']==0,'Real selected slider input required')
        require(all(near(pointer[k],target) for k in ('target','after','ui_value','material_progress')),'Native slider/data source/material differ')
        if row['initially_dirty']:
            baseline=row['baseline_cancel'];click(baseline)
            require(near(baseline['value_before'],initial) and near(baseline['value_after'],initial) and baseline['files_unchanged'] and baseline['clean'] and baseline['screen_active'],'Initial native Cancel must retain loaded state')
        result=row['cancel'];click(result)
        require(near(result['value_before'],target) and all(near(result[k],initial) for k in ('value_after','ui_after','material_after')),'Actual Cancel must revert value/UI/material')
        require(result['screen_active'] and result['clean'] and result['files_before']==result['files_after'] and result['cancel_action_removed'],'Cancel must retain the screen,clear dirty/action binding and preserve files')
        for key in ('native_back_after_cancel_closed','volume_still_original','world_unchanged','health_unchanged'):require(row[key] is True,'Native post-Cancel back/ownership differs: '+key)
    return dict(status='passed',native_dirty_cancel_actions=2,full_acceptance=False)
def outcome(report):
    validate(report)
    return [dict(initial=r['initial'],target=r['target'],pointer_callbacks=r['pointer']['selected_callbacks'],cancel_clicks=r['cancel']['selected_clicks'],value_after=r['cancel']['value_after'],material_after=r['cancel']['material_after']) for r in report['cases']]
def compare(directories):
    cases={}
    for directory in directories:
        root=Path(directory);load=lambda n:json.loads((root/n).read_text(encoding='utf-8-sig'));summary=load('summary.json');report=load('failure.json')
        require(summary['status']=='passed' and summary['process']['exit_code']==summary['external_gate']['exit_code']==0,'Native process/gate did not pass')
        require(not summary['cpp_compile_executed'] and not summary['cook_package_executed'],'Cancel lane must reuse existing binaries')
        require(summary['profile']==report['profile'] and report['profile'] not in cases,'Distinct matching profiles required')
        require(summary['hashes'],'Frozen native inputs missing')
        for item in summary['hashes']:require(hashlib.sha256(Path(item['path']).read_bytes()).hexdigest().upper()==item['sha256'].upper(),'Frozen Cancel input changed: '+item['path'])
        cases[report['profile']]=outcome(report)
    require(set(cases)=={'BlueprintFallback','Python'} and cases['BlueprintFallback']==cases['Python'],'Both native Cancel profile outcomes must match')
    return dict(status='passed',native_dirty_cancel_actions=4,actual_clean_native_processes=2,outcome=cases['Python'],full_acceptance=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--report');group.add_argument('--directories',nargs=2);parser.add_argument('--result');args=parser.parse_args()
    if args.report:result=validate(json.loads(Path(args.report).read_text(encoding='utf-8-sig')))
    else:
        require(args.result,'Cancel comparison result required');result=compare(args.directories);Path(args.result).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='outcome'}))
