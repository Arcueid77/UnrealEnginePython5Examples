"""Native equipment instances/actors and existing parent inheritance routes."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
KINDS=('parent','simple-base','simple','big','explorer-hero','explorer-pawn')
SCENARIOS=('empty-manager','equipped-types','repeat','already-hidden','empty-weapon-instance','missing-manager')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','whole_parent_business_migrated','child_blueprints_modified','equipment_private_properties_written','native_equipment_spawn_implementation_changed')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Hero parent equipment fixture failed')
    for key in FALSE_FIELDS:require(r[key] is False,'Hero parent equipment overclaim: '+key)
    for key in ('primary_player_inventory_health_and_equipment_unchanged','existing_shooter_child_router_owner_preserved','owned_actors_equipment_instances_profiles_roots_and_selectors_restored','original_descendant_file_hashes_unchanged'):require(r[key] is True,'parent equipment cleanup missing: '+key)
    require([(c['profile'],c['kind']) for c in r['cases']]==[(p,k) for p in ('BlueprintFallback','Python') for k in KINDS],'parent equipment family matrix incomplete')
    for c in r['cases']:
        require(c['target_function_is_parent_router'] and c['native_manager_equipped_real_instances_and_actors'],'parent equipment route/native producer missing')
        require([v['name'] for v in c['scenarios']]==list(SCENARIOS),'parent equipment scenario matrix incomplete')
        for v in c['scenarios']:require(v['all_weapon_actors_hidden'] and v['nonweapon_actor_visibility_unchanged'] and v['pawn_visibility_and_equipment_identity_unchanged'] and v['route_delta']==v['calls'],'parent equipment filter/visibility/identity differs')
        require(c['native_unequip_destroyed_all_fixture_spawned_actors'],'parent equipment native cleanup leaked actors')
    return dict(status='passed',native_parent_equipment_family_cases=12,native_equipment_scenarios=72,whole_parent_business_migrated=False,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
