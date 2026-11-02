"""Actual Escape input, native Menu layer/input modes and travel/destruct gates."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require

PLAN=[('L_EscapeUI_A','NativeFallback',2),('L_EscapeUI_A','Python',2),('L_EscapeUI_B','Python',2),('L_EscapeUI_A','NativeFallback',1)]


def validate_matrix(report):
    require(report['status']=='passed' and report['error'] is None,'native Escape runtime failed')
    require(len(report['stages'])==len(PLAN) and len(report['cycles'])==7,'Escape profile/travel/repeat matrix incomplete')
    for stage,(map_name,profile,count) in zip(report['stages'],PLAN):require(map_name in stage['world'] and stage['profile']==profile and stage['cycles']==count,'Escape stage differs')
    for row in report['cycles']:
        require(row['open_dispatch_delta']==1 and row['close_dispatch_delta']==0,'Escape action dispatched more than once')
        require(row['menu_class']==row['requested_class'] and row['original_menu_layer'] and row['owning_player_matches'],'native streamed Menu layer/class/owner differs')
        require(row['menu_desired_input_config']==3,'original Menu desired input configuration changed')
        require(row['input_before'] in (1,2) and row['input_open'] in (0,1,2) and row['input_after']==row['input_before'],'native input state did not restore')
        require(row['ignore_after']==row['ignore_before'] and row['menu_deactivated_and_removed'],'native input or Menu cleanup failed')
    require(len(report['travels'])==2 and all(r['native_destruct_observed'] and r['new_hud_observed'] for r in report['travels']),'native HUD travel/destruct/rebuild evidence missing')
    require(report['profile_classes_selectors_roots_restored'] and report['menu_stack_empty_at_exit'],'Escape observers/selectors/Menu layer leaked')
    require(report['stack_transitions_restored_or_released'],'runtime stack transition fixture leaked')
    require(not report['synthetic_keyboard_events'] and not report['cook_package_executed'],'Escape validation overclaims')


def validate(report,actions=None):
    validate_matrix(report)
    require(report['validation_mode']=='actual_window' and not report['direct_handle_calls'] and report['direct_handle_call_count']==report['direct_deactivate_call_count']==0,'headless calls cannot accept actual Escape input')
    require(report['headless_transition_overrides']==0,'actual-window input cannot use the headless animation fixture')
    require(all(row['input_open']==0 for row in report['cycles']),'actual-window native input did not enter Menu mode')
    if actions is not None:
        require(actions['run_id']==report['run_id'] and actions['computer_use']=='@oai/sky','foreign UI input evidence')
        rows=actions['actions'];require(len(rows)==14 and [r['serial'] for r in rows]==list(range(1,15)),'actual Escape input matrix incomplete')
        require(all(r['key']=='Escape' and r['window_id'] and r['before_screenshot'] and r['after_screenshot'] for r in rows),'actual window/key/screenshot evidence missing')
    return dict(status='passed',profiles=2,escape_open_close_cycles=7,actual_window_escape_inputs=14 if actions is not None else None,native_input_modes_and_travel_cleanup=True,isolated_common_ui_worlds=True,full_shooter_scene_rendering_acceptance=False)


def validate_headless(report):
    validate_matrix(report)
    require(report['validation_mode']=='headless_policy' and report['direct_handle_calls'] and report['direct_handle_call_count']==report['direct_deactivate_call_count']==7,'headless policy matrix incomplete')
    require(not report['actual_os_keyboard_events'] and not report['visible_ui_observed'],'headless checks cannot claim actual input or visible pixels')
    require(report['headless_transition_overrides']>=2,'explicit headless stack animation fixture required')
    states={p:{(r['input_before'],r['input_open'],r['input_after'],tuple(r['ignore_before']),tuple(r['ignore_after'])) for r in report['cycles'] if r['profile']==p} for p in ('Python','NativeFallback')}
    require(len(states['Python'])==len(states['NativeFallback'])==1 and states['Python']==states['NativeFallback'],'native/Python observed input states differ')
    return dict(status='passed',profiles=2,escape_open_close_cycles=7,direct_policy_calls=7,direct_deactivate_calls=7,native_desired_menu_input_config_verified=True,native_input_state_observed_and_restored=True,native_menu_mode_transition_acceptance=False,native_travel_cleanup=True,zero_duration_runtime_stack_fixture=True,stack_transitions_restored_or_released=True,actual_window_input_acceptance=False,visible_ui_acceptance=False,full_shooter_scene_rendering_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--actions',type=Path);p.add_argument('--headless',action='store_true');a=p.parse_args()
    if not a.headless and a.actions is None:p.error('--actions is required for actual-window input acceptance')
    report=json.loads(a.report.read_text(encoding='utf-8-sig'));print(json.dumps(validate_headless(report) if a.headless else validate(report,json.loads(a.actions.read_text(encoding='utf-8-sig'))),indent=2))
