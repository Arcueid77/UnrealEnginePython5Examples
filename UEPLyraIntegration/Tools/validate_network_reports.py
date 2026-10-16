"""External post-exit report validation; this does not import or start Unreal."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Overlay' / 'Content' / 'Scripts'))
from uep_lyra_network_protocol import validate_run

parser = argparse.ArgumentParser()
parser.add_argument('--directory', required=True)
parser.add_argument('--run-id', required=True)
args = parser.parse_args()
directory = Path(args.directory)
reports = {peer: json.loads((directory / (peer + '.json')).read_text(encoding='utf-8-sig'))
           for peer in ('server', 'A', 'B0', 'B1')}
result = validate_run(reports, args.run_id)
print(json.dumps(result))
