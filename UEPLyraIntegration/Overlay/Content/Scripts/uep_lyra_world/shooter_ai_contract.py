"""Native AI tree schedules, GAS delivery, decision parity and owned cleanup."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','health_properties_written','native_bt_scheduler_replaced','native_async_factories_replaced','physical_aim_accuracy_tested')
TRUE_FIELDS=('natural_controller_ready_possess_and_team_observed','passive_empty_overrides_preserved','native_ammo_blackboard_cases_match','native_focus_set_and_clear_match','native_weapon_query_and_slot_cases_match','native_gas_reload_slot_fire_payloads_observed','native_tree_service_callbacks_and_intervals_observed','native_unpossess_clears_enemy_and_stops_brain','native_repossess_and_team_observer_observed','inventory_slots_stats_and_transforms_restored','profile_selectors_wrappers_and_roots_restored','probe_gameplay_event_actions_closed','original_live_player_health_unchanged')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback') and r['mode'] in ('tdm','cp') and r['native_mode']=='Standalone','native shooter AI failed')
    for k in FALSE_FIELDS:require(r[k] is False,'AI scope overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'AI evidence missing: '+k)
    require(len(r['ammo_cases'])>=4 and len(r['weapon_cases'])>=5,'AI decision matrix incomplete')
    require(r['diagnostic_fallbacks']==0 and r['native_tree_tick_samples']>=3,'AI used fallback diagnostics or synthetic tree ticks')
    if r['mode']=='cp':require(r['natural_controller_class'].endswith('B_AI_Controller_LyraShooter_ControlPoint_C'),'CP child controller not observed')
    return dict(status='passed',profile=r['profile'],mode=r['mode'],ammo_cases=len(r['ammo_cases']),weapon_cases=len(r['weapon_cases']),full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
