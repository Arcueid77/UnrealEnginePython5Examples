import copy
import unittest
from uep_packaged_discovery_contract import validate


def report():
    rows={}
    for name in ('Main','Companion','Widget'):
        rows[name]=dict(same_unreal_class=True,native_original_restored=True,
            metaclass='WidgetBlueprintGeneratedClass' if name=='Widget' else 'BlueprintGeneratedClass',
            python=dict(BlueprintCalls=1,PythonCalls=2 if name=='Main' else 1),
            fallback=dict(BlueprintCalls=3 if name=='Main' else 2,PythonCalls=0))
    return dict(status='passed',explicit_registration_called=False,fresh_classes_initially_absent=True,
        automatic_imported_classes_discovered=True,cleanup_complete=True,full_acceptance=False,
        precompiled_blueprint_caller_routed=True,classes=rows)


class PackagedDiscoveryContractTests(unittest.TestCase):
    def test_complete_scoped_report_is_accepted(self):
        validate(report())

    def test_manual_registration_cannot_prove_discovery(self):
        value=report();value['explicit_registration_called']=True
        with self.assertRaises(AssertionError):validate(value)

    def test_missing_imported_widget_cannot_be_ignored(self):
        value=report();del value['classes']['Widget']
        with self.assertRaises(AssertionError):validate(value)

    def test_python_fallthrough_is_rejected(self):
        value=report();value['classes']['Main']['python']['BlueprintCalls']=2
        with self.assertRaises(AssertionError):validate(value)

    def test_wrong_widget_metaclass_is_rejected(self):
        value=report();value['classes']['Widget']['metaclass']='BlueprintGeneratedClass'
        with self.assertRaises(AssertionError):validate(value)

    def test_failed_cleanup_or_unrestored_original_is_rejected(self):
        for key in ('cleanup_complete','native_original_restored'):
            value=report()
            if key=='cleanup_complete':value[key]=False
            else:value['classes']['Companion'][key]=False
            with self.subTest(key=key),self.assertRaises(AssertionError):validate(value)
