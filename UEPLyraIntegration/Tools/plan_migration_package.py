"""Read-only current migration/package inventory; never builds or cooks."""
import argparse, hashlib, json
from pathlib import Path

COUNTS = (246, 182, 63, 11)
FEATURES = ('ShooterCore', 'ShooterMaps', 'ShooterExplorer', 'TopDownArena')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_file(stage, package):
    if not package.startswith('/') or '\\' in package:
        raise ValueError('invalid long package path')
    name, separator, object_name = package.partition('.')
    if separator and (not object_name or '/' in object_name or '.' in object_name or object_name != name.rsplit('/', 1)[-1]):
        raise ValueError('invalid package/object name')
    parts = name.strip('/').split('/')
    if len(parts) < 2 or any(part in ('.', '..') for part in parts):
        raise ValueError('invalid package name')
    if parts[0] == 'Game':
        base = stage/'Content'
    elif parts[0] in FEATURES:
        base = stage/'Plugins/GameFeatures'/parts[0]/'Content'
    else:
        raise ValueError('unsupported migration mount: '+parts[0])
    return base.joinpath(*parts[1:]).with_suffix('.uasset')


def virtual_file(relative):
    parts = Path(relative).parts
    if parts[0] == 'Content':
        return '/Game/'+Path(*parts[1:]).with_suffix('').as_posix()
    if len(parts) > 4 and parts[:2] == ('Plugins', 'GameFeatures') and parts[3] == 'Content':
        return '/'+parts[2]+'/'+Path(*parts[4:]).with_suffix('').as_posix()
    raise ValueError('unsupported overlay asset layout')


def inspect(stage, overlay, manifest):
    if not (stage/'.uep-lyra-full-stage.json').is_file():
        raise ValueError('marked Lyra stage required')
    projects = list(stage.glob('*.uproject'))
    if len(projects) != 1:
        raise ValueError('one staged project required')
    data = json.loads(manifest.read_text(encoding='utf-8-sig'))
    if tuple(data[k] for k in ('runtime_candidates', 'configuration_only', 'retained', 'scope_review_candidates')) != COUNTS or len(data['assets']) != 246:
        raise ValueError('original migration inventory differs')
    candidates = []
    cook_directories = {'/Game/UEPMixins', '/Game/UEPInterop'}
    for row in data['assets']:
        file = package_file(stage, row['path'])
        if not file.is_file():
            raise ValueError('candidate asset missing: '+str(file))
        package = row['path'].split('.', 1)[0]
        cook_directories.add(package.rsplit('/', 1)[0])
        candidates.append(dict(path=row['path'], version=row['version'], status=row['status'], relative_path=file.relative_to(stage).as_posix(),
            stage=str(file.resolve()), sha256=sha(file), packaging_semantics_reviewed=False))
    assets = []
    for source in sorted(overlay.rglob('*.uasset')):
        relative = source.relative_to(overlay);copy = stage/relative
        if not copy.is_file() or sha(copy) != sha(source):
            raise ValueError('accepted overlay/stage asset differs: '+str(relative))
        package = virtual_file(relative)
        cook_directories.add(package.rsplit('/', 1)[0])
        assets.append(dict(package=package, relative_path=relative.as_posix(), sha256=sha(source)))
    maps = []
    roots = [(stage/'Plugins/GameFeatures'/feature/'Content/Maps', '/'+feature+'/Maps') for feature in ('ShooterMaps', 'ShooterExplorer', 'TopDownArena')]
    roots += [(stage/'Content/System/FrontEnd/Maps', '/Game/System/FrontEnd/Maps')]
    for directory, mount in roots:
        for file in sorted(directory.glob('*.umap')):
            maps.append(dict(package=mount+'/'+file.stem, relative_path=file.relative_to(stage).as_posix(), sha256=sha(file)))
    transition = stage/'Content/System/TransitionMap.umap'
    if not transition.is_file():
        raise ValueError('native transition map missing')
    maps.append(dict(package='/Game/System/TransitionMap', relative_path=transition.relative_to(stage).as_posix(), sha256=sha(transition)))
    descriptor = stage/'Plugins/UnrealEnginePython/UnrealEnginePython.uplugin'
    version = json.loads(descriptor.read_text(encoding='utf-8-sig'))
    scripts = sorted((overlay/'Content/Scripts').rglob('*.py'))
    return dict(schema_version=1, status='passed', inspection_only=True, build_executed=False,
        cook_package_executed=False, runtime_acceptance=False, full_acceptance=False,
        static_scope=list(COUNTS), project_name=projects[0].stem, candidate_paths_in_original_order=[r['path'] for r in candidates],
        candidate_assets=candidates, accepted_overlay_assets=assets, runtime_maps=maps,
        engine_entry_map_required='/Engine/Maps/Entry',
        proposed_always_cook_directories=sorted(cook_directories),
        proposed_cook_directory_paths=[dict(virtual_directory=directory,
            physical_directory=str(package_file(stage, directory+'/Placeholder.Placeholder').parent.resolve())) for directory in sorted(cook_directories)],
        project_editor_overview_map_excluded_from_runtime_map_list=True,
        scripts_nonufs_directory='Content/Scripts', script_files=len(scripts),
        script_hashes=[dict(relative_path=p.relative_to(overlay).as_posix(), sha256=sha(p)) for p in scripts],
        staged_plugin_descriptor=dict(path=str(descriptor.resolve()), sha256=sha(descriptor), version_name=version.get('VersionName')),
        previous_game_receipt=json.loads((stage/'Binaries/Win64/LyraGame.target').read_text(encoding='utf-8-sig'))['Version'],
        notes=['This inventory does not assert that current Game binaries match current source.',
               'The old Expanse-only cook is insufficient for the original Explorer/Arena/frontend scope.',
               'Always-cook directory semantics and editor-only dependencies still need an actual protected cook gate.',
               'No stage configuration,reference project,assets or native binaries are modified by this tool.',
               'Descriptor version labels are recorded as observed,not silently promoted to a release.'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True);parser.add_argument('--overlay',required=True);parser.add_argument('--manifest',required=True);parser.add_argument('--result',required=True)
    args=parser.parse_args();report=inspect(Path(args.stage).resolve(),Path(args.overlay).resolve(),Path(args.manifest).resolve())
    Path(args.result).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],candidates=len(report['candidate_assets']),overlay_assets=len(report['accepted_overlay_assets']),runtime_maps=len(report['runtime_maps']),cook_directories=len(report['proposed_always_cook_directories']),cook_executed=False)))


if __name__=='__main__':
    main()
