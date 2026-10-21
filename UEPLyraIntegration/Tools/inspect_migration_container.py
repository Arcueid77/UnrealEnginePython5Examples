"""Compare an actual UnrealPak IoStore listing with the frozen package plan.

Presence proves packaged content only, never runtime behavior. Missing original
candidates remain explicit, including any retained source-only definitions.
"""
import argparse
import csv
import json
from pathlib import Path


def content_relative(filename, project_name):
    parts = filename.replace('\\', '/').strip().split('/')
    while parts and parts[0] in ('', '.', '..'):
        parts.pop(0)
    if not parts or parts.pop(0).casefold() != project_name.casefold():
        return None
    if 'Plugins' in parts:
        start = parts.index('Plugins')
        if parts[start:start+2] == ['Plugins', 'GameFeatures'] and len(parts) > start+4 and parts[start+3] == 'Content':
            return '/'.join(parts[start:])
        return None
    if 'Content' in parts:
        return '/'.join(parts[parts.index('Content'):])
    return None


def inspect(plan, listing):
    if plan.get('status') != 'passed' or plan.get('static_scope') != [246, 182, 63, 11]:
        raise ValueError('accepted original-scope package plan required')
    reader = csv.DictReader(listing, skipinitialspace=True)
    if not reader.fieldnames or not {'Filename', 'ChunkType', 'Size'} <= set(reader.fieldnames):
        raise ValueError('UnrealPak IoStore CSV columns missing')
    packages = set()
    rows = 0
    for row in reader:
        rows += 1
        if row['ChunkType'].strip() != 'ExportBundleData' or int(row['Size'].strip()) <= 0:
            continue
        relative = content_relative(row['Filename'], plan['project_name'])
        if relative:
            packages.add(relative.casefold())
    if not rows or not packages:
        raise ValueError('listing contains no cooked content packages')
    def missing(group):
        return [row['relative_path'] for row in group if row['relative_path'].casefold() not in packages]
    groups = {'candidate_assets': plan['candidate_assets'], 'overlay_assets': plan['accepted_overlay_assets'],
              'runtime_maps': plan['runtime_maps']}
    coverage = {name: dict(expected=len(group), present=len(group)-len(missing(group)), missing=missing(group))
                for name, group in groups.items()}
    return dict(schema_version=1, status='passed' if not any(row['missing'] for row in coverage.values()) else 'review_required',
                scope='actual-cooked-package-presence-only', runtime_acceptance=False, full_acceptance=False,
                csv_rows=rows, unique_content_packages=len(packages), coverage=coverage)


def main():
    parser = argparse.ArgumentParser()
    for name in ('plan', 'csv', 'result'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding='utf-8-sig'))
    with Path(args.csv).open(encoding='utf-8-sig', newline='') as listing:
        report = inspect(plan, listing)
    Path(args.result).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
