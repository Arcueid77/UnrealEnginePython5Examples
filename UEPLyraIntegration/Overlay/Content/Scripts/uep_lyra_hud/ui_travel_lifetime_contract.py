"""Native settings reopen before and after confirmed frontend-map travel."""
import argparse,json
from pathlib import Path
from uep_lyra_hud.menu_travel_contract import validate as travel_validate,require
FORBIDDEN=('callbacks_replayed','settings_back_api_called','travel_adapter_called_by_probe','configuration_store_written_by_python','physical_input_tested','full_acceptance','network_acceptance','packaged_runtime')
def validate(report):
    require(report['status']=='passed' and report['error'] is None,'UI travel lifetime observation failed')
    for key in FORBIDDEN:require(report[key] is False,'UI travel lifetime shortcut: '+key)
    travel_validate(report['travel']);require(report['travel']['profile']==report['profile'],'Travel profile differs')
    rows=report['cases'];require([(r['origin'],r['cycle']) for r in rows]==[('game',0),('game',1),('frontend',0),('frontend',1)],'Two real reopen cycles on each side of travel required')
    for row in rows:
        require(row['profile']==report['profile'] and row['parent_focus'] and row['settings_focus'],'Native UI ownership/focus differs')
        require(row['parent_selected_callbacks']==row['back_selected_callbacks']==1 and row['parent_other_callbacks']==row['back_other_callbacks']==0,'Native routed callback duplicated/crossed profile')
        require(row['screen_profile_matches'] and row['back_profile_matches'] and row['settings_closed'] and row['settings_focus_removed'],'Native settings Back did not restore state')
        require(row['settings_object'] and row['controller'] and row['world'],'Native object identities required')
    require(rows[0]['world']==rows[1]['world']!=rows[2]['world']==rows[3]['world'],'Actual old/new worlds required')
    require(rows[0]['world']==report['travel']['old_world_path'] and rows[2]['world']==report['travel']['new_world_path'],'Settings cycles must belong to the observed native travel worlds')
    require(rows[0]['controller']==rows[1]['controller']!=rows[2]['controller']==rows[3]['controller'],'Actual controller replacement required')
    for key in ('old_ui_naturally_deactivated_before_probe_cleanup','old_travel_observers_unbound','old_travel_callbacks_quiet_after_new_ui','new_frontend_reactivated_after_back','owned_ui_unmounted_and_unrooted','selectors_and_class_roots_restored'):
        require(report[key] is True,'UI travel cleanup missing: '+key)
    return dict(status='passed',profile=report['profile'],native_settings_cycles=4,native_confirmed_map_travels=1,full_acceptance=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
