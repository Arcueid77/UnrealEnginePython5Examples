"""Native setting UI cancellation, owned save and fresh-process persistence."""
from pathlib import Path


def validate(report):
    assert report['status']=='passed' and report['profile'] in ('BlueprintFallback','Python')
    assert report['setting']=='GamepadVibration' and report['mode'] in ('write','read_restore')
    assert report['saved_path_owned'] and report['native_button_handler_calls']>=2
    assert report['effective_profiles_match'] and report['selected_profile_callback_entries']==report['native_button_handler_calls']
    assert report['cancel_restores_initial'] and report['cancel_does_not_write_files']
    assert report['native_async_save_success'] and report['dirty_state_cleared']
    assert report['selectors_roots_widgets_restored'] and report['health_unchanged']
    assert not report['direct_settings_setter_called'] and not report['configuration_files_written_by_python']
    assert not report['physical_keyboard_or_pointer_tested'] and not report['full_acceptance']
    assert report['initial'] in (0,1) and report['saved'] in (0,1)
    assert report['saved']==1-report['initial']
    assert report['save_files'] and all(Path(row['path']).is_relative_to(Path(report['owned_user_root'])) for row in report['save_files'])
    if report['mode']=='write':
        assert report['same_process_reopen_keeps_saved'] and report['cancel_after_reopen_keeps_saved']
    else:
        assert report['fresh_process_loaded_saved'] and report['original_owned_value_restored']


def validate_pair(write, read):
    validate(write);validate(read)
    assert write['mode']=='write' and read['mode']=='read_restore' and write['profile']==read['profile']
    assert write['owned_user_root']==read['owned_user_root']
    assert read['initial']==write['saved'] and read['saved']==write['initial']


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);parser.add_argument('--previous');args=parser.parse_args()
    report=json.loads(Path(args.report).read_text(encoding='utf-8-sig'));validate(report)
    if args.previous:validate_pair(json.loads(Path(args.previous).read_text(encoding='utf-8-sig')),report)
    print('Native settings persistence contract passed')
