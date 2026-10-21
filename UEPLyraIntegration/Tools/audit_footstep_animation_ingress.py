"""Inspect original animation notifies without playing or modifying animations."""
import hashlib, json, sys, traceback
from pathlib import Path
import unreal_engine as ue

script = globals().get('__file__') or next(v for v in sys.argv if Path(v).name == 'audit_footstep_animation_ingress.py')
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def arg(name):
    return next(v.split('=', 1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def inspect():
    stage = require_authoring_stage(arg('UEPAnimationAuditStage'), ue.convert_relative_path_to_full(ue.get_content_dir()))
    official = Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    folder = Path('Content/Characters/Heroes/Mannequin/Animations/Locomotion/Unarmed')
    files = sorted({*folder_path.glob('*Walk_Fwd.uasset'), *folder_path.glob('*Jog_Fwd.uasset')}) if (folder_path := stage/folder).is_dir() else []
    if not files:
        raise RuntimeError('original forward locomotion animations missing')
    hashes = {str(file): sha(file) for file in files}
    sequences = []
    for file in files:
        relative = file.relative_to(stage)
        if sha(official/relative) != hashes[str(file)]:
            raise RuntimeError('source locomotion animation differs')
        package = '/Game/'+relative.relative_to('Content').with_suffix('').as_posix()
        asset = ue.load_object(ue.find_class('AnimSequence'), package+'.'+file.stem)
        notifies = []
        for event in asset.get_property('Notifies'):
            notify = event.Notify
            row = dict(notify_class=notify.get_class().get_path_name() if notify else None,
                notify_name=str(event.NotifyName), trigger_offset=float(event.TriggerTimeOffset),
                track_index=int(event.TrackIndex))
            if notify and notify.is_a(ue.find_class('AnimNotify_LyraContextEffects')):
                trace = notify.get_property('TraceProperties')
                row.update(effect_tag=str(notify.get_property('Effect').TagName), attached=bool(notify.get_property('bAttached')),
                    socket=str(notify.get_property('SocketName')), performs_trace=bool(notify.get_property('bPerformTrace')),
                    trace_channel=int(trace.TraceChannel), trace_end_offset=[float(getattr(trace.EndTraceLocationOffset, key)) for key in ('x', 'y', 'z')],
                    trace_ignores_owner=bool(trace.bIgnoreActor))
            notifies.append(row)
        sequences.append(dict(package=package+'.'+file.stem, relative_path=relative.as_posix(), sha256=hashes[str(file)], notifies=notifies))
    for path, digest in hashes.items():
        if sha(path) != digest:
            raise RuntimeError('read-only animation inspection changed source')
    native = [row for sequence in sequences for row in sequence['notifies'] if row.get('effect_tag')]
    if not native:
        raise RuntimeError('no original native context-effect notifies found')
    return dict(status='passed', assets_modified=False, assets_saved_or_compiled=False,
        runtime_acceptance=False, full_acceptance=False, runtime_dispatch_tested=False,
        animation_playback_executed=False, animation_notify_callbacks_called=False,
        source_animations_byte_identical=True, frozen_asset_hashes=hashes, sequences=sequences,
        native_context_notify_count=len(native),
        native_dispatch_source='Source/LyraGame/Feedback/ContextEffects/AnimNotify_LyraContextEffects.cpp',
        next='Play an unchanged sequence through the native animation system and observe actual Actor/component interface delivery, original floor trace and downstream footstep policy. This inspection is not runtime proof.')


try:
    report = inspect()
except Exception:
    report = dict(status='failed', error=traceback.format_exc())
    ue.log_error(report['error'])
Path(arg('UEPAnimationAuditResult')).write_text(json.dumps(report, indent=2), encoding='utf-8')
if report['status'] != 'passed':
    raise RuntimeError(report['error'])
ue.log('UEP_FOOTSTEP_ANIMATION_AUDIT_PASSED')
