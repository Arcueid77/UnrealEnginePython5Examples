"""Original spline geometry, native curves/clock, movement/scale and pool reuse."""
import argparse,json
from pathlib import Path
from .hero_burst_cue_contract import require
CASES=(('short-none',.3,'None',False),('long-none',.8,'None',False),('socket-pelvis',.6,'pelvis',False),('missing-socket',.6,'UEP_NoSocket',False),('switch-update',.6,'pelvis',True),('zero-rate',0.,'None',False),('invalid-pawn',.6,'None',False))
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','timeline_callbacks_replayed','python_timeline_clock_added','native_timeline_private_properties_written')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'collect Cue native fixture failed')
    for key in FALSE_FIELDS:require(r[key] is False,'collect Cue overclaim: '+key)
    for key in ('primary_player_inventory_health_and_transform_unchanged','owned_actor_roots_and_class_selectors_restored','native_cue_recycling_and_timer_cleanup_enabled'):require(r[key] is True,'collect Cue cleanup missing: '+key)
    require([(c['profile'],c['name']) for c in r['cases']]==[(p,v[0]) for p in ('BlueprintFallback','Python') for v in CASES],'collect Cue native matrix incomplete')
    for c in r['cases']:
        require(c['native_manager_executed_exact_class'] and c['source_target_collision_and_lifespan_set'] and c['pool_actor_alive_hidden_ownerless_and_resource_free'],'collect Cue manager/target/pool behavior differs')
        if c['name']=='invalid-pawn':require(c['invalid_pawn_no_timeline'] and c['self_lifespan_cleared'],'collect Cue invalid Pawn branch differs');continue
        require(c['original_spline_points_and_world_attachment_match'] and c['native_play_rate_matches_source'],'collect Cue native setup differs')
        require(c['native_timeline_length']==5.,'original collect Cue native Timeline length differs')
        if c['name']=='zero-rate':require(c['zero_rate_preserves_stalled_native_timeline'],'collect Cue zero rate behavior differs');continue
        for key in ('all_samples_match_native_spline_distance_and_uniform_scale','all_samples_match_original_native_curves','native_finished_hides_then_retains_self_three_seconds','pending_profile_switch_used_current_update_and_finish'):require(c[key] is True,'collect Cue timeline observation missing: '+key)
        require(c['samples']>=3 and c['actual_native_update_count']>=3 and c['native_finish_count']==1,'collect Cue natural native update/finish counts differ')
    return dict(status='passed',native_collect_cue_cases=14,whole_collect_cue_business_migrated=True,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
