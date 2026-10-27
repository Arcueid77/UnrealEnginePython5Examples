"""Reject incomplete/forged network proof; host fixtures are not native runs."""
import copy,unittest
from uep_lyra_abilities import explorer_actions_network_contract as contract
from uep_lyra_hud.startup import validation_module

def group(profile):
    reports={}
    prefix='python' if profile=='Python' else 'fallback'
    for peer in ('server',*contract.PEERS):
        r=dict.fromkeys(contract.FALSE_FIELDS,False)
        r.update(status='passed',error=None,peer=peer,profile=profile,cases=[],selectors_restored=True,observers_restored=True,duration_scope_closed=True,actual_exit_finalizer=True,poses_restored=True,shutdown_active_progress=0,player_id=contract.PEERS.index(peer)+1 if peer in contract.PEERS else 0)
        reports[peer]=r
    inventories={p:{} for p in contract.PEERS}
    for owner,kind in contract.CASES:
        before=copy.deepcopy(inventories);templates=[dict(definition='rock',count=1)] if kind=='collect' else []
        after=contract.expected_inventory(before[owner],templates)
        for peer,r in reports.items():
            foreign=contract.PEERS[1-contract.PEERS.index(owner)]
            row=dict(owner=owner,kind=kind,target='placed-'+kind+owner,target_class=contract.TARGETS[kind],pickup_templates=templates,
                inventory_before=before[owner if peer=='server' else peer],inventory_after=after if peer in ('server',owner) else before[peer],duration_delta=1 if peer==owner else 0)
            if peer in ('server',owner):
                d={p+'_'+n:0 for p in ('python','fallback') for n in ('activate','end','press')}
                d.update({prefix+'_activate':1,prefix+'_end':1,'authority':int(peer=='server'),'client':int(peer!='server'),'native_duration_messages':int(peer!='server')})
                role=3 if peer=='server' else 2;instance='action-'+peer+owner+kind
                row.update(role=role,pawn='pawn-'+owner,events=[dict(instance=instance,authority=peer=='server',instigator='pawn-'+owner,target=row['target'],
                    native_start=dict(instance=instance,active=True,active_tasks=0,spec_active_counts=[1]))],action_deltas=[d],native_tasks_closed=True,
                    native_completion=[dict(instance=instance,active=False,active_tasks=0,spec_active_counts=[0])])
                if peer=='server':row.update(other_inventory_before=before[foreign],other_inventory_after=before[foreign],target_expired=kind=='collect',target_preserved=kind=='sit')
                else:row.update(input_asset='/ShooterExplorer/Input/Actions/IA_Interact.IA_Interact',interactor_press_deltas=[{prefix+'_press':1,('fallback' if prefix=='python' else 'python')+'_press':0}],durations=[dict(instigator='pawn-'+owner,duration=.5)],progress_matched_original=True,progress_completed=True)
            else:row['own_activation_delta']=0
            r['cases'].append(row)
        inventories[owner]=after
    return reports

class ExplorerActionsNetworkContractTests(unittest.TestCase):
    def setUp(self):self.groups=[group(p) for p in contract.PROFILES]
    def test_complete_original_python_protocol(self):contract.validate_pair(self.groups)
    def test_authority_and_client_are_both_required(self):
        for peer,value in (('server',2),('A',3)):
            g=copy.deepcopy(self.groups[1]);g[peer]['cases'][0]['role']=value
            with self.assertRaisesRegex(ValueError,'authority role'):contract.validate(g)
    def test_explicit_duration_helper_is_not_prediction(self):
        g=copy.deepcopy(self.groups[1]);g['A']['cases'][0]['action_deltas'][0]['client']=0
        with self.assertRaisesRegex(ValueError,'predicted/authority'):contract.validate(g)
    def test_remote_message_inventory_or_activation_rejected(self):
        for key,value in (('duration_delta',1),('inventory_after',{'rock':1}),('own_activation_delta',1)):
            g=copy.deepcopy(self.groups[1]);g['B0']['cases'][0][key]=value
            with self.assertRaisesRegex(ValueError,'owner boundary'):contract.validate(g)
    def test_owner_replica_must_match_native_inventory(self):
        g=copy.deepcopy(self.groups[1]);g['A']['cases'][0]['inventory_after']={}
        with self.assertRaisesRegex(ValueError,'owner-only replication'):contract.validate(g)
    def test_duplicate_input_and_fallback_leak_rejected(self):
        for key,value in (('python_activate',2),('fallback_activate',1)):
            g=copy.deepcopy(self.groups[1]);g['A']['cases'][0]['action_deltas'][0][key]=value
            with self.assertRaisesRegex(ValueError,'activation/client'):contract.validate(g)
    def test_server_native_completion_can_precede_its_local_montage_callback(self):
        for profile_index,prefix in ((0,'fallback'),(1,'python')):
            g=copy.deepcopy(self.groups[profile_index]);g['server']['cases'][0]['action_deltas'][0][prefix+'_end']=0
            contract.validate(g)
            g['server']['cases'][0]['native_completion']=[]
            with self.assertRaises(ValueError):contract.validate(g)
    def test_missing_client_montage_completion_cannot_use_server_native_end(self):
        g=copy.deepcopy(self.groups[1]);g['A']['cases'][0]['action_deltas'][0]['python_end']=0
        with self.assertRaises(ValueError):contract.validate(g)
    def test_native_completion_must_match_actual_action_and_closed_spec(self):
        for field,value in (('instance','foreign'),('active',True),('active_tasks',1),('spec_active_counts',[1])):
            g=copy.deepcopy(self.groups[1]);g['server']['cases'][0]['native_completion'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):contract.validate(g)
        g=copy.deepcopy(self.groups[1]);g['server']['cases'][0]['events'][0]['native_start']['active']=False
        with self.assertRaises(ValueError):contract.validate(g)
    def test_native_payload_and_duration_required(self):
        g=copy.deepcopy(self.groups[1]);g['A']['cases'][0]['events'][0]['instigator']='foreign'
        with self.assertRaisesRegex(ValueError,'payload/role'):contract.validate(g)
        g=copy.deepcopy(self.groups[1]);g['A']['cases'][0]['durations'][0]['duration']=.4
        with self.assertRaisesRegex(ValueError,'native duration'):contract.validate(g)
    def test_cleanup_and_scope_are_fail_closed(self):
        for key in ('selectors_restored','observers_restored','duration_scope_closed','actual_exit_finalizer','poses_restored'):
            g=copy.deepcopy(self.groups[1]);g['A'][key]=False
            with self.assertRaisesRegex(ValueError,'cleanup missing'):contract.validate(g)
        for key in contract.FALSE_FIELDS:
            g=copy.deepcopy(self.groups[1]);g['server'][key]=True
            with self.assertRaisesRegex(ValueError,'scope overclaim'):contract.validate(g)
    def test_both_owner_sequences_required(self):
        g=copy.deepcopy(self.groups[1]);g['server']['cases'].pop()
        with self.assertRaisesRegex(ValueError,'sequence incomplete'):contract.validate(g)
    def test_normal_startup_and_commandlets_stay_ordinary(self):
        flag='-UEPExplorerActionsNetworkResult=result.json'
        self.assertIsNone(validation_module([]));self.assertIsNone(validation_module(['-run=Py',flag]))
        self.assertEqual(validation_module([flag]),'uep_lyra_abilities.explorer_actions_network_validation')

if __name__=='__main__':unittest.main()
