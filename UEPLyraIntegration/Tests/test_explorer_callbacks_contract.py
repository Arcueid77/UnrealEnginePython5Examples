"""Do not accept direct callback replay or counters without actual GAS/AI/lifecycle."""
import copy,unittest
from test_character_health_changed_contract import case
from uep_lyra_characters.explorer_callbacks_contract import validate,FALSE_FIELDS,TRUE_FIELDS,NAMES

def report():
    r=dict(status='passed',error=None,profile='Python',characters=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for kind,cls in (('hero','B_Hero_Explorer'),('pawn','B_Pawn_Explorer')):
        row=dict(kind=kind,native_class='/ShooterExplorer/Blueprint/'+cls+'.'+cls+'_C',parts_original_entries_and_actors_restored=True,parts=[dict(operation=name,native_callback_count=count,selected_receiver_calls=count,native_delegate_payload_matches=True,native_device_count_matches=True,native_devices_retired=True) for name,count in (('add',1),('remove',1),('remove-again',0))],health=[case(name,'Python') for name in NAMES],health_cleanup_restored=True)
        for name in ('reset','death'):row[name]=dict(native_producer_called=True,selected_event_calls=1,native_clear_calls=1,clear_after_matches_original_guard=True,old_actor_was_original_explorer=True)
        r['characters'].append(row)
    return r
class ExplorerCallbacksContractTests(unittest.TestCase):
    def test_complete_native_callback_matrix(self):self.assertEqual(validate(report())['native_lifecycle_events'],4)
    def test_each_scope_overclaim_is_rejected(self):
        for name in FALSE_FIELDS:
            r=report();r[name]=True
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_all_cleanup_required(self):
        for name in TRUE_FIELDS:
            r=report();r[name]=False
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_callback_without_independent_delegate_is_rejected(self):
        r=report();r['characters'][0]['parts'][0]['native_callback_count']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_remove_again_must_not_retrigger(self):
        r=report();r['characters'][0]['parts'][2]['selected_receiver_calls']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_health_sense_evidence_is_required(self):
        r=report();r['characters'][0]['health'][3]['native_stimuli']=[]
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_lifecycle_to_clear_chain_is_required(self):
        for event in ('reset','death'):
            for field in ('native_producer_called','old_actor_was_original_explorer','clear_after_matches_original_guard'):
                r=report();r['characters'][0][event][field]=False
                with self.subTest(event=event,field=field),self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_or_missing_lifecycle_events_rejected(self):
        for count in (0,2):
            r=report();r['characters'][0]['reset']['selected_event_calls']=count
            with self.assertRaises(RuntimeError):validate(r)
