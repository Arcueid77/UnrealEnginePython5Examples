"""Native weak tags, geometric/RNG family, popup/decal/lens/RPC and timer gate."""
import argparse
from collections import Counter
import json
import struct
from pathlib import Path


def require(value,text):
    if not value:raise RuntimeError(text)


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','native character damage run failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','health_properties_written','native_rng_values_injected','rpc_function_overridden','parent_effects_disabled','native_timer_properties_written'):
        require(report[key] is False,'damage scope overclaim: '+key)
    for key in ('production_profiles_restored','music_fields_and_providers_restored','probe_unrooted','original_health_unchanged','owned_material_roots_released','owned_decal_components_removed','number_pop_state_restored'):
        require(report[key] is True,'damage cleanup absent: '+key)
    weak=report['weak_cases'];require(len(weak)==24,'native weak-spot direct/BP/Profile matrix incomplete')
    for row in weak:require(row['actual']==row['expected'] and row['dispatch_entries']==1,'exact tagged-material weak spot differs')
    selections=report['selector_cases'];require(len(selections)>=64,'native selector boundary/range matrix incomplete')
    require({r['profile'] for r in selections}=={'Python','BlueprintFallback'} and {r['path'] for r in selections}=={'direct','blueprint'},'real native selector callers missing')
    for row in selections:
        require(row['returned'] in row['allowed'] and row['actual_native_group']==row['expected_group'] and row['actual_positive']==row['expected_positive'] and row['dispatch_entries']==1,'native geometric decision/RNG data family differs')
    parents=report['parent_cases'];require(len(parents)==8,'native parent/context/material matrix incomplete')
    for row in parents:
        require(row['native_return'] is False and row['burst_entries']==row['execute_entries']==row['rpc_body_entries']==1,'native parent/RPC/body dispatch differs')
        require(row['actual_messages']==1 and row['message_target_matches'] and row['number_pop_added']==1 and row['native_pop_value']==row['expected_pop_value'],'actual typed message or number-pop backend differs')
        # UNiagaraDataInterfaceArrayFloat4 stores FVector4f; its public getter
        # expands that data back to FVector4. Compare the actual native rounding.
        expected_position=list(struct.unpack('<3f',struct.pack('<3f',*row['expected_pop_location'])))
        require(row['native_pop_location']==expected_position,'native number pop used cue/impact location instead of float32 hit Location')
        require(row['context_instigator_is_local_state'] and row['selected_montage_in_allowed_set'] and row['native_character_montage_playing'],'native context/animation/RPC primitive missing')
        require(row['actual_new_decals']==(1 if row['surface'] else 0),'source valid non-default surface decal rule differs')
        if row['actual_new_decals']:
            require(row['decal_attachment_and_native_properties_match'],'actual native decal transform/material/fade differs')
        if not row['cue_instigator_decoy']:require(row['actual_lens_updates']>=1 and row['actual_native_lens_parameters_match'],'actual native camera-lens Niagara writes missing')
    timers=report['timer_cases'];require(Counter(r['profile'] for r in timers)==Counter(('Python','BlueprintFallback')),'native latent lifetime Profiles missing')
    for row in timers:require(row['visible_before_deadline'] and row['native_recycled_after_minimum_lifetime'] and row['elapsed']>=5.,'original native minimum five-second lifetime changed')
    require(report['natural_manager_python_burst_entries']==1 and report['natural_manager_python_execute_entries']==1 and report['natural_manager_typed_message_entries']==1,'actual Cue manager default Python path missing')
    return dict(status='passed',weak_native_cases=24,native_selector_cases=len(selections),native_parent_cases=8,native_lifetime_profiles=2,real_manager_cases=1,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
