"""Standalone natural phase flow, typed countdown and actual restart acceptance."""
import argparse
import json
from pathlib import Path
from .hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','pie_skip_branch_tested','health_properties_written','ability_callbacks_replayed','native_latent_nodes_replaced','native_phase_parent_replaced')
TRUE_FIELDS=('natural_warmup_and_playing_observed','sanitization_matches_source_rules','countdown_payloads_and_inclusive_zero_match','pregame_effect_removed_before_playing','native_phase_parent_tags_and_cancellation_observed','postgame_immunity_then_block_then_next_tick','actual_server_travel_and_second_natural_round','probe_scope_closed_before_travel','runtime_cdo_fields_and_profile_wrappers_restored','no_fixture_roots_remaining')


def travel_evidence(log):
    positions=[log.find(s) for s in ('LogGameMode: ProcessServerTravel:','LogWorld: SeamlessTravel to:','LogWorld: ----SeamlessTravel finished')]
    return dict(requested=positions[0]>=0,started=positions[1]>=0,finished=positions[2]>=0,ordered=0<=positions[0]<positions[1]<positions[2])


def validate(r,log=None):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in PROFILES and r['native_mode']=='Standalone','native game phase flow failed')
    for k in FALSE_FIELDS:require(r[k] is False,'phase scope overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'phase evidence missing: '+k)
    require(len(r['sanitize_cases'])==4,'phase duration matrix incomplete')
    require([m['magnitude'] for m in r['countdown_messages']]==[2.,1.,0.],'natural countdown sequence differs')
    require(r['postgame_wait_elapsed']>=.23 and r['restart_frame']>r['block_frame'],'source postgame wait/next-tick order missing')
    require(all(r['native_travel_log_evidence'].values()),'native server-travel evidence missing')
    if log is not None:require(travel_evidence(log)==r['native_travel_log_evidence'],'native travel log proof changed')
    return dict(status='passed',profile=r['profile'],sanitize_cases=4,natural_rounds=2,actual_server_travel=True,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);path=Path(p.parse_args().report);print(json.dumps(validate(json.loads(path.read_text(encoding='utf-8-sig')),(path.parent/'jump.log').read_text(encoding='utf-8-sig',errors='replace'))))
