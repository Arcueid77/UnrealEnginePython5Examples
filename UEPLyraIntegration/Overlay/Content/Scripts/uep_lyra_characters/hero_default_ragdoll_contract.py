"""Parent virtual calls, native movement input and quantitative velocity change."""
import argparse,json,math
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
KINDS=('parent','simple-base','simple','big','explorer-hero','explorer-pawn')
SCENARIOS=('stationary','moving','zero-strength','repeat')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','whole_parent_business_migrated','child_blueprints_modified','physics_properties_written_directly','native_chaos_implementation_changed','original_multibody_physics_visuals_verified')

def close(a,b):return len(a)==len(b) and all(math.isfinite(x) and math.isfinite(y) and abs(x-y)<.08 for x,y in zip(a,b))

def validate(r):
    require(r['status']=='passed' and r['error'] is None,'parent ragdoll native fixture failed')
    for k in FALSE_FIELDS:require(r[k] is False,'parent ragdoll overclaim: '+k)
    for k in ('primary_player_inventory_health_and_physics_unchanged','existing_shooter_child_router_owner_preserved','owned_actors_controllers_profiles_roots_and_selectors_restored','original_descendant_file_hashes_unchanged','original_physics_source_hashes_unchanged'):require(r[k] is True,'ragdoll cleanup/provenance missing: '+k)
    require([(v['profile'],v['kind'],v['name']) for v in r['cases']]==[(p,k,n) for p in ('BlueprintFallback','Python') for k in KINDS for n in SCENARIOS],'parent ragdoll family matrix incomplete')
    for v in r['cases']:
        calls=2 if v['name']=='repeat' else 1
        require(v['calls']==calls and v['route_delta']==calls and v['target_function_is_parent_router'],'parent ragdoll route differs')
        require(v['single_body_native_control'] and v['native_ai_possession'] and v['owned_strength_restored_before_destroy'] and v['pawn_hidden_unchanged'],'parent native physics preparation or cleanup differs')
        velocity=v['input_velocity'];magnitude=math.sqrt(sum(x*x for x in velocity));strength=v['strength']
        require(all(math.isfinite(x) for x in velocity+[strength]),'invalid native physics input')
        require((magnitude<.001) if v['name']=='stationary' else v['native_launch_producer'] and velocity[0]>100.,'native movement producer absent')
        require(strength==0. if v['name']=='zero-strength' else strength>0.,'strength scenario differs')
        impulse=[x+(x/magnitude*strength if magnitude*magnitude>.0001 else 0.) for x in velocity]
        require(close(v['native_after_physics_step']['velocity'],[x+y*calls for x,y in zip(v['native_before']['velocity'],impulse)]),'native bVelChange impulse differs after physics tick')
        for state in (v['native_after'],v['native_after_physics_step']):require(state['simulating'] and state['collision_profile']=='Ragdoll','native physics simulation/collision missing')
        require(v['native_physics_frames_elapsed']>=2,'physics tick observation missing')
        if v['profile']=='Python':require(v['trace']==['collision','simulation','impulse']*calls and close(v['python_impulse'],impulse),'Python source order/formula differs')
    return dict(status='passed',native_parent_ragdoll_cases=48,full_acceptance=False,whole_parent_business_migrated=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
