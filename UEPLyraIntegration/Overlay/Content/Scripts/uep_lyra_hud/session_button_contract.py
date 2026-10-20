"""Native session button labels/materials and real latent animation completion."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_mouse_touch_or_button_input_tested','audio_playback_tested','native_latent_or_finished_callbacks_replayed','health_properties_written','browser_entry_or_join_migrated')
ROW_TRUE=('native_construct_and_preconstruct','native_five_ftext_histories_preserved','native_six_target_reset_preserves_unused_label_scalars','native_font_reset_function','native_texture_identity_and_null_retention','native_only_border_disabled_and_blocked_handlers','native_enabled_selection_and_hover_directions','native_mid_animation_click_continuity','native_actual_finished_then_reverse_and_quiet')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native session button failed')
    for field in FALSE_FIELDS:require(r[field] is False,'session button scope overclaim: '+field)
    require(r['owned_roots_profiles_and_gameplay_health_restored'] is True,'session button cleanup failed')
    require([row['profile'] for row in r['profiles']]==list(PROFILES),'session button Profiles incomplete')
    require(r['direct_blueprint_event_inputs']==['BP_OnHovered','BP_OnUnhovered'],'direct hover test inputs must be disclosed')
    for row in r['profiles']:
        for field in ROW_TRUE:require(row[field] is True,'native session button observation missing: '+field)
        require(row['native_finished_callbacks']==1,'native session button Finished count differs')
    require(r['source_python_state_pairs_match'] is True,'session button Profile states differ')
    return dict(status='passed',native_session_button_profiles=2,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
