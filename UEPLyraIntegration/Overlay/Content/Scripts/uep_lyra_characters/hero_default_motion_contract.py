"""Actual listen-server/client branch, native child forwarding and 3s lifetime."""
import argparse,json,math
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
KINDS=('parent','simple-base','simple','big','explorer-hero','explorer-pawn')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','natural_animation_notify_ingress_tested','footprint_particles_tested','callback_replay','native_timer_properties_written','child_blueprints_modified')
TRUE_FIELDS=('primary_inventory_health_and_physics_unchanged','existing_shooter_child_router_owner_preserved','owned_actors_profiles_roots_and_selectors_restored','descendant_and_downstream_asset_hashes_unchanged','original_downstream_profile_classes_restored')

def validate(r):
    require(r['status']=='passed' and r['error'] is None,'parent motion fixture failed')
    for k in FALSE_FIELDS:require(r[k] is False,'parent motion overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'parent motion cleanup/provenance missing: '+k)
    require(r['role'] in ('server','client') and r['native_is_server'] is (r['role']=='server'),'actual native server/client predicate differs')
    require(r['native_mode']==('ListenServer' if r['role']=='server' else 'Client'),'real listen-server/client world required')
    require([(c['profile'],c['kind']) for c in r['cases']]==[(p,k) for p in ('BlueprintFallback','Python') for k in KINDS],'parent motion family matrix incomplete')
    for c in r['cases']:
        empty=c['kind']=='explorer-hero';client=r['role']=='client' and not empty;calls=4 if client else 2;counts=c['counts'];py=c['profile']=='Python'
        require(c['typed_second_blueprint_caller'] and c['actual_function_owner_preserved'],'native caller or preserved inherited/empty override missing')
        require(counts['python_calls']==(calls if py and not empty else 0) and counts['fallback_calls']==(calls if not py and not empty else 0),'labelled motion Profile did not execute')
        if client:
            for key in ('native_exposed_properties_match_source','native_keep_relative_attachment_matches','same_footstep_reused','native_retrigger_preserved_actor_before_deadline','native_destroyed_after_delay','replacement_is_new_actor','replacement_naturally_destroyed','all_twelve_payloads_match','native_downstream_no_footprint_component'):require(c[key] is True,'native client motion differs: '+key)
            require(c['downstream_calls']==4 and c['native_original_delay_seconds']==3. and math.isfinite(c['native_destruction_elapsed']) and 3.-c['maximum_world_delta']-.001<=c['native_destruction_elapsed']<=3.+2*c['maximum_world_delta']+.15,'native downstream retriggerable delay differs')
            if py:require(counts['spawns']==2 and counts['reuses']==2 and counts['attachments']==2 and counts['forwards']==4 and counts['server_noops']==0,'client motion orchestration counts differ')
        else:
            require(c['no_footstep_spawned_or_forwarded'],'server/empty override produced a footstep')
            if py and not empty:require(counts['server_noops']==2 and counts['spawns']==counts['forwards']==0,'server motion gate differs')
    return dict(status='passed',role=r['role'],native_family_cases=12,native_client_forwarding_cases=10 if r['role']=='client' else 0,full_acceptance=False,network_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
