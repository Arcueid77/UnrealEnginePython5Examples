import ast
import copy
import importlib.util
from pathlib import Path
import unittest

scripts=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud'
spec=importlib.util.spec_from_file_location('quickbar_initialization_contract',scripts/'quickbar_initialization_contract.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)


def valid_report():
    report=dict(status='passed',error=None,profile_selected_before_native_create=True,
        native_create_api='WidgetBlueprintLibrary.Create',native_initialization_parity_tested=True,
        lifecycle_event_replayed=False,profile_changed_after_create=False,resume_entry_called=False,
        native_player_state_written=False,full_acceptance=False,network_acceptance=False,packaged_runtime=False,
        original_defaults_restored=True,test_roots_released=True,owned_widgets_removed=True,native_player_state_unchanged=True,
        pairs=[],owned_cleanup=dict(python_active_before=3,python_active_after=3,original_proxies_inactive=6,released_roots=6),
        shutdown=dict(active_count=0,scopes_created=9,scopes_closed=9,errors=[],pool_lifetime=dict(active_count=0,ticker_active=False)))
    for index in range(3):
        initial=dict(index=index,empty=True,selected=False,numeric=0.,text='0',icon=None,ammo_icon=None,animations=[False]*3)
        mounted=dict(initial,empty=index!=0,selected=index==0)
        rows=[]
        for profile in contract.PROFILES:
            python=profile=='Python'
            rows.append(dict(profile=profile,effective_profile=profile,selected_before_create=True,
                widget=f'widget{index}-{profile}',**{'class':'/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot_C'},
                initial=copy.deepcopy(initial),python_scope_open=python,original_proxy_active=[not python]*2,
                python_counter_delta=dict(slot_updates=int(python),scopes_created=int(python))))
        report['pairs'].append(dict(slot_index=index,creations=rows,initial_states_equal=True,
            mounted_states_equal=True,mounted=[copy.deepcopy(mounted),copy.deepcopy(mounted)]))
    return report


class QuickBarInitializationContractTests(unittest.TestCase):
    def test_all_three_native_slot_profile_pairs(self):
        self.assertEqual(contract.validate(valid_report())['native_widget_creations'],6)
        value=valid_report();value['pairs'].pop()
        with self.assertRaises(ValueError):contract.validate(value)

    def test_post_create_profile_or_replayed_initialization_is_not_evidence(self):
        for field in ('profile_changed_after_create','lifecycle_event_replayed','resume_entry_called'):
            value=valid_report();value[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):contract.validate(value)

    def test_original_initialization_cannot_have_entered_python(self):
        value=valid_report();value['pairs'][0]['creations'][0]['python_counter_delta']['slot_updates']=1
        with self.assertRaises(ValueError):contract.validate(value)

    def test_python_initialization_cannot_retain_original_listeners(self):
        value=valid_report();value['pairs'][0]['creations'][1]['original_proxy_active']=[True,True]
        with self.assertRaises(ValueError):contract.validate(value)

    def test_class_identity_profile_order_and_distinct_native_creations(self):
        for field in ('class','effective_profile','widget'):
            value=valid_report();row=value['pairs'][1]['creations'][0]
            row[field]=value['pairs'][0]['creations'][0]['widget'] if field=='widget' else 'wrong'
            with self.subTest(field=field),self.assertRaises(ValueError):contract.validate(value)

    def test_equal_flags_cannot_hide_different_original_state(self):
        for phase in ('initial','mounted'):
            value=valid_report()
            target=value['pairs'][0]['creations'][0]['initial'] if phase=='initial' else value['pairs'][0]['mounted'][0]
            target['numeric']=42.
            with self.subTest(phase=phase),self.assertRaises(ValueError):contract.validate(value)

    def test_subscription_root_player_state_and_cdo_cleanup_are_required(self):
        for field in ('original_defaults_restored','test_roots_released','owned_widgets_removed','native_player_state_unchanged'):
            value=valid_report();value[field]=False
            with self.subTest(field=field),self.assertRaises(ValueError):contract.validate(value)
        for delta in (dict(active_count=1),dict(scopes_closed=8),dict(errors=['late callback'])):
            value=valid_report();value['shutdown'].update(delta)
            with self.subTest(delta=delta),self.assertRaises(ValueError):contract.validate(value)

    def test_fixture_uses_native_creation_without_lifecycle_or_resume_calls(self):
        tree=ast.parse((scripts/'quickbar_initialization_validation.py').read_text(encoding='utf-8-sig'))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(n.func,ast.Attribute) and n.func.attr=='set_mixin_profile' for n in calls))
        names=[n.args[0].value for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='call_function'
               and n.args and isinstance(n.args[0],ast.Constant)]
        self.assertIn('Create',names)
        self.assertFalse(set(names)&{'OnInitialized','Construct','Destruct','UEPResumeQuickBarSlotObservation'})
