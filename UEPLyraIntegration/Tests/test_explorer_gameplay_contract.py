"""Native-entry snapshot and semantic rejection models; no runtime acceptance."""
import ast,base64,copy,tempfile,types,unittest
from pathlib import Path
from uep_lyra_abilities import explorer_gameplay_contract as contract
from uep_lyra_hud.startup import validation_module

class Native:
    def __init__(self,name):self.name=name
    def is_valid(self):return True
    def get_path_name(self):return self.name

def observe_entry(owner,kind,original):
    # Compile the unchanged method in isolation: the containing module needs UE.
    source=Path(__file__).parents[1]/'Overlay/Content/Scripts/uep_lyra_abilities/explorer_gameplay_validation.py'
    module=ast.parse(source.read_text(encoding='utf-8-sig'))
    cls=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='Validation')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='observe_entry')
    namespace={'path':lambda value:value.get_path_name() if value is not None else None}
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
    return namespace['observe_entry'](owner,kind,original)

class NativeEntrySnapshotTests(unittest.TestCase):
    def test_entry_payload_survives_native_end_clearing_current_event_data(self):
        owner=types.SimpleNamespace(activation_events=[]);calls=[]
        payload=types.SimpleNamespace(Instigator=Native('pawn'),Target=Native('placed-rock'))
        def original(actor,data):
            calls.append((actor,data));data.Instigator=None;data.Target=None;return 42
        actor=Native('native-ability');result=observe_entry(owner,'collect',original)(actor,payload)
        self.assertEqual(result,42);self.assertEqual(calls,[(actor,payload)]);self.assertIsNone(payload.Target)
        self.assertEqual(owner.activation_events,[dict(kind='collect',instance='native-ability',instigator='pawn',target='placed-rock')])
    def test_native_exception_is_forwarded_once_without_callback_replay(self):
        owner=types.SimpleNamespace(activation_events=[]);calls=[]
        def original(actor,data):calls.append(actor);raise RuntimeError('native failure')
        with self.assertRaisesRegex(RuntimeError,'native failure'):observe_entry(owner,'sit',original)(Native('ability'),types.SimpleNamespace(Instigator=None,Target=None))
        self.assertEqual(len(calls),1);self.assertEqual(len(owner.activation_events),1)

def report(profile,directory):
    python=profile=='Python';prefix='python' if python else 'fallback';other='fallback' if python else 'python'
    d={prefix+'_activate':1,other+'_activate':0,prefix+'_end':1,other+'_end':0}
    before={'original-rifle':1};after=dict(before,rock=1)
    actions=[]
    for kind in ('collect','sit'):
        row=dict(kind=kind,target_class=contract.TARGETS[kind],actual_event_target_and_instigator=True,native_montage_seen=True,native_tasks_closed=True,
            interactor_press_deltas=[{prefix+'_press':1,other+'_press':0}],action_deltas=[dict(d)],inventory_before=before if kind=='collect' else after,
            inventory_after=after,target_collision_after=kind=='sit',target_lifespan_after=0. if kind=='sit' else 2.,
            pickup_templates=[dict(definition='rock',count=1)],native_target_expired_after_three_seconds=True)
        actions.append(row)
    images=[]
    for kind in ('collect','sit','marker'):
        file=directory/(profile+'-'+kind+'.png');file.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a8ioAAAAASUVORK5CYII='))
        images.append(dict(kind=kind,path=str(file),sha256=contract.hashlib.sha256(file.read_bytes()).hexdigest()))
    value=dict(status='passed',error=None,selected_profile=profile,world=contract.MAP+'.L_InteractionTestMap',experience='/ShooterExplorer/System/Experiences/B_TestInventoryExperience.Default__B_TestInventoryExperience_C',
        pawn_class='/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer_C',native_role=3,native_level_open_requests=2,fixture_position_movement_and_aim=True,
        actual_interactor_count=1,initial_target_counts=dict(collect=2,sit=4),initial_inventory=[dict(definition='original-rifle',count=1)],selected_class_paths=['native-explorer'],
        native_input_asset_injections=['IA_Interact','IA_Interact','IA_ToggleMarkerInWorld'],actions=actions,
        recycled_collect_cues=[dict(alive=True,hidden=True,owner_cleared=True,splines=0,lifespan=0.,counters=dict(python_release=1,fallback_release=0))],
        marker=[dict(has_actor=True,hit_actor_classes=['original-chair'],native_tasks_closed=True,draw_center=[1.,2.,3.],endpoint=[1.,2.,3.],
            deltas={p+'_'+name:int(p==prefix) for p in ('python','fallback') for name in ('activate','data','draw')})],images=images)
    value.update(dict.fromkeys(contract.FALSE_FIELDS,False))
    value.update(dict.fromkeys(('selectors_restored','actual_exit_finalizer','pawn_pose_restored','level_targets_destroyed_after_travel','native_inventory_restored_after_travel','original_target_counts_restored','old_profile_pawns_and_controllers_destroyed','old_ability_instances_destroyed_after_travel','action_observers_restored'),True))
    return value

class ExplorerGameplayContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.reports=[report(p,Path(self.temp.name)) for p in contract.PROFILES]
    def test_bounded_original_python_semantic_pair(self):self.assertIs(contract.validate_pair(self.reports),self.reports)
    def test_original_template_pickup_amount_is_required(self):
        self.reports[1]['actions'][0]['inventory_after']['rock']=2
        with self.assertRaisesRegex(ValueError,'pickup amount'):contract.validate_pair(self.reports)
    def test_sit_cannot_mutate_inventory(self):
        self.reports[1]['actions'][1]['inventory_after']={'original-rifle':1}
        with self.assertRaisesRegex(ValueError,'sit changed'):contract.validate_pair(self.reports)
    def test_native_interactor_press_cannot_fall_through(self):
        self.reports[1]['actions'][0]['interactor_press_deltas'][0]['fallback_press']=1
        with self.assertRaisesRegex(ValueError,'selected Interact'):contract.validate_pair(self.reports)
    def test_marker_requires_real_actor_and_matching_native_endpoint(self):
        for key,value in (('has_actor',False),('draw_center',[0.,0.,0.])):
            data=copy.deepcopy(self.reports);data[1]['marker'][0][key]=value
            with self.assertRaisesRegex(ValueError,'marker actor'):contract.validate_pair(data)
    def test_target_expiry_cue_cleanup_and_native_travel_are_required(self):
        data=copy.deepcopy(self.reports);data[1]['actions'][0]['native_target_expired_after_three_seconds']=False
        with self.assertRaises(ValueError):contract.validate_pair(data)
        data=copy.deepcopy(self.reports);data[1]['recycled_collect_cues'][0]['splines']=1
        with self.assertRaises(ValueError):contract.validate_pair(data)
        data=copy.deepcopy(self.reports);data[1]['old_ability_instances_destroyed_after_travel']=False
        with self.assertRaises(ValueError):contract.validate_pair(data)
    def test_frame_tampering_and_scope_overclaim_rejected(self):
        image=Path(self.reports[1]['images'][0]['path']);image.write_bytes(image.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'PNG'):contract.validate_pair(self.reports)
        for key in contract.FALSE_FIELDS:
            data=copy.deepcopy(self.reports);data[1][key]=True
            with self.assertRaisesRegex(ValueError,'scope overclaim'):contract.validate_pair(data)
    def test_normal_play_and_commandlets_do_not_select_gameplay_probe(self):
        self.assertIsNone(validation_module([]));self.assertIsNone(validation_module(['-run=Py','-UEPExplorerGameplayResult=x']))
        self.assertEqual(validation_module(['-UEPExplorerGameplayResult=x']),'uep_lyra_abilities.explorer_gameplay_validation')

if __name__=='__main__':unittest.main()
