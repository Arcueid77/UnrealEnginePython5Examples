import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_small_batch_comparison_acceptance as audit
from audit_migration_acceptance import attach_small_batch_comparison_review


def policy_sources():
    classes={(m,'ExamplePythonProfile') for m in audit.PARENT_CALLS}
    sources={m:'class ExamplePythonProfile:\n def OnAnimationFinished(self, Animation):\n  self.call_mixin_original("OnAnimationFinished", Animation)\nclass ExampleBlueprintFallbackProfile:\n def Init(self):\n  self.call_mixin_original("OnInitialized")\n' for m in audit.PARENT_CALLS}
    coverage=dict(assets=[dict(profiles={'Python':dict(python_class=m+'.ExamplePythonProfile')},
        ancestry=['/Game/Widget','/Script/UMG.UserWidget'],staged_wired_entries=[]) for m in audit.PARENT_CALLS])
    return sources,classes,coverage


def route_fixture():
    kinds=['python-routed']*93+['staged-script-dispatch-forwarder-review']*28+['direct-parent-forwarder-review']*10+['no-connected-execution-business']*7+['unrouted-business-review']*2
    scope=[dict(path=str(i)) for i in range(32)];entries=[];reviews=[]
    coverage=dict(assets=[dict(asset=str(i),all_ancestor_bindings=[dict(target_class='cls'+str(i),default_profile='Python',profiles=dict(Python=['Business','Dispatch']))]) for i in range(32)])
    for i,kind in enumerate(kinds):
        row=dict(asset=str(i%32),version='0.10.0',graph='Graph',entry='Entry'+str(i),disposition=kind,
            native_router='cls'+str(i%32),staged_entry=dict(entry='Business',calls_python_dispatch=['Dispatch']),
            node_classes=['K2Node_CallParentFunction'],reachable_execution_nodes=0)
        entries.append(row)
        if kind=='unrouted-business-review':reviews.append(dict(asset=row['asset'],graph=row['graph'],entry=row['entry'],kind='native-gas-teardown'))
    return dict(entrypoints=entries),coverage,scope,dict(entries=reviews)


class SmallBatchComparisonAcceptanceTests(unittest.TestCase):
    def test_only_two_exact_native_animation_parent_calls_are_allowed(self):
        sources,classes,coverage=policy_sources();self.assertEqual(len(audit.no_original_business(sources,classes,coverage)),2)
        module=next(iter(sources));sources[module]=sources[module].replace('"OnAnimationFinished", Animation','"OnInitialized"')
        with self.assertRaises(ValueError):audit.no_original_business(sources,classes,coverage)

    def test_authored_bp_or_bp_ancestor_cannot_be_called_as_native_parent(self):
        for field in ('ancestor','event'):
            sources,classes,coverage=policy_sources();row=coverage['assets'][0]
            if field=='ancestor':row['ancestry'].append('/Game/BPParent')
            else:row['staged_wired_entries'].append(dict(entry='OnAnimationFinished'))
            with self.subTest(field=field),self.assertRaises(ValueError):audit.no_original_business(sources,classes,coverage)

    def test_module_helper_cannot_hide_original_bp_business_call(self):
        sources,classes,coverage=policy_sources();module=next(iter(sources));sources[module]+='\ndef helper(self):\n self.call_mixin_original("Business")\n'
        with self.assertRaises(ValueError):audit.no_original_business(sources,classes,coverage)

    def test_all140_original_entries_and32_paths_are_required(self):
        entries,coverage,scope,reviews=route_fixture();self.assertEqual(audit.entry_routes(entries,coverage,scope,reviews)['original_entries'],140)
        entries['entrypoints'].pop()
        with self.assertRaises(ValueError):audit.entry_routes(entries,coverage,scope,reviews)

    def test_default_routing_dispatch_parent_and_empty_entry_gaps_fail(self):
        for kind in ('default','dispatch','parent','empty','retained'):
            entries,coverage,scope,reviews=route_fixture()
            if kind=='default':coverage['assets'][0]['all_ancestor_bindings'][0]['default_profile']='BlueprintFallback'
            elif kind=='dispatch':entries['entrypoints'][93]['staged_entry']['calls_python_dispatch']=[]
            elif kind=='parent':entries['entrypoints'][121]['node_classes']=['K2Node_VariableSet']
            elif kind=='empty':entries['entrypoints'][131]['reachable_execution_nodes']=1
            else:reviews['entries'][0]['kind']='unreviewed-business'
            with self.subTest(kind=kind),self.assertRaises(ValueError):audit.entry_routes(entries,coverage,scope,reviews)

    def test_one_missing_native_comparison_family_rejects_candidate_matrix(self):
        scope=[dict(path=str(i)) for i in range(32)]
        dispositions={str(i):dict(effective_python_class=('module.PythonProfile' if i<30 else None),disposition='retained-native-cpp-touch-parent-forwarder') for i in range(32)}
        self.assertEqual(len(audit.candidate_matrix(scope,dispositions,[dict(directory='run',policy_modules=['module'])])),32)
        with self.assertRaises(ValueError):audit.candidate_matrix(scope,dispositions,[])

    def test_lazy_menu_round_trip_must_have_original_native_push_and_pop(self):
        value=dict(status='passed',error=None,menu_class_loaded_before=False,class_preloaded_by_probe=False,python_clicks=1,
            full_acceptance=False,physical_touch_tested=False,cases=[dict(profile=p,menu_class='W_LyraGameMenu_C',same_button_class='W_OpenMenuTouchButton_C',active=True,native_async_layer_push=True,native_deactivated=True,visible_after_transition=True) for p in ('Python','BlueprintFallback','Python')])
        self.assertEqual(audit.menu_gate(value)['profile_round_trip'],3)
        value['cases'][1]['native_deactivated']=False
        with self.assertRaises(ValueError):audit.menu_gate(value)

    def test_reticle_family_and_finite_native_values_cannot_be_skipped(self):
        value=dict(status='passed',error=None,cases=[],message_cases=[],real_ads_input_tested=True,
            real_equipped_shotgun_tested=True,native_shotgun_ammo_before=8,native_shotgun_ammo_after=5,
            repeated_elimination_and_suicide_filter=True,full_acceptance=False,network_acceptance=False,
            real_elimination_gameplay_tested=False,inventory_or_weapon_spread_written=False,
            reticle_shutdown=dict(active_count=0,scopes_created=6,scopes_closed=6,errors=[]))
        for kind in ('Pistol','Rifle','Shotgun'):
            for _ in range(2):value['cases'].append(dict(kind=kind,bp=dict(radius=1.,width=2.,height=2.),
                python=dict(radius=1.,width=2.,height=2.),native=dict(radius=1.,width=2.,height=2.),same_class=True,automatic_python_ticks=1))
            value['message_cases'].append(dict(local_ads_received=True,foreign_ads_ignored=True,
                ads_animation_noop_preserved=True,elimination_triggered=True))
        self.assertEqual(audit.reticle_gate(value)['layout_context_pairs'],6)
        invalid=copy.deepcopy(value);bad=dict(radius=float('nan'),width=2.,height=2.)
        invalid['cases'][0].update(bp=bad,python=bad,native=bad)
        with self.assertRaises(ValueError):audit.reticle_gate(invalid)
        value['cases'][-1]['kind']='Pistol'
        with self.assertRaises(ValueError):audit.reticle_gate(value)

    def test_only_original010_small_batch_requirement_is_promoted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'review.json';path.write_text('{}',encoding='utf-8')
            rows=[dict(version='0.10.0',text=audit.REQUIREMENT,completion_proven=False),dict(version='0.14.0',text='Whole Experiences',completion_proven=False)]
            report=dict(requirements=rows,inputs=[])
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')):attach_small_batch_comparison_review(report,{}, {},temporary,path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven'])
            rows[0]['version']='0.9.0'
            with patch.object(audit,'verify_documentation',return_value=dict(status='passed')),self.assertRaises(ValueError):attach_small_batch_comparison_review(report,{}, {},temporary,path)

    def test_metadata_cannot_substitute_for_reproduced_native_comparisons(self):
        for doc in (dict(criterion='partial',completion_proven=True),dict(criterion=audit.REQUIREMENT,completion_proven=False)):
            with self.assertRaises(ValueError):audit.verify_documentation(doc,{}, {},'.')
        doc=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=dict(original_candidates=1))
        with patch.object(audit,'inspect',return_value=dict(original_candidates=32)),self.assertRaises(ValueError):audit.verify_documentation(doc,{}, {},'.')
