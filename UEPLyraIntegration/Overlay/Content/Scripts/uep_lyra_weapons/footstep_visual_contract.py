"""Captured-render provenance; visual inspection is a separate evidence step."""
import argparse, hashlib, json, struct
from pathlib import Path
from .footstep_locomotion_contract import validate as locomotion
from .hero_burst_cue_contract import require


def validate(report):
    locomotion(report)
    require(report['visual_inspection_completed'] is False, 'runtime capture must not self-certify visual content')
    require(report['original_view_target_restored'], 'fixture camera was not restored')
    if report['role'] == 'client':
        require([row['kind'] for row in report['images']] == ['before', 'after', 'effect-hidden', 'effect-restored'], 'native render and effect-visibility control images missing')
        require(report['effect_render_visibility_restored'], 'effect visibility control not restored')
        for row in report['images']:
            file = Path(row['path']);data = file.read_bytes()
            require(data.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(data).hexdigest() == row['sha256'], 'native screenshot hash/header differs')
            width, height = struct.unpack('>II', data[16:24])
            require(width >= 640 and height >= 360, 'actual viewport image required')
        require(report['images'][1]['successful_footsteps_at_capture'] >= 1 and report['images'][1]['projected_hits_in_view'] >= 1, 'native effects were not associated with the render view')
    else:
        require(not report['images'], 'server render capture not part of this gate')
    return dict(status='passed', role=report['role'], profile=report['requested_profile'], native_images=len(report['images']), visual_inspection_completed=False, full_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--report', required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
