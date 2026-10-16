"""Post-exit validation only; never imports or launches Unreal."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_world.inventory_pad_network_protocol import PEERS, validate_reports

root = Path(sys.argv[1])
reports = {peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
print(json.dumps(validate_reports(reports), indent=2))
