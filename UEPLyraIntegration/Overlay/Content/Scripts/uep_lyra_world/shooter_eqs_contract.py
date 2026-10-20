"""Real EQS contexts/generator, typed query results and original state restoration."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','health_properties_written','query_callbacks_replayed','native_query_scheduler_replaced')
TRUE_FIELDS=('native_async_queries_completed','all_query_results_match_source_rules','all_context_and_generator_callbacks_observed','source_enum_and_fresh_local_lists_preserved','blackboard_team_inventory_and_actor_fields_restored','profile_wrappers_cdo_fields_and_roots_restored','original_live_player_health_unchanged')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback') and r['mode'] in ('tdm','cp') and r['native_mode']=='Standalone','native shooter EQS failed')
    for k in FALSE_FIELDS:require(r[k] is False,'EQS scope overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'EQS evidence missing: '+k)
    counts={k:sum(c['context']==k for c in r['cases']) for k in ('points','enemy','weapon','enemies')}
    require(counts['points']>=3 and counts['enemy']>=4 and counts['weapon']>=5 and counts['enemies']>=4 and r['diagnostic_fallbacks']==0,'native EQS matrix incomplete')
    if r['mode']=='cp':require(r['actual_control_point_count']>=3,'actual CP context fixtures missing')
    return dict(status='passed',profile=r['profile'],mode=r['mode'],native_queries=len(r['cases']),full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
