"""Three actual native worlds, local cosmetic Interface references, no RPC claim."""
import argparse
import json
from pathlib import Path
from .emote_audio_contract import validate as local
from uep_lyra_abilities.auto_respawn_helpers_contract import require


def validate(reports):
    require(set(reports) == {"server", "A", "B0"}, "Character audio software needs server and two real clients")
    server = reports["server"]
    require(server["server_waited_for_client_process_exit"] is True and server["all_local_checks_complete_before_release"] is True and
        server["native_playing_gate"]["native_playing_phase"] is True and set(server["player_ids"]) == {"A", "B0"} and
        len(set(server["player_ids"].values())) == 2, "Character Interface native Playing/identity/exit barriers missing")
    for peer, report in reports.items():
        local(report)
        require(report["peer"] == peer and report["run_id"] == server["run_id"] and report["network_acceptance"] is True and
            report["network_software_only"] is True and report["audio_property_replication_claimed"] is False and
            report["gameplay_state_delivered_by_files"] is False, "Character Interface network scope/peer differs")
        primary = "A" if peer == "server" else peer
        secondary = "B0" if primary == "A" else "A"
        require(report["primary_player_id"] == server["player_ids"][primary] and report["secondary_player_id"] == server["player_ids"][secondary] and
            report["primary_role"] == (3 if peer == "server" else 2) and report["secondary_role"] == (3 if peer == "server" else 1),
            "Character Interface own/foreign native Actor identities/roles differ")
        if peer != "server":
            require(report["native_net_mode"] == "Client" and report["authority_phase_gate_observed"] is True,
                "Character Interface client bypassed actual native readiness")
    return dict(status="passed", native_three_world_software_interface=True, owners=2, roundtrip_cases=36,
        native_gc_worlds=3, audio_property_replication_claimed=False, hardware_sound_verified=False, whole_character_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
