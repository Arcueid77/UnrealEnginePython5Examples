"""Additional native Standalone equipment ownership/rollback checks."""
import argparse
import json
from pathlib import Path
from .autoreload_contract import validate as validate_ammo, require


def validate(report):
    result = validate_ammo(report)
    require(report['weapon'] in ('rifle','shotgun') and report['native_mode'] == 'Standalone',
            'A supported non-pistol Standalone family is required')
    for field in ('standalone_native_equipment_fixture','temporary_weapon_removed','original_inventory_restored'):
        require(report[field] is True, 'Native Standalone equipment restore missing: '+field)
    fixture = report['native_weapon_fixture']
    original = fixture['original_inventory']
    require(fixture['weapon'] == report['weapon'] and fixture['slot'] > 0 and
            isinstance(fixture['owned_item'],str) and fixture['owned_item'] and
            len(original['items']) == 1 and original['slots'][0] == original['items'][0] and
            all(value is None for value in original['slots'][1:]) and
            fixture['owned_item'] not in original['items'] and fixture['owned_item'] not in original['slots'] and
            original['active'] == 0 and fixture['original_auto_active'] is True,
            'Only one test-owned equipment item may be removed; original loadout must be preserved')
    return dict(**result, weapon=report['weapon'], native_mode='Standalone',
                native_temporary_equipment_restored=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
