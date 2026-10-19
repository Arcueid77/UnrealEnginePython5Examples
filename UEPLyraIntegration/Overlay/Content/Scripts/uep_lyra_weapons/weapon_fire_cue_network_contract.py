"""Typed Cue transport augments real native prediction/cost/damage replication."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.network_identity import same
from .weapon_ability_fire_network_contract import validate as validate_firing,PEERS,PLAN,near_vectors
from .weapon_actor_helpers_contract import require
RIFLE_SOUND="/Game/Audio/Sounds/Weapons/Rifle2/MSS_Weapons_Rifle2_Fire.MSS_Weapons_Rifle2_Fire"


def validate(server,clients):
    validate_firing(server,clients)
    for report in [server,*clients.values()]:
        require(report["cue_handler_replayed"] is False and report["cue_assets_or_policy_changed"] is False,"network Cue scope overclaim")
    for position,(_,profile) in enumerate(PLAN):
        authority=server["cases"][position];require(authority["native_firing_cues"]==[],"dedicated authority executed cosmetic OnBurst")
        for peer in PEERS:
            row=clients[peer]["cases"][position];require(len(row["native_firing_cues"])==1,"predicted or remote native Cue entry count differs")
            cue=row["native_firing_cues"][0];require(cue["profile"]==profile and same(cue["target"],authority["source_identity"]),"actual native Cue Profile/source differs")
            require(len(cue["payloads"])==1 and cue["payloads"][0]==dict(positions=[cue["location"]],normals=[cue["normal"]],surfaces=[cue["surface"]]),"native replicated Cue to typed weapon payload differs")
            require(len(cue["rifle_sounds"])==int(server["weapon"]=="rifle") and all(value["sound"]==RIFLE_SOUND and same(value["target"],authority["source_identity"]) for value in cue["rifle_sounds"]),"native Rifle-only sound/target transport differs")
            if profile=="Python":
                order=["SendWeaponFire","Weapon.Fire"]+(["Weapon.TriggerFireAudio"] if server["weapon"]=="rifle" else [])+["SetWeaponSoundParams","EarlyReflections","WhizBy"]
                require(cue["python_order"]==order,"network native audio orchestration order differs")
        a,b=(clients[peer]["cases"][position]["native_firing_cues"][0] for peer in PEERS)
        require(near_vectors(a["location"],b["location"]) and near_vectors(a["normal"],b["normal"],.002) and a["surface"]==b["surface"],"native predicted/remote Cue quantized payload differs")
    return dict(status="passed",weapon=server["weapon"],native_predicted_owner_shots=4,native_predicted_remote_cue_entries=8,audible_playback_accepted=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True);root=Path(parser.parse_args().directory)
    def read(peer):return json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
    print(json.dumps(validate(read("server"),{peer:read(peer) for peer in PEERS})))
