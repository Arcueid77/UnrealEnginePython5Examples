"""Actual native scalar input and local configuration persistence boundaries."""
import argparse,configparser,hashlib,json,math
from pathlib import Path
FORBIDDEN=('direct_settings_setter_called','configuration_files_written_by_python','scalar_callback_replayed','physical_keyboard_or_pointer_tested','full_acceptance','network_acceptance','packaged_runtime')
def require(value,message):
    if not value:raise ValueError(message)
def near(a,b):return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<.0001
def validate(report):
    require(report['status']=='passed' and report['error'] is None,'Native local settings failed')
    require(report['profile'] in ('BlueprintFallback','Python') and report['mode'] in ('write','read_restore'),'Unknown local settings lane')
    require(report['native_mode']=='Standalone' and report['setting']=='OverallVolume' and report['native_store']=='LyraSettingsLocal/GameUserSettings.ini','Native local scalar store required')
    for key in FORBIDDEN:require(report[key] is False,'Local settings shortcut: '+key)
    for key in ('saved_path_owned','cancel_restores_initial','cancel_does_not_write_files','dirty_state_cleared','native_ini_saved','native_companion_save_complete','selectors_roots_widgets_restored','health_unchanged'):
        require(report[key] is True,'Local settings boundary failed: '+key)
    initial,saved=report['initial'],report['saved'];require(0.<=initial<=1. and 0.<=saved<=1. and not near(initial,saved),'Native scalar must actually change')
    baselines=report['native_screen_baselines'];require(len(baselines)==(2 if report['mode']=='write' else 1),'Native screen baseline missing')
    for i,row in enumerate(baselines):
        require(near(row['value_before'],initial if i==0 else saved) and near(row['value_after'],row['value_before']) and row['config_files_unchanged'] and row['clean_after_cancel'],'Initial native cancel must retain loaded value and persistent files')
        require(row['original_cancel_used']==row['initially_dirty'],'Initial dirty screen must use the original native cancel operation')
    events=report['native_pointer_events'];require(len(events)==(3 if report['mode']=='write' else 2),'Native cancel/apply/reopen input missing')
    for i,event in enumerate(events):
        target=initial if i==2 else saved
        require(event['entry']=='SSlider.OnMouseButtonDown' and event['handled'] and event['synthetic_pointer_up_sent'],'Native slider pointer entry required')
        require(all(near(event[key],target) for key in ('target','after','ui_value','material_progress')) and not near(event['before'],target),'Slider/local-data-source/material parity differs')
        require(isinstance(event['selected_callbacks'],int) and event['selected_callbacks']>0 and event['other_callbacks']==0 and all(v>0. for v in event['native_geometry']),'Selected native scalar callback required')
    require(len(report['ini_files'])==1,'One native local INI required')
    root=Path(report['owned_user_root']).resolve();item=report['ini_files'][0];path=Path(item['path']).resolve()
    require(path.is_relative_to(root) and path.name=='GameUserSettings.ini' and near(item['value'],saved),'Wrong native local configuration output')
    data=Path(item['snapshot']).read_bytes();require(hashlib.sha256(data).hexdigest().upper()==item['sha256'],'Native INI evidence snapshot changed')
    parser=configparser.RawConfigParser(strict=False);parser.read_string(data.decode('utf-8-sig'))
    require(near(parser.getfloat('/Script/LyraGame.LyraSettingsLocal','OverallVolume'),saved),'Native local INI snapshot value differs')
    if report['mode']=='write':require(report['same_process_reopen_keeps_saved'] and report['cancel_after_reopen_keeps_saved'],'Native reopen/cancel loses saved setting')
    else:require(report['fresh_process_loaded_saved'] and report['original_owned_value_restored'],'Fresh-process load/owned restore missing')
    return dict(status='passed',profile=report['profile'],mode=report['mode'],full_acceptance=False)
def validate_pair(write,read):
    validate(write);validate(read)
    require(write['mode']=='write' and read['mode']=='read_restore' and write['profile']==read['profile'],'Same-profile native write/read pair required')
    require(Path(write['owned_user_root']).resolve()==Path(read['owned_user_root']).resolve(),'Native write/read stores differ')
    require(near(read['initial'],write['saved']) and near(read['saved'],write['initial']),'Fresh read and native original-value restore differ')
def compare(directories):
    cases={}
    for directory in directories:
        root=Path(directory);load=lambda n:json.loads((root/n).read_text(encoding='utf-8-sig'));summary=load('summary.json');report=load('result.json');validate(report)
        require(summary['status']=='passed' and summary['process']['exit_code']==summary['external_gate']['exit_code']==0,'Native process/independent gate failed')
        require(summary['cpp_compile_executed'] is False and summary['cook_package_executed'] is False,'Local settings must reuse existing binaries')
        require(summary['profile']==report['profile'] and summary['mode']==report['mode'],'Native lane metadata differs')
        require(summary['hashes'],'Frozen native inputs missing')
        for item in summary['hashes']:require(hashlib.sha256(Path(item['path']).read_bytes()).hexdigest().upper()==item['sha256'].upper(),'Frozen local-settings input changed: '+item['path'])
        key=(report['profile'],report['mode']);require(key not in cases,'Duplicate native lane');cases[key]=report
    require(set(cases)=={(p,m) for p in ('BlueprintFallback','Python') for m in ('write','read_restore')},'Four native write/read lanes required')
    for profile in ('BlueprintFallback','Python'):validate_pair(cases[profile,'write'],cases[profile,'read_restore'])
    for mode in ('write','read_restore'):
        a,b=(cases[p,mode] for p in ('BlueprintFallback','Python'))
        require(near(a['initial'],b['initial']) and near(a['saved'],b['saved']),'Original/Python local values differ')
        require([[e[k] for k in ('target','selected_callbacks','other_callbacks')] for e in a['native_pointer_events']]==[[e[k] for k in ('target','selected_callbacks','other_callbacks')] for e in b['native_pointer_events']],'Original/Python native input outcomes differ')
    return dict(status='passed',actual_clean_native_processes=4,native_pointer_changes=10,original_python_values_match=True,fresh_process_restores=2,full_acceptance=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--report');group.add_argument('--directories',nargs=4);parser.add_argument('--previous');parser.add_argument('--result');args=parser.parse_args()
    if args.report:
        read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'));report=read(args.report);result=validate(report)
        if args.previous:validate_pair(read(args.previous),report)
    else:
        require(args.result,'Local settings comparison output required');result=compare(args.directories);Path(args.result).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
