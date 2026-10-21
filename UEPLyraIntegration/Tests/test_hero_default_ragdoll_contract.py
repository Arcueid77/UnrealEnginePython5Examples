import copy,math,unittest
from uep_lyra_characters.hero_default_ragdoll_contract import KINDS,SCENARIOS,FALSE_FIELDS,validate

def report():
    r=dict(status='passed',error=None,cases=[],primary_player_inventory_health_and_physics_unchanged=True,existing_shooter_child_router_owner_preserved=True,owned_actors_controllers_profiles_roots_and_selectors_restored=True,original_descendant_file_hashes_unchanged=True,original_physics_source_hashes_unchanged=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for p in ('BlueprintFallback','Python'):
        for k in KINDS:
            for n in SCENARIOS:
                v=[0.,0.,0.] if n=='stationary' else [150.,50.,100.];strength=0. if n=='zero-strength' else 300.;mag=math.sqrt(sum(x*x for x in v));imp=[x+(x/mag*strength if mag else 0.) for x in v];calls=2 if n=='repeat' else 1;after=dict(velocity=[x+y*calls for x,y in zip([3.,4.,5.],imp)],simulating=True,collision_profile='Ragdoll')
                r['cases'].append(dict(profile=p,kind=k,name=n,calls=calls,route_delta=calls,python_calls_delta=calls if p=="Python" else 0,fallback_calls_delta=calls if p=="BlueprintFallback" else 0,target_function_is_parent_router=True,single_body_native_control=True,native_ai_possession=True,owned_strength_restored_before_destroy=True,pawn_hidden_unchanged=True,input_velocity=v,strength=strength,native_launch_producer=n!='stationary',native_before=dict(velocity=[3.,4.,5.]),native_after=after,native_after_physics_step=copy.deepcopy(after),native_physics_frames_elapsed=2,trace=['collision','simulation','impulse']*calls,python_impulse=imp))
    return r

class HeroDefaultRagdollContractTests(unittest.TestCase):
    def test_fallback_label_without_fallback_execution_rejected(self):
        r=report();v=r['cases'][0];v['python_calls_delta']=1;v['fallback_calls_delta']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_complete_native_family_matrix(self):self.assertEqual(validate(report())['native_parent_ragdoll_cases'],48)
    def test_non_velocity_change_impulse_rejected(self):
        r=report();r['cases'][1]['native_after_physics_step']['velocity'][0]*=.5
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_inherited_case_rejected(self):
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_movement_simulation_or_cleanup_missing_rejected(self):
        for key in ('native_launch_producer','native_ai_possession','owned_strength_restored_before_destroy','target_function_is_parent_router'):
            r=report();r['cases'][1][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_nan_or_wrong_repeat_delta_rejected(self):
        for value in (float('nan'),-999.):
            r=report();r['cases'][3]['native_after_physics_step']['velocity'][0]=value
            with self.subTest(value=value),self.assertRaises(RuntimeError):validate(r)
    def test_order_and_scope_overclaim_rejected(self):
        r=report();r['cases'][24]['trace'].reverse()
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['original_multibody_physics_visuals_verified']=True
        with self.assertRaises(RuntimeError):validate(r)
