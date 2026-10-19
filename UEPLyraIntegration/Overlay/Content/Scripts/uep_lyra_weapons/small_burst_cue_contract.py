"""Native particle colors/typed guards, music routing and heal audio/lifetime."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .hero_burst_cue_contract import require,close

HEAL_SOUND='/Game/Audio/MetaSounds/sfx_Heal_nl_metaPreset.sfx_Heal_nl_metaPreset'


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','native small Burst run failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','hardware_audio_playback_tested','callbacks_replayed','native_timer_properties_written','health_properties_written'):require(report[key] is False,'small Burst scope overclaim: '+key)
    for key in ('controlled_edge_spawn_arrays','owned_actors_destroyed','owned_effects_removed','production_profiles_restored','original_health_unchanged','spawner_default_definition_restored','heal_audio_playing_on_later_native_tick','heal_parent_minimum_five_second_lifetime_and_pool_return'):require(report[key] is True,'native small Burst/lifetime/cleanup absent: '+key)
    colors=report['color_cases'];require(Counter(r['kind'] for r in colors)==Counter(pickup=4,grenade=4),'native two-color matrix incomplete')
    require(Counter((r['kind'],r['profile']) for r in colors)==Counter({(k,p):2 for k in ('pickup','grenade') for p in ('BlueprintFallback','Python')}),'both real color Profiles required')
    for row in colors:require(row['entries']==1 and row['native_parent_fx_count']==1 and row['color_valid'] and close(row['color_after'],row['expected_color']),'actual parent-spawned Niagara/source color differs')
    melee=report['melee_cases'];require(len(melee)==4 and Counter(r['player_kind'] for r in melee)==Counter(local=2,remote=2),'native melee matrix incomplete')
    require(Counter((r['player_kind'],r['profile']) for r in melee)==Counter({(k,p):1 for k in ('local','remote') for p in ('BlueprintFallback','Python')}),'both real melee Profiles required')
    for row in melee:
        require(row['entries']==1 and row['music_fire_entries']==int(row['player_kind']=='local'),'real source SendWeaponFire player/context dispatch differs')
        require(abs(row['intensity_after']-(min(1.,row['intensity_before']+.2) if row['player_kind']=='local' else row['intensity_before']))<.0001,'source melee .2 strength differs')
    edges=report['edge_cases'];require(len(edges)==6 and Counter((r['kind'],r['mode']) for r in edges)==Counter({('pickup','null-first'):2,('grenade','null-first'):2,('grenade','wrong-target'):2}),'controlled first-FX and typed-guard matrix incomplete')
    require(Counter((r['kind'],r['mode'],r['profile']) for r in edges)==Counter({(k,m,p):1 for k,m in (('pickup','null-first'),('grenade','null-first'),('grenade','wrong-target')) for p in ('BlueprintFallback','Python')}),'both controlled edge Profiles required')
    for row in edges:require(row['entries']==1 and row['first_color_unchanged'] and row['second_color_unchanged'],'typed cast/first-element policy differs')
    heals=report['heal_cases'];require(len(heals)==4 and [r['native_parent_fx_count'] for r in heals]==[1,1,2,2] and all(r['entries']==1 and r['native_audio_playing'] and r['native_audio_sound']==HEAL_SOUND for r in heals),'real native heal audio component Play/retrigger or source append-only results differs')
    require([r['profile'] for r in heals]==['BlueprintFallback','Python','BlueprintFallback','Python'],'both initial and repeated heal Profiles required')
    managers=report['manager_cases'];require(Counter(r['kind'] for r in managers)==Counter(('pickup','melee','grenade','heal')),'four real default manager tags required')
    for row in managers:require(row['profile']=='Python' and row['entries']==1,'real default Python Cue dispatch differs')
    return dict(status='passed',native_color_calls=8,native_melee_calls=4,controlled_edge_calls=6,native_heal_calls=4,real_default_manager_tags=4,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
