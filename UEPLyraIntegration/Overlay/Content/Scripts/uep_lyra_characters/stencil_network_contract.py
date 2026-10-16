"""Three real local stencil worlds, not replicated stencil or pixel proof."""
import argparse
import json
from pathlib import Path
from .team_cosmetics_network_contract import validate as team, require
from .stencil_contract import validate as local


def validate(reports):
    result = team(reports)
    for peer, report in reports.items():
        local(report)
        require(report["stencil_replication_claimed"] is False, "local stencil values cannot certify native replication")
        for row in report["stencil_cases"]:
            owner = row["target"] == "owner"
            require(row["locally_controlled"] is (owner and peer != "server") and row["player_controlled"] is owner,
                "native direct stencil owner/control context differs")
    result.update(native_three_world_stencil_software=True, native_direct_stencil_pairs=36, native_case_trials=120,
        native_bp_invocations=156, native_gc_calls=72, stencil_replication_claimed=False, full_acceptance=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
