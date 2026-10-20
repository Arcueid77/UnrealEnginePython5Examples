"""Actual replay component/HUD/UMG ticks and native pointer seek acceptance."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_pointer_input_tested','native_async_callbacks_replayed','health_properties_written','cross_travel_actor_health_identity_claimed')
TRUE_FIELDS=('early_runtime_profiles_selected_before_natural_beginplay','natural_regular_controller_component_beginplay','native_wrong_controller_owner_no_effect','native_idle_umg_tick_zero_percent','native_zero_width_pointer_handled','native_zero_divide_warning_preserved','natural_replay_controller_component_creates_hud','native_replay_hud_construct_activates','native_umg_tick_percent_matches_actual_getter_samples','native_slate_pointer_events_seek_forward_and_back','native_original_handled_reply_preserved','native_real_recordings_query_and_playback','native_playback_stopped','owned_roots_profiles_settings_input_and_fixture_actors_restored')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'native replay runtime failed')
    for f in FALSE_FIELDS:require(r[f] is False,'replay runtime overclaim: '+f)
    for f in TRUE_FIELDS:require(r[f] is True,'native replay runtime observation missing: '+f)
    require(r['synthetic_slate_pointer_inputs']==[.75,.2] and r['native_handled_replies']==[True,True] and len(r['native_seek_samples'])==2,'native pointer seek matrix incomplete')
    require(r['native_tick_samples']>=3 and r['direct_zero_width_slate_pointer_input'] is True,'native actual tick/zero-width coverage missing')
    return dict(status='passed',native_replay_runtime_profile=r['profile'],native_seek_inputs=2,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
