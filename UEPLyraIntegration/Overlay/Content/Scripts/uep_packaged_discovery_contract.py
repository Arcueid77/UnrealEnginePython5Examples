"""Independent requirements for a real fresh-process cooked discovery run."""
import argparse
import json
from pathlib import Path


def validate(report):
    assert report['status'] == 'passed'
    assert report['explicit_registration_called'] is False
    assert report['fresh_classes_initially_absent'] is True
    assert report['automatic_imported_classes_discovered'] is True
    assert report['cleanup_complete'] is True
    assert report['full_acceptance'] is False
    assert set(report['classes']) == {'Main', 'Companion', 'Widget'}
    for name, row in report['classes'].items():
        assert row['same_unreal_class'] and row['native_original_restored']
        assert row['python'] == {'BlueprintCalls': 1, 'PythonCalls': 2 if name == 'Main' else 1}
        assert row['fallback'] == {'BlueprintCalls': 3 if name == 'Main' else 2, 'PythonCalls': 0}
        assert row['metaclass'] == ('WidgetBlueprintGeneratedClass' if name == 'Widget' else 'BlueprintGeneratedClass')
    assert report['precompiled_blueprint_caller_routed'] is True


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);args=parser.parse_args()
    validate(json.loads(Path(args.report).read_text(encoding='utf-8-sig')))
    print('Packaged automatic discovery contract passed')
