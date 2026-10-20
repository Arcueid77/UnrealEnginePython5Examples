"""Original identity Logout success, local reset, startup and initialization."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
IDENTITY_PROXY='/Script/OnlineSubsystemUtils.LogoutCallbackProxy'
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested','native_callbacks_replayed','online_authentication_tested','health_properties_written','frontend_map_travel_executed','session_destruction_claimed')
TRUE_FIELDS=('native_default_online_subsystem_is_null','fixture_primary_local_play_precondition_complete','owned_roots_and_profiles_restored','original_controller_health_and_initialized_local_user_state_preserved')
ROW_TRUE=('native_localized_confirmation_preserved','native_confirmed_logout_result_delivered','native_original_identity_logout_success_handler_executed','native_user_info_object_replaced_by_reset','native_startup_afterpush_and_waiting_state','native_primary_initialization_deactivates_startup')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native frontend identity logout failed')
    for key in FALSE_FIELDS:require(r[key] is False,'frontend logout scope overclaim: '+key)
    for key in TRUE_FIELDS:require(r[key] is True,'frontend logout cleanup missing: '+key)
    require([row['profile'] for row in r['profiles']]==list(PROFILES),'frontend identity logout Profiles incomplete')
    for row in r['profiles']:
        for key in ROW_TRUE:require(row[key] is True,'frontend identity logout evidence missing: '+key)
        require(row['confirmation_results']==[0] and row['native_logout_success_delta']==1 and row['native_initialize_user_indices']==[0],'frontend identity logout native result/order/count differs')
        require(row['native_async_logout_proxy_class']==IDENTITY_PROXY and row['new_destroy_session_proxies']==0,'identity logout must not be mislabeled DestroySession')
    require(r['source_python_state_pairs_match'] is True,'frontend identity logout Profile states differ')
    return dict(status='passed',native_confirmed_identity_logout_profiles=2,full_acceptance=False)

if __name__=='__main__':
    from .frontend_logout_log_contract import audit
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);file=Path(parser.parse_args().report);result=validate(json.loads(file.read_text(encoding='utf-8-sig')));_,logs=audit(file.with_suffix('.log').read_text(encoding='utf-8-sig'));result['expected_native_permission_loss_errors']=logs['expected_native_permission_loss_errors'];print(json.dumps(result))
