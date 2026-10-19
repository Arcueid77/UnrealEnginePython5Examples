"""Real firing plus controlled native GAS Cue/material transport, not audibility."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .weapon_ability_fire_contract import validate as validate_firing,PROFILES,PLAN as FIRING_PLAN
from .weapon_actor_helpers_contract import require

WEAPONS=("Pistol","Rifle","Shotgun")
PLAN=tuple((weapon,profile,surface) for weapon in WEAPONS for profile in PROFILES for surface in (0,1,4))


def validate(report):
    validate_firing(report)
    require(report["cue_observers_and_profiles_restored"] and report["native_static_audio_abi_preserved"] and not report["cue_handler_replayed"],"native Cue observer/ABI/scope proof missing")
    rows=report["controlled_cue_cases"];require(Counter((row["weapon"],row["profile"],row["surface"]) for row in rows)==Counter(PLAN),"controlled native GAS Cue/material matrix missing")
    for row in rows:
        require(row["native_gas_cue_requests"]==1 and row["native_cue_entries"]==1 and row["native_weapon_fire_entries"]==1 and row["typed_payload_matches"],"native typed Cue/material/weapon transport differs")
        require(row["rifle_audio_entries"]==int(row["weapon"]=="Rifle") and row["rifle_sound_matches"],"native Rifle-only sound transport differs")
        if row["profile"]=="Python":require(row["python_order_matches"],"original native audio orchestration order differs")
    require(len(report["native_input_cue_cases"])==16,"real input Cue/montage matrix incomplete")
    expected=[(weapon.title(),profile) for weapon,profile,_ in FIRING_PLAN]+[("Pistol",profile) for profile in PROFILES for _ in range(4)]
    require([(row["weapon"],row["profile"]) for row in report["native_input_cue_cases"]]==expected,"actual native input Cue weapon/Profile order differs")
    for row in report["native_input_cue_cases"]:
        require(row["native_cue_entries"]==1 and row["native_weapon_fire_entries"]==1 and row["typed_payload_matches"] and row["rifle_sound_matches"],"actual native input Cue payload/orchestration differs")
        require(row["rifle_audio_entries"]==int(row["weapon"]=="Rifle"),"actual native input Rifle-only audio differs")
    return dict(status="passed",controlled_native_gas_cue_cases=18,real_native_input_cue_cases=16,native_static_audio_business_migrated=False,audible_playback_accepted=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
