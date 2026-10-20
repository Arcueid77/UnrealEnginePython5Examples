"""Require original compiled StateTree execution separately from event fixtures."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','health_properties_written','native_async_callbacks_replayed','python_latent_clock_added','unused_nodes_claimed_as_compiled_tree_execution','successful_navmesh_location_path_tested')
TRUE_FIELDS=('original_compiled_tree_executed','native_global_location_matches_player_zero','native_goto_and_follow_callbacks_observed','native_tree_stopped','native_evaluator_event_location_matches','native_delay_enter_tick_flags_and_two_completions_observed','owned_objects_roots_profiles_and_templates_restored','initial_gameplay_health_unchanged')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'Explorer StateTree runtime failed')
    for field in FALSE_FIELDS:require(r[field] is False,'Explorer scope overclaim: '+field)
    for field in TRUE_FIELDS:require(r[field] is True,'Explorer native observation missing: '+field)
    counts=r['compiled_tree_counts']
    require(counts['location_tick']>=3 and counts['goto_enter']>=1 and counts['follow_enter']>=1,'original tree node dispatch missing')
    require(counts['goto_success']+counts['goto_failed']>=1 and counts['follow_success']+counts['follow_failed']>=1,'original tree native move callbacks missing')
    require(r['direct_event_nodes']==['eval','delay','goto','follow'] and r['compiled_tree_nodes']==['location','goto','follow'],'direct events and actual tree execution must be distinguished')
    for kind in ('goto','follow'):require(r['direct_move_counts'][kind]==dict(enter=1,success=1,failed=0),'native already-at-goal success missing: '+kind)
    delay=r['delay_counts'];require(delay['enter']==1 and delay['enter_done']==1 and delay['tick']>=2 and delay['tick_done']==1,'native delay completion matrix differs')
    require(r['delay_elapsed']>=r['delay_duration']*2-.04,'native enter/tick delays did not both elapse')
    return dict(status='passed',profile=r['profile'],compiled_tree_nodes=r['compiled_tree_nodes'],full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
