"""Direct and inherited parent routing, recursive primitives and local-player zero."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
KINDS=('parent','simple-base','simple','big','explorer-hero','explorer-pawn','local-parent')
TEAMS=(-10,0,1,255,256,1000)
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','whole_parent_business_migrated','child_blueprints_modified','native_rendering_implementation_changed')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Hero parent stencil fixture failed')
    for key in FALSE_FIELDS:require(r[key] is False,'Hero parent stencil overclaim: '+key)
    for key in ('primary_player_inventory_health_and_stencil_unchanged','existing_shooter_child_router_owner_preserved','owned_contexts_primitives_profiles_roots_and_selectors_restored','original_descendant_file_hashes_unchanged'):require(r[key] is True,'parent stencil cleanup missing: '+key)
    require([(c['profile'],c['kind']) for c in r['cases']]==[(p,k) for p in ('BlueprintFallback','Python') for k in KINDS],'parent stencil family matrix incomplete')
    for c in r['cases']:
        require(c['target_function_is_parent_router'] and c['recursive_child_primitives_present'],'parent inherited function or recursive fixture missing')
        require([v['team'] for v in c['values']]==list(TEAMS),'parent stencil team edge cases missing')
        for v in c['values']:
            require(v['python_calls_delta']==int(c['profile']=='Python') and v['fallback_calls_delta']==int(c['profile']=='BlueprintFallback'),'stencil parent selected Profile did not execute')
            require(v['all_components_match_source'] and v['render_custom_depth_enable_flags_unchanged'] and v['parent_route_delta']==1,'parent stencil decision/setter/profile differs')
        if c['kind']=='local-parent':require(c['native_locally_and_player_controlled'],'owned parent pawn did not exercise local-player zero')
    return dict(status='passed',native_parent_stencil_family_cases=14,whole_parent_business_migrated=False,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
