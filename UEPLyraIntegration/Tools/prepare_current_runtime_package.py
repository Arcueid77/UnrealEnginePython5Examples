"""Derive an isolated current-native/Python package from unchanged cooked assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def inside(path, root):
    path=Path(path).resolve();root=Path(root).resolve()
    require(path != root and path.is_relative_to(root), 'Path must stay inside its owned directory')
    return path


def verify_rows(rows):
    require(rows, 'Frozen inputs/products absent')
    for row in rows:
        require(sha(row['path']) == row['sha256'].upper(), 'Frozen input/product changed: '+row['path'])


def asset_rows(plan, stage):
    require(len(plan['candidate_assets']) == 246 and len(plan['accepted_overlay_assets']) >= 460 and
            len(plan['runtime_maps']) >= 12, 'Original full cooked asset/map inventory required')
    result=[]
    for family in ('candidate_assets', 'accepted_overlay_assets', 'runtime_maps'):
        for row in plan[family]:
            path=inside(stage/row['relative_path'], stage)
            if 'stage' in row:
                require(Path(row['stage']).resolve() == path, 'Cooked candidate path differs')
            require(sha(path) == row['sha256'].upper(), 'Cooked asset differs; recook affected content first')
            result.append(dict(path=str(path),sha256=row['sha256'].upper()))
    return result


def prepare(repo, stage, cook_root, game_root, output):
    repo=Path(repo).resolve();owned=repo/'.build'
    stage=inside(stage,owned);cook_root=inside(cook_root,owned)
    game_root=inside(game_root,owned);output=inside(output,owned)
    require(not output.exists() and (stage/'.uep-lyra-full-stage.json').is_file(),
            'Marked stage and fresh package snapshot required')
    cook=read(cook_root/'summary.json');game=read(game_root/'summary.json')
    require(cook['status'] == 'passed' and cook['scope'] == 'current-original-migration-content-cook-package' and
            cook['process']['exit_code'] == 0, 'Successful original content cook required')
    require(game['status'] == 'passed' and game['scope'] == 'current-Development-LyraGame-build-only' and
            game['no_engine_changes_requested'] is True and game['process']['exit_code'] == 0 and
            len(game['products']) == 2, 'Verified current protected Game build required')
    require(any('-Project='+str(stage/'LyraStarterGame.uproject') == arg for arg in game['process']['arguments']),
            'Current native build belongs to another stage')
    verify_rows(game['hashes']+game['engine_inputs']+game['products'])
    # The old native/Python inputs may differ. Reuse only its unchanged cooked
    # products, current asset source bytes and identical protected Engine inputs.
    verify_rows(cook['products'])
    plan_row,=[r for r in cook['hashes'] if 'package-plan' in Path(r['path']).name]
    verify_rows([plan_row]);plan=read(plan_row['path'])
    require(plan['status'] == 'passed' and plan['inspection_only'] is True and
            plan['static_scope'] == [246,182,63,11], 'Original complete package plan required')
    assets=asset_rows(plan,stage)
    old_build_row,=[r for r in cook['hashes'] if Path(r['path']).name == 'summary.json']
    verify_rows([old_build_row]);verify_rows(read(old_build_row['path'])['engine_inputs'])
    for row in cook['hashes']:
        if Path(row['path']).name in ('DefaultGame.ini', 'LyraStarterGame.uproject'):
            verify_rows([row])
    descriptor=plan['staged_plugin_descriptor'];verify_rows([descriptor])
    base=inside(cook['archive'],owned)
    old_exe=inside(cook['packaged_executable'],base)
    require(old_exe.name == 'LyraGame.exe' and old_exe.stat().st_size > 100_000_000,
            'Actual inner Game executable required')
    native=next(r for r in game['products'] if Path(r['path']).name == 'LyraGame.exe')
    require(Path(native['path']).stat().st_size > 100_000_000, 'Bootstrap cannot replace Game executable')
    output.mkdir();archive=output/'Archive'
    summary=dict(schema_version=1,status='failed',scope='current native and Python snapshot with unchanged cooked migration assets',
        cpp_compile_executed=False,cook_package_executed=False,base_archive_unchanged=True,
        full_acceptance=False,packaged_runtime=False,archive=str(archive),packaged_executable=None,
        reused_cooked_candidates=246,reused_overlay_assets=len(plan['accepted_overlay_assets']),
        reused_runtime_maps=len(plan['runtime_maps']),hashes=[],products=[],script_payloads=[],error=None)
    def pin(path):
        summary['hashes'].append(dict(path=str(path),sha256=sha(path)))
    try:
        for p in (Path(__file__),cook_root/'summary.json',game_root/'summary.json',Path(plan_row['path'])):
            pin(p)
        summary['hashes']+=game['hashes']+game['engine_inputs']+game['products']+assets
        shutil.copytree(base,archive,copy_function=shutil.copy2)
        executable=inside(archive/old_exe.relative_to(base),archive)
        project=executable.parents[2]
        # Move only newly copied payloads, preserving their bytes in this new
        # evidence directory. The original archive is never moved or edited.
        for label,source,target in (
            ('project',repo/'Demos/UEPLyraIntegration/Overlay/Content/Scripts',project/'Content/Scripts'),
            ('core',repo/'Content/Scripts',project/'Plugins/UnrealEnginePython/Content/Scripts')):
            target=inside(target,archive);previous=inside(output/('PreviousScripts-'+label),output)
            require(target.is_dir() and not previous.exists(), 'Unexpected package Python directory')
            shutil.move(str(target),str(previous))
            shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))
            files=sorted(source.rglob('*.py'))
            for file in files:
                copy=target/file.relative_to(source)
                require(sha(file) == sha(copy), 'Copied current Python payload differs')
                pin(file);pin(copy)
            summary['script_payloads'].append(dict(label=label,current_python_files=len(files),previous_payload=str(previous)))
        previous_exe=inside(output/'PreviousGame.exe',output)
        shutil.move(str(inside(executable,archive)),str(previous_exe))
        shutil.copy2(native['path'],executable)
        require(sha(executable) == native['sha256'].upper(), 'Current executable copy differs')
        for row in cook['products']:
            copy=archive/Path(row['path']).resolve().relative_to(base)
            expected=native['sha256'] if copy == executable else row['sha256']
            require(sha(copy) == expected.upper(), 'Derived package product changed unexpectedly')
            summary['products'].append(dict(path=str(copy),sha256=expected.upper()))
        verify_rows(cook['products']);verify_rows(summary['hashes'])
        summary.update(status='passed',packaged_executable=str(executable),
            current_executable_sha256=native['sha256'].upper(),old_executable_sha256=sha(previous_exe))
    except Exception as error:
        summary['error']=str(error)
        raise
    finally:
        (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('stage','cook-directory','game-build','output'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    report=prepare(Path(__file__).resolve().parents[3],args.stage,args.cook_directory,args.game_build,args.output)
    print(json.dumps(dict(status=report['status'],reused_candidates=246,cook_executed=False,
        scripts=sum(r['current_python_files'] for r in report['script_payloads']))))


if __name__ == '__main__':main()
