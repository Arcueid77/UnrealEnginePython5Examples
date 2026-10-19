"""Static/public and Blueprint caller math equivalence, including float locals."""
import argparse
from itertools import product
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

ORIGINS=((0.,0.,0.),(1.125,-2.5,3.75),(16777217.125,-33554433.5,123.125))
NORMALS=((1.,0.,0.),(2.,-3.,.5),(0.,0.,0.))
DISTANCES=(0.,.001,1.,1000.,-25.5,1000000.125)
AXES=((0.,0.,1.),(0.,1.,0.),(0.,0.,0.),(0.,0.,2.))
LISTENERS=((0.,10.,0.),(0.,-10.,0.),(5.,0.,0.),(20.,10.,0.),(-10.,-10.,0.),(0.,0.,0.),(0.,.00001,0.))
IMPACTS=((10.,0.,0.),(0.,0.,0.),(3.,4.,5.))
MINIMUMS=(0.,1000.,-1000.,.1,123.456789)
SIDE_PLAN=tuple(product(ORIGINS,NORMALS,DISTANCES,AXES))
WHIZ_PLAN=tuple(product(LISTENERS,ORIGINS[:2],MINIMUMS,IMPACTS))


def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native static math run failed")
    for field in ("full_acceptance","network_acceptance","audible_playback_tested","cpp_compile_executed","static_functions_registered_as_mixins","physics_or_audio_state_written"):
        require(report[field] is False,"static math scope overclaim: "+field)
    require(report["original_static_signatures_preserved"] and report["router_profile_restored"] and report["original_player_health_unchanged"],"static ABI/Profile/Health restoration missing")
    for name,plan in (("side_pairs",SIDE_PLAN),("whiz_pairs",WHIZ_PLAN)):
        rows=report[name];require(len(rows)==len(plan),"native static math matrix incomplete")
        for index,row in enumerate(rows):
            require(row["index"]==index and row["direct_and_bp_callers_equal"] and row["original_python_outputs_equal"] and row["native_next_random_equal"],"static math original/Python/caller/output/RNG differs")
            require(row["fallback_dispatches"]>=2 and row["python_dispatches"]>=2,"typed Object bridge did not execute each native caller")
    return dict(status="passed",native_side_cases=len(SIDE_PLAN),native_whiz_cases=len(WHIZ_PLAN),native_static_and_bp_invocations=(len(SIDE_PLAN)+len(WHIZ_PLAN))*4,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
