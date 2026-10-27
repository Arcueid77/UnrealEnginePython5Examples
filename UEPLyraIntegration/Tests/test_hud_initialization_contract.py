import ast
import copy
import importlib.util
from pathlib import Path
import unittest

scripts=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud'
spec=importlib.util.spec_from_file_location('hud_initialization_contract',scripts/'hud_initialization_contract.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)


def report():
    value=dict(status='passed',error=None,selection_before_native_create=True,profile_changed_after_create=False,
        lifecycle_or_resume_replayed=False,pairs=[],defaults_restored=True,released_roots=10,inactive_original_proxies=5,
        native_player_state_unchanged=True,owned_cleanup=[dict(active_before=3,active_after=3)],
        shutdown=dict(action=dict(active_count=0,scopes_created=4,scopes_closed=4,errors=[])),
        full_acceptance=False,network_acceptance=False,packaged_runtime=False)
    for kind in contract.KINDS:
        rows=[]
        for profile in ('BlueprintFallback','Python'):
            python=profile=='Python'
            rows.append(dict(profile=profile,effective_profile=profile,**{'class':kind},widget=kind+profile,
                initial=dict(visible=False),python_scope_open=python,original_proxy_active=not python,python_scopes_created=int(python)))
        value['pairs'].append(dict(kind=kind,**{'class':kind},creations=rows,mounted=[dict(visible=False),dict(visible=False)]))
    return value


class HUDInitializationContractTests(unittest.TestCase):
    def test_all_five_original_candidate_pairs_required(self):
        self.assertEqual(contract.validate(report())['native_creations'],10)
        value=report();value['pairs'].pop()
        with self.assertRaises(ValueError):contract.validate(value)

    def test_shared_python_initialization_cannot_substitute_for_original(self):
        value=report();value['pairs'][0]['creations'][0]['python_scopes_created']=1
        with self.assertRaises(ValueError):contract.validate(value)

    def test_python_cannot_keep_blueprint_listener(self):
        value=report();value['pairs'][0]['creations'][1]['original_proxy_active']=True
        with self.assertRaises(ValueError):contract.validate(value)

    def test_after_creation_profile_switch_or_lifecycle_replay_fails(self):
        for field in ('profile_changed_after_create','lifecycle_or_resume_replayed'):
            value=report();value[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):contract.validate(value)

    def test_initial_and_mounted_comparisons_both_required(self):
        for phase in ('initial','mounted'):
            value=report()
            target=value['pairs'][0]['creations'][0]['initial'] if phase=='initial' else value['pairs'][0]['mounted'][0]
            target['visible']=True
            with self.subTest(phase=phase),self.assertRaises(ValueError):contract.validate(value)

    def test_wrong_profile_or_reused_native_widget_fails(self):
        for field in ('effective_profile','widget'):
            value=report();value['pairs'][1]['creations'][0][field]=value['pairs'][0]['creations'][0]['widget'] if field=='widget' else 'wrong'
            with self.subTest(field=field),self.assertRaises(ValueError):contract.validate(value)

    def test_default_root_proxy_and_subscription_cleanup_required(self):
        for delta in (dict(defaults_restored=False),dict(released_roots=9),dict(inactive_original_proxies=4),dict(native_player_state_unchanged=False)):
            value=report();value.update(delta)
            with self.subTest(delta=delta),self.assertRaises(ValueError):contract.validate(value)
        value=report();value['shutdown']['action']['active_count']=1
        with self.assertRaises(ValueError):contract.validate(value)

    def test_runtime_fixture_does_not_import_another_auto_starting_validation(self):
        tree=ast.parse((scripts/'hud_initialization_validation.py').read_text(encoding='utf-8-sig'))
        modules=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module]
        self.assertFalse(any(m.endswith('_validation') for m in modules))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertFalse(any(n.func.attr=='set_mixin_profile' for n in calls))
