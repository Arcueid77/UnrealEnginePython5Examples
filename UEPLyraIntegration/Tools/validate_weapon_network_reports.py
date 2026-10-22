"""Validate finished processes, not merely in-game success markers."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Overlay' / 'Content' / 'Scripts'))
from uep_lyra_weapon_protocol import validate_reports

parser = argparse.ArgumentParser()
parser.add_argument('--directory', required=True)
parser.add_argument('--run-id', required=True)
parser.add_argument('--combat-hud', action='store_true')
parser.add_argument('--debug-spread', action='store_true')
parser.add_argument('--production-reticles', action='store_true')
parser.add_argument('--reticle-hosts', action='store_true')
parser.add_argument('--ability-progress', action='store_true')
parser.add_argument('--ability-failure', action='store_true')
parser.add_argument('--dash-cooldown', action='store_true')
parser.add_argument('--respawn-timer', action='store_true')
parser.add_argument('--quickbar-slots', action='store_true')
parser.add_argument('--nameplates', action='store_true')
parser.add_argument('--gameplay-profile', choices=('Python', 'BlueprintFallback'))
args = parser.parse_args()
root = Path(args.directory)
reports = {peer: json.loads((root / (peer + '.json')).read_text(encoding='utf-8-sig'))
           for peer in ('server', 'A', 'B0', 'B1')}
if args.gameplay_profile:
    from uep_lyra_weapons.integrated_profile_contract import validate
    for report in reports.values(): validate(report['integrated_gameplay'], args.gameplay_profile)
print(json.dumps(validate_reports(reports, args.run_id, combat_hud=args.combat_hud, debug_spread=args.debug_spread,
                                 production_reticles=args.production_reticles, reticle_hosts=args.reticle_hosts,
                                 ability_progress=args.ability_progress, ability_failure=args.ability_failure,
                                 dash_cooldown=args.dash_cooldown, respawn_timer=args.respawn_timer, quickbar_slots=args.quickbar_slots,
                                 nameplates=args.nameplates)))
