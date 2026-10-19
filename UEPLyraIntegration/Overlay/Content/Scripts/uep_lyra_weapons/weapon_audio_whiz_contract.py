"""Native WhizBy component state parity on offline and disabled-audio backends."""
import argparse
from itertools import product
import json
import math
from pathlib import Path
import struct
from .weapon_actor_helpers_contract import require

PROFILES=("BlueprintFallback","Python")
TRAJECTORIES=(((1000.,250.,0.),(-1000.,-250.,0.)),((1000.,-250.,0.),(-1000.,250.,0.)),
    ((250.,50.,0.),(250.,50.,0.)),((1000.,0.,0.),(2000.,0.,0.)),((-1500.,250.,100.),(-500.,100.,25.)))
PLAN=tuple(product(("foreign","local","null"),(None,0,1,4),range(len(TRAJECTORIES))))
SOUND="/Game/Audio/MetaSounds/sfx_WhizBys_nl_meta.sfx_WhizBys_nl_meta"


def f32(value):return struct.unpack("<f",struct.pack("<f",value))[0]
def expected_geometry(listener,origin,impact):
    delta=[b-a for a,b in zip(origin,impact)];den=sum(v*v for v in delta)
    t=max(0.,min(1.,sum((p-a)*d for p,a,d in zip(listener,origin,delta))/den)) if den else 0.
    location=[a+t*d for a,d in zip(origin,delta)];perp=[p-a for p,a in zip(listener,location)]
    length=math.sqrt(sum(v*v for v in perp));normal=[v/length for v in perp] if length*length>.0001 else [0.,0.,0.]
    yaw=math.atan2(delta[1],delta[0]) if den>.0001 else 0.;right=(-math.sin(yaw),math.cos(yaw),0.)
    from_right=sum(a*b for a,b in zip(right,normal))<=0.
    distance=f32(math.sqrt(sum((a-b)**2 for a,b in zip(listener,origin))))
    return dict(location=location,spread=f32(f32(length)+1000.),onset=f32(distance*.000010),swap=1. if from_right else 0.)


def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native WhizBy differential failed")
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","preset_asset_saved","cpp_compile_executed","static_functions_registered_as_mixins"):
        require(report[key] is False,"WhizBy scope overclaim: "+key)
    for key in ("router_profile_restored","owned_components_destroyed","owned_actors_destroyed","player_health_unchanged","original_static_signatures_preserved","dispatch_regression_passed"):
        require(report[key] is True,"WhizBy cleanup/ABI/regression missing: "+key)
    require(len(report["math_regression"])==8 and all(report["math_regression"]),"previous static math caller regression")
    require(len(report["whiz_pairs"])==len(PLAN),"WhizBy matrix incomplete")
    spawned=0
    for index,(row,plan) in enumerate(zip(report["whiz_pairs"],PLAN)):
        eligible=plan[0]=="foreign" and plan[1]!=1;count=int(eligible and not report["no_sound"])
        require(row["index"]==index and row["fallback_dispatches"]==2 and row["python_dispatches"]==2,"actual typed WhizBy caller/Profile missing")
        require(row["math_dispatches"]==(4 if eligible else 0),"WhizBy eligibility/math dispatch changed")
        values=row["observations"];require(len(values)==4 and values.count(values[0])==4,"native WhizBy original/Python/direct/BP state differs")
        require(all(len(value)==count for value in values),"native WhizBy component creation branch differs")
        spawned+=count*4
        if count:
            state=values[0][0];expected=expected_geometry(row["listener"],row["origin"],row["impact"])
            require(state["sound"]==SOUND and state["playing"] and state["auto_destroy"] and state["attenuation_success"],"native WhizBy sound/play/attenuation policy differs")
            require(state["volume"]==state["pitch"]==1.,"native WhizBy gain/pitch defaults differ")
            require(all(math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-5) for a,b in zip(state["location"],expected["location"])),"native WhizBy closest segment point differs")
            require(math.isclose(state["attenuation"]["StereoSpread"],expected["spread"],rel_tol=1e-6,abs_tol=1e-4),"native WhizBy attenuation spread differs")
            require(math.isclose(state["parameters"]["OnsetDelay"],expected["onset"],rel_tol=1e-6,abs_tol=1e-7),"native WhizBy onset delay differs")
            require(state["parameters"]["SwapLR"]==expected["swap"],"native WhizBy stereo side differs")
    return dict(status="passed",cases=len(PLAN),static_and_bp_invocations=len(PLAN)*4,actual_audio_components=spawned,no_sound=report["no_sound"],math_regression_invocations=32,dispatch_regression_invocations=16,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
