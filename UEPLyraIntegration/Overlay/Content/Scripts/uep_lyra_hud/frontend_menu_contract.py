"""Native frontend menu pushes, declined prompts and actual confirmed quit."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
ROUTES=(('start','StartGameButton','/Game/UI/Menu/Experiences/W_ExperienceSelectionScreen.W_ExperienceSelectionScreen_C'),('options','OptionsButton','/Game/UI/Settings/W_LyraSettingScreen.W_LyraSettingScreen_C'),('credits','CreditsButton','/Game/UI/Credits/W_Credits.W_Credits_C'),('replays','ReplaysButton','/Game/UI/Menu/Replays/W_ReplayBrowserScreen.W_ReplayBrowserScreen_C'))
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested','native_callbacks_replayed','confirmed_logout_session_reset_executed','online_authentication_executed','health_properties_written')
TRUE_FIELDS=('owned_roots_and_profile_selectors_restored','original_player_health_unchanged','native_user_initialization_state_unchanged')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native frontend failed')
    for k in FALSE_FIELDS:require(r[k] is False,'frontend scope overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'frontend cleanup missing: '+k)
    if r['mode']=='quit':
        require(r['profile'] in PROFILES and r['native_confirmed_quit_result']==[0] and r['native_quit_requested_from_original_confirmation'] is True and r['native_request_exit_fallback_used'] is False,'frontend quit must deliver actual native confirmed result and cause shutdown')
        return dict(status='passed',owned_native_confirmed_quit_profile=r['profile'],full_acceptance=False)
    require(r['mode']=='life' and [p['profile'] for p in r['profiles']]==list(PROFILES),'frontend lifecycle Profiles incomplete')
    for row in r['profiles']:
        require(row['actual_activation_animation_and_focus_target'] is True,'native frontend activation/focus missing')
        require(row['native_afterpush_routes']==[[name,cls] for name,_,cls in ROUTES],'native menu route/order/classes differ')
        require(row['native_declined_confirmation_results']==[['quit',1],['logout',1]] and row['original_prompt_localization_preserved'] is True and row['declines_leave_original_controller_world'] is True,'native frontend decline/prompt evidence missing')
    require(r['source_python_state_pairs_match'] is True,'native frontend Profile state differs')
    return dict(status='passed',native_lifecycle_profiles=2,native_afterpush_routes=8,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
