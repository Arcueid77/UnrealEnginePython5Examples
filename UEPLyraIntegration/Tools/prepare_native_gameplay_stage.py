"""Copy the accepted baseline into a fresh, independent native-gameplay stage."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil

REPO = Path(__file__).resolve().parents[3]
SKIP_DIRS = {'Intermediate', 'Saved', 'DerivedDataCache', '.git', '__pycache__'}
SKIP_SUFFIXES = {'.pdb', '.ilk', '.exp', '.obj'}


def prepare(source, stage, result):
    source, stage, result = (Path(p).resolve() for p in (source, stage, result))
    owned = (REPO / '.build').resolve()
    if not source.is_relative_to(owned) or not stage.is_relative_to(owned) or not result.is_relative_to(owned):
        raise ValueError('Source, fresh stage and report must be workspace-owned')
    marker = source / '.uep-lyra-full-stage.json'
    if not marker.is_file() or stage.exists() or result.exists() or stage.is_relative_to(source):
        raise ValueError('A marked source and a fresh independent stage/report are required')
    original = json.loads(marker.read_text(encoding='utf-8-sig'))
    stage.mkdir(parents=True)
    report = dict(status='copying', parent_stage=str(source), stage=str(stage), copied_files=0,
                  copied_bytes=0, skipped_files=0, hardlinks_used=False, junctions_used=False,
                  runtime_acceptance=False, excluded_directories=sorted(SKIP_DIRS), files=[])
    result.parent.mkdir(parents=True, exist_ok=True)
    try:
        for directory, dirs, names in os.walk(source, followlinks=False):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            parent = Path(directory)
            for d in dirs:
                if (parent / d).lstat().st_file_attributes & 0x400:
                    raise ValueError('Reparse-point source directory requires explicit handling: '+str(parent/d))
            for name in names:
                file = parent / name
                rel = file.relative_to(source)
                if file.suffix.lower() in SKIP_SUFFIXES or rel.as_posix() == '.uep-lyra-full-stage.json':
                    report['skipped_files'] += 1
                    continue
                if len(rel.parts) == 1 and name not in ('LyraStarterGame.uproject', 'README.md'):
                    continue
                if len(rel.parts) > 1 and rel.parts[0] not in ('Binaries','Build','Config','Content','Platforms','Plugins','Source'):
                    continue
                target = stage / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                before = file.stat()
                shutil.copy2(file, target)
                if file.stat().st_size != before.st_size or target.stat().st_size != before.st_size:
                    raise RuntimeError('Copy input changed: '+str(file))
                report['copied_files'] += 1
                report['copied_bytes'] += before.st_size
                report['files'].append(dict(path=rel.as_posix(), bytes=before.st_size))
                if report['copied_files'] % 1000 == 0:
                    print(f"Copied {report['copied_files']} files", flush=True)
        marker_data = dict(original, parent_stage=str(source), purpose='approved-native-gameplay-migration',
                           independent_file_copies=True)
        (stage/'.uep-lyra-full-stage.json').write_text(json.dumps(marker_data,indent=2)+'\n',encoding='utf-8')
        report['marker_sha256'] = hashlib.sha256((stage/'.uep-lyra-full-stage.json').read_bytes()).hexdigest().upper()
        report['status'] = 'passed'
    except Exception as error:
        report['status'], report['error'] = 'failed', repr(error)
        raise
    finally:
        result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return {k:v for k,v in report.items() if k != 'files'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True);parser.add_argument('--stage',required=True);parser.add_argument('--result',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.source,args.stage,args.result)))
