"""Native engine input/GAS/equipment and untouched fallback frame evidence."""
import unittest
from uep_lyra_characters.explorer_input_contract import validate,FALSE_FIELDS,TRUE_FIELDS,ACTIONS,CASES,DEFINITIONS,CLASSES

def report():
    r=dict(status='passed',error=None,profile='Python',characters=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for kind in ('hero','pawn'):
        names={a:'Receiver_'+kind+'_'+a for a in ACTIONS};actor=dict(kind=kind,native_class=CLASSES[kind],native_receiver_names=names,native_profile_method_counts=dict(Python=25,BlueprintFallback=20),input_cases=[])
        for name,action,initial,expected,empty in CASES:
            _,_,magnitude,tag=ACTIONS[action];actor['input_cases'].append(dict(name=name,positive_native_injections=1,native_input_subsystem_used=True,native_bound_receiver=names[action],receiver_is_native_router=True,input_counters=dict(python_calls=1,fallback_calls=0,**{key:int(key==action) for key in ACTIONS}),helper_counters=dict(python_calls=1,fallback_calls=0),inventory=dict(active=expected,items=sorted(DEFINITIONS),slots=[None if i==empty else d for i,d in enumerate(DEFINITIONS)],definition=DEFINITIONS[expected],equipment_instigator_matches=True,equipment_class=DEFINITIONS[expected].replace('/ID_','/B_WeaponInstance_').replace('.ID_','.B_WeaponInstance_')),events=[dict(tag=tag,magnitude=float(magnitude),instigator_null=True,target_null=True,optional_objects_null=True)] if empty is None else [],native_tasks_before=3,native_tasks_after=3,inventory_items_unchanged=True,task_scope_closed=True,no_repeated_or_release_handler=True))
        r['characters'].append(actor)
    return r
class ExplorerInputContractTests(unittest.TestCase):
    def test_complete_two_actor_native_input_matrix(self):self.assertEqual(validate(report())['native_input_cases'],16)
    def test_no_physical_or_replication_or_whole_character_overclaims(self):
        for name in FALSE_FIELDS:
            r=report();r[name]=True
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_all_native_cleanup_required(self):
        for name in TRUE_FIELDS:
            r=report();r[name]=False
            with self.assertRaises(RuntimeError):validate(r)
    def test_input_injection_and_native_receiver_required(self):
        for name,value in (('positive_native_injections',0),('native_input_subsystem_used',False),('receiver_is_native_router',False)):
            r=report();r['characters'][0]['input_cases'][0][name]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_cycle_retains_original_zero_magnitude(self):
        r=report();r['characters'][0]['input_cases'][3]['events'][0]['magnitude']=-1.
        with self.assertRaises(RuntimeError):validate(r)
    def test_empty_default_cycle_does_not_send_event(self):
        r=report();r['characters'][0]['input_cases'][-1]['events']=[{}]
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_equipment_and_item_identity_and_tasks_checked(self):
        for name,value in (('native_tasks_after',4),('inventory_items_unchanged',False),('task_scope_closed',False),('no_repeated_or_release_handler',False)):
            r=report();r['characters'][0]['input_cases'][0][name]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_both_profiles_complete_local_family_checked(self):
        r=report();r['characters'][0]['native_profile_method_counts']['BlueprintFallback']=25
        with self.assertRaises(RuntimeError):validate(r)
