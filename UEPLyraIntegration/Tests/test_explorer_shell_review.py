"""Do not retain source shells if business or event payload forwarding appears."""
import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('explorer_shell_review_test',Path(__file__).resolve().parents[1]/'Tools/explorer_shell_review.py');review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
def actor():
    return {'EventGraph':[dict(node='Event',cls='K2Node_Event',pins=[dict(name='then',direction=1,category='exec',links=['Parent.execute']),dict(name='DeltaSeconds',direction=1,category='real',links=['Parent.DeltaSeconds'])]),dict(node='Parent',cls='K2Node_CallParentFunction',function=dict(name='ReceiveTick'),pins=[dict(name='execute',direction=0,category='exec',links=['Event.then']),dict(name='DeltaSeconds',direction=0,category='real',links=['Event.DeltaSeconds'])])]}
class ExplorerShellReviewTests(unittest.TestCase):
    def test_parent_forwarder_has_no_independent_business(self):self.assertEqual(review.classify_actor(actor())['independent_business_nodes'],0)
    def test_real_business_node_rejected(self):
        data=actor();data['EventGraph'].append(dict(node='Business',cls='K2Node_CallFunction',pins=[]))
        with self.assertRaises(RuntimeError):review.classify_actor(data)
    def test_dropped_event_argument_rejected(self):
        data=actor();data['EventGraph'][1]['pins'][1]['links']=[]
        with self.assertRaises(RuntimeError):review.classify_actor(data)
    def test_new_parent_business_forwarder_rejected(self):
        data=actor();data['EventGraph'][1]['function']['name']='RunNewBusiness'
        with self.assertRaises(RuntimeError):review.classify_actor(data)
    def test_unconnected_prompt_cast_retained_but_new_execution_rejected(self):
        # The pure classifier's prompt edge tests use a small source-shaped graph.
        rows=[dict(node='K2Node_Event_'+str(i),cls='K2Node_Event',pins=[]) for i in range(4)];rows.extend([dict(node='K2Node_DynamicCast_0',cls='K2Node_DynamicCast',pins=[dict(name='then',direction=1,category='exec',links=[])]),dict(node='K2Node_CallFunction_1',cls='K2Node_CallFunction',function=dict(name='GetDataObject'),pins=[]),dict(node='K2Node_CallFunction_3',cls='K2Node_CallFunction',function=dict(name='GetComponentByClass'),pins=[])]);self.assertTrue(review.classify_prompt({'EventGraph':rows})['unused_bind_result_and_unconnected_cast_branches']);rows[4]['pins'][0]['links']=['NewBusiness.execute']
        with self.assertRaises(RuntimeError):review.classify_prompt({'EventGraph':rows})
