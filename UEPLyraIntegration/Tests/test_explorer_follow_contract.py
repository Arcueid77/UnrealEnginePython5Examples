"""Reject incomplete actual navigation/teardown and verify observer forwarding."""
import ast,copy,types,unittest
from pathlib import Path
from uep_lyra_world import explorer_follow_contract as contract
from uep_lyra_hud.startup import validation_module

def report(profile):
    waypoint=dict(arrived=True,native_success_delta=1,plans=[dict(partial=False,points=3,length=1600.)],ai_start=[[0.,0.,0.]],ai_end=[[1500.,0.,0.]])
    r=dict(status='passed',error=None,selected_profile=profile,original_tree=contract.TREE,native_level_open_requests=2,selected_class_paths=['original-Explorer'],template_count=6,
        placed_pawns=[dict(cls=contract.PAWN,use_behavior_tree=False) for _ in range(3)],initial_inventory=[dict(definition='original-rifle',count=1)],
        waypoints=[copy.deepcopy(waypoint),copy.deepcopy(waypoint)],late_callbacks_after_travel=0,garbage_collection_requested_frame=100,garbage_collection_checked_frame=160,
        totals=dict(location_tick=6,goto_enter=1,follow_enter=1,goto_success=1,follow_success=1),node_observations=[dict(kind='location',profile=profile,location_mismatches=0,location_samples=3,last_location=[1.,2.,3.],last_player_location=[1.,2.,3.])],
        cancel=dict(moving_before=1,stopped=True,quiet_after_drain=True),restart=dict(running=True,moving=1,native_callbacks_resumed=True,travel_while_move_active=True))
    r.update(dict.fromkeys(contract.FALSE_FIELDS,False))
    r.update(dict.fromkeys(('selectors_restored','templates_and_observers_restored','player_pose_restored','actual_exit_finalizer','original_placed_ai_destroyed_after_travel','original_runtime_nodes_destroyed_after_travel','old_profile_pawns_and_controllers_destroyed','inventory_preserved_after_travel'),True))
    return r

class ExplorerFollowContractTests(unittest.TestCase):
    def test_complete_bounded_semantic_pair(self):
        reports=[report(p) for p in contract.PROFILES];self.assertIs(contract.validate_pair(reports),reports)
    def test_partial_or_missing_real_navigation_is_rejected(self):
        for change in (dict(partial=True),dict(points=1),dict(length=100.)):
            r=report('Python');r['waypoints'][0]['plans'][0].update(change)
            with self.assertRaisesRegex(ValueError,'full route'):contract.validate(r)
        r=report('Python');r['waypoints'][0]['ai_end']=[[0.,0.,0.]]
        with self.assertRaisesRegex(ValueError,'actually move'):contract.validate(r)
    def test_enter_or_failure_only_does_not_prove_move_success(self):
        r=report('Python');r['totals']['follow_success']=0
        with self.assertRaisesRegex(ValueError,'successful navigation'):contract.validate(r)
    def test_wrong_profile_location_and_late_callback_rejected(self):
        for key,value in (('profile','BlueprintFallback'),('location_mismatches',1)):
            r=report('Python');r['node_observations'][0][key]=value
            with self.assertRaises(ValueError):contract.validate(r)
        r=report('Python');r['late_callbacks_after_travel']=1
        with self.assertRaisesRegex(ValueError,'teardown'):contract.validate(r)
    def test_cancel_requires_active_move_then_quiet_and_real_restart(self):
        for category,key,value in (('cancel','moving_before',0),('cancel','quiet_after_drain',False),('restart','native_callbacks_resumed',False),('restart','travel_while_move_active',False)):
            r=report('Python');r[category][key]=value
            with self.assertRaises(ValueError):contract.validate(r)
    def test_template_and_old_world_cleanup_are_required(self):
        for key in ('templates_and_observers_restored','original_placed_ai_destroyed_after_travel','original_runtime_nodes_destroyed_after_travel'):
            r=report('Python');r[key]=False
            with self.assertRaisesRegex(ValueError,'cleanup'):contract.validate(r)
        r=report('Python');r['garbage_collection_checked_frame']=100
        with self.assertRaisesRegex(ValueError,'deferred native GC'):contract.validate(r)
    def test_overclaims_and_unexecuted_node_families_rejected(self):
        for key in contract.FALSE_FIELDS:
            r=report('Python');r[key]=True
            with self.assertRaisesRegex(ValueError,'overclaim'):contract.validate(r)
    def test_normal_play_and_commandlets_cannot_select_follow_probe(self):
        self.assertIsNone(validation_module([]));self.assertIsNone(validation_module(['-run=Py','-UEPExplorerFollowResult=x']))
        self.assertEqual(validation_module(['-UEPExplorerFollowResult=x']),'uep_lyra_world.explorer_follow_validation')

class ObserverForwardingTests(unittest.TestCase):
    def test_original_result_arguments_and_override_are_preserved_once(self):
        source=Path(__file__).parents[1]/'Overlay/Content/Scripts/uep_lyra_world/explorer_follow_validation.py'
        cls=next(n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef) and n.name=='Validation')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='around')
        namespace={'path':lambda n:n.name};exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
        class Node:
            name='native-runtime-node'
        for kind,result in (('follow',True),('follow',False),('location',True),('location',False)):
            owner=types.SimpleNamespace(templates={},observed={});calls=[]
            def original(node,*args):calls.append((node,args));return result
            original.override='exact-original-native-gate';node=Node();payload=object()
            name='tick' if kind=='location' else 'enter'
            wrapped=namespace['around'](owner,kind,name,'Python',original)
            self.assertIs(wrapped(node,payload),result);self.assertEqual(calls,[(node,(payload,))]);self.assertEqual(wrapped.override,original.override)
            self.assertEqual(owner.observed[node.name]['calls'],{name:1})
    def test_fallback_location_is_sampled_after_original_graph_continues(self):
        source=Path(__file__).parents[1]/'Overlay/Content/Scripts/uep_lyra_world/explorer_follow_validation.py'
        cls=next(n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef) and n.name=='Validation')
        methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('around','sample_locations')]
        namespace={'path':lambda n:n.name,'valid':lambda n:n is not None,'vector':list}
        exec(compile(ast.Module(body=methods,type_ignores=[]),str(source),'exec'),namespace)
        class Node:
            name='native-location';value=(0.,0.,0.)
            def get_property(self,name):return self.value
        node=Node();owner=types.SimpleNamespace(templates={},observed={},pose={},pawn=types.SimpleNamespace(get_actor_location=lambda:(1.,2.,3.)))
        def fallback(actor,delta):return True
        fallback.override='exact-native-location-gate'
        wrapped=namespace['around'](owner,'location','tick','BlueprintFallback',fallback)
        self.assertIs(wrapped(node,.016),True)
        node.value=(1.,2.,3.) # The original graph runs after the True return.
        namespace['sample_locations'](owner)
        row=owner.observed[node.name]
        self.assertEqual(row['location_samples'],1);self.assertEqual(row['location_mismatches'],0)
        self.assertEqual(row['last_location'],[1.,2.,3.])

if __name__=='__main__':unittest.main()
