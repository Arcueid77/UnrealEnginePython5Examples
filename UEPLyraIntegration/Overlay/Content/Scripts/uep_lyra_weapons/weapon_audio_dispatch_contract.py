"""Independent acceptance of native static calls and actual audio/tap state."""
import argparse
from itertools import product
import json
import math
from pathlib import Path
import struct
from .weapon_actor_helpers_contract import require

PROFILES=("BlueprintFallback","Python")
HIT_OFFSETS=((125.,-250.,50.),(-10.,100.,0.),(0.,0.,0.))
TAP_PLAN=tuple(product((False,True),(-1250.125,0.,.125,8000.,20000.),(0.,500.125,1500.,16777217.125),HIT_OFFSETS))
PARAM_PLAN=("local","remote","not-pawn","null","empty-audio","invalid-instigator","no-controller")
FIRE_PLAN=tuple(product(("local","remote","null"),(-2.5,0.,.125,3.)))
DEBUG_PLAN=(("UEPDispatchTap",0.,-60.,180.),("UEPDispatchTap",.125,-9.25,-45.5),("另一个Tap",123.456,0.,0.))


def f32(value):return struct.unpack("<f",struct.pack("<f",value))[0]
def clamp(value):return max(0.,min(1.,value))
def expected_tap(plan,camera,right):
    hit,travel,distance,offset=plan
    if not hit:return dict(DelayLength=123.25,Gain=-60.,PanInDegrees=-67.125)
    point=[a+b for a,b in zip(camera,offset)];listener=[point[0]+distance,point[1]+distance/3.,point[2]]
    hit_distance=f32(math.sqrt(sum((a-b)**2 for a,b in zip(listener,point))));ratio=(f32(travel)+hit_distance)/10000.
    delta=[a-b for a,b in zip(camera,point)];size=math.sqrt(sum(v*v for v in delta));direction=[v/size for v in delta] if size*size>.0001 else [0.,0.,0.]
    return dict(DelayLength=f32(10.+ratio*ratio*590.),Gain=f32(-9.-51.*clamp(ratio*clamp(hit_distance/1000.))),PanInDegrees=f32(sum(a*b for a,b in zip(right,direction))*180.))


def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native audio dispatch run failed")
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","debug_pixels_tested","cpp_compile_executed","static_functions_registered_as_mixins","preset_asset_saved"):
        require(report[key] is False,"audio dispatch scope overclaim: "+key)
    for key in ("router_profile_restored","music_observer_removed","owned_actors_destroyed","original_instigator_restored","original_player_health_unchanged","preset_state_restored","original_static_signatures_preserved"):
        require(report[key] is True,"native audio cleanup/ABI missing: "+key)
    for label,plan in (("tap_pairs",TAP_PLAN),("parameter_pairs",PARAM_PLAN),("fire_pairs",FIRE_PLAN),("debug_pairs",DEBUG_PLAN)):
        rows=report[label];require(len(rows)==len(plan),"native audio matrix incomplete: "+label)
        for index,row in enumerate(rows):
            require(row["index"]==index and len(row["observations"])==4,"native direct/BP caller evidence missing")
            require(row["observations"].count(row["observations"][0])==4,"native original/Python/caller state differs: "+label+str(index))
            require(row["fallback_dispatches"]==2 and row["python_dispatches"]==2,"four static caller dispatches required")
            require(row["expected_behavior"],"authored native branch behavior differs: "+label+str(index))
            observed=row["observations"][0]
            if label=="fire_pairs":
                who,strength=plan[index];expected=[dict(player=report["local_pawn"],strength=strength)] if who=="local" else []
                require(observed==expected,"first local Pawn/music strength policy changed")
            elif label=="parameter_pairs":
                scenario=plan[index];expected=dict(PawnSeed=321,MagazineAmmo=777,Unrelated=19)
                if scenario=="local":expected.update(PawnSeed=-1,MagazineAmmo=report["actual_magazine_ammo"])
                if scenario=="remote":expected["PawnSeed"]=report["remote_pawn_seed"]
                require(observed==[expected,expected],"audio seed/ammo/preservation policy changed")
            elif label=="tap_pairs":
                require(observed["TapId"]==report["owned_tap_id"] and observed["TapLineMode"]==1 and observed["OutputChannel"]==0,"tap identity/mode/channel policy changed")
                expected=expected_tap(plan[index],report["camera_location"],report["camera_right"])
                require(all(math.isclose(observed[key],value,rel_tol=2e-6,abs_tol=2e-5) for key,value in expected.items()),"tap delay/gain/pan formula differs")
            else:require(observed is True,"native DebugPrintTap did not return void")
    require(len(report["math_regression"])==8 and all(report["math_regression"]),"previous math static/BP routing regression")
    return dict(status="passed",tap_cases=len(TAP_PLAN),audio_parameter_cases=len(PARAM_PLAN),music_cases=len(FIRE_PLAN),debug_call_cases=len(DEBUG_PLAN),
        dispatch_invocations=4*(len(TAP_PLAN)+len(PARAM_PLAN)+len(FIRE_PLAN)+len(DEBUG_PLAN)),math_regression_invocations=32,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
