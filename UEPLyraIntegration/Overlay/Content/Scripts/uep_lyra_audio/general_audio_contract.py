"""Actual static/BP transport into the unchanged default music component family."""
import argparse
from itertools import product
import json
from pathlib import Path
from uep_lyra_weapons.weapon_actor_helpers_contract import require

PLAN=tuple(product((False,True),("invalid","stopped","playing"),(-.5,.7,2.)))
def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native GeneralAudio run failed")
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","static_functions_registered_as_mixins","native_error_branches_exercised","cpp_compile_executed"):
        require(report[key] is False,"GeneralAudio scope overclaim: "+key)
    for key in ("static_signature_flags_preserved","router_profile_restored","music_profile_family_restored","manager_fields_restored","owned_actor_destroyed","player_health_unchanged"):
        require(report[key] is True,"GeneralAudio state/ABI restoration missing: "+key)
    require(len(report["pairs"])==len(PLAN),"GeneralAudio controlled matrix incomplete")
    for index,(row,plan) in enumerate(zip(report["pairs"],PLAN)):
        values=row["observations"];require(row["index"]==index and len(values)==4 and values.count(values[0])==4,"GeneralAudio original/Python/direct/BP receiver/state differs")
        require(row["fallback_dispatches"]==row["python_dispatches"]==2 and row["python_manager_calls"]==2,"ordinary typed router did not forward actual music receiver")
        require(values[0]["intensity"]==0. and values[0]["positive_arguments"]==[plan[0]],"actual music Stinger receiver/reset differs")
    return dict(status="passed",native_cases=len(PLAN),native_static_and_bp_invocations=len(PLAN)*4,actual_music_receiver_entries=len(PLAN)*4,
        native_error_branches_exercised=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
