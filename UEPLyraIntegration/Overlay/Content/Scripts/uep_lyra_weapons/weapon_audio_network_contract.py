"""Default audio routes augment all existing native two-owner firing/Cue gates."""
import argparse
import json
from pathlib import Path
from .weapon_fire_cue_network_contract import validate as validate_cues
from .weapon_ability_fire_network_contract import PEERS,PLAN
from .weapon_audio_cold_contract import ROUTERS,REQUIRED,delta,counters
from .weapon_actor_helpers_contract import require


def validate_audio(server,clients):
    for report in [server,*clients.values()]:
        for field in ("manual_audio_registration","audio_helpers_preloaded_by_probe","audio_profiles_changed_by_probe"):
            require(report[field] is False,"network audio routing was forced by probe: "+field)
    for position,_ in enumerate(PLAN):
        authority=server["cases"][position]
        for key in ROUTERS:
            before=counters(authority["audio_case_before"],key);after=counters(authority["audio_case_after"],key)
            require(before==after,"dedicated authority executed cosmetic audio helper: "+key)
        for peer in PEERS:
            cue=clients[peer]["cases"][position]["native_firing_cues"][0];before,after=cue["audio_before"],cue["audio_after"]
            for key,fields in REQUIRED.items():
                require(after.get(key,{}).get("registered") and after[key]["selected_profile"]=="Python","predicted/remote default audio registration missing: "+key)
                for field in fields:require(delta(before,after,key,field)==1,"predicted/remote actual Python audio dispatch missing: "+peer+"/"+key+"/"+field)
            require(all(row["selected_profile"]=="Python" for row in after.values() if row.get("registered")),"audio helper Profile changed across native Cue")
    return dict(status="passed",weapon=server["weapon"],native_owner_shots=4,native_predicted_remote_cue_entries=8,actual_default_audio_dispatch_entries=32,
        dedicated_server_audio_dispatch_entries=0,audible_playback_accepted=False,full_acceptance=False)


def validate(server,clients):
    validate_cues(server,clients);return validate_audio(server,clients)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True);root=Path(parser.parse_args().directory)
    def read(peer):return json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
    print(json.dumps(validate(read("server"),{peer:read(peer) for peer in PEERS})))
