"""Native seven-trace/eight-Tap scheduling, callback inputs and preset parity."""
import argparse
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

ORDER=("Direct.Primary","Direct.Second.C","Side.Second.L","Side.Second.R","Direct.Second.L","Direct.Second.R","Side.First.L","Side.First.R")
INDICES=(0,1,4,5,2,3,6,7)
BASE_PLAN=(("local-none","local",None,(0.,800.,300.)),("local-solid","local",0,(0.,800.,300.)),
    ("foreign-near","foreign",4,(0.,800.,300.)),("foreign-far","foreign",0,(0.,6000.,0.)),
    ("local-far","local",4,(0.,6000.,0.)),("flesh","local",1,(0.,800.,300.)),
    ("null-target","null",0,(0.,800.,300.)),("below-limit","foreign",0,(0.,3999.75,0.)),
    ("at-limit","foreign",0,(0.,4000.,0.)),("above-limit","foreign",0,(0.,4000.25,0.)))
NORMALS=(("unit",(0.,-1.,0.)),("zero",(0.,0.,0.)),("nonunit",(0.,-2.,.25)))
PLAN=tuple((name+"-"+label,target,surface,offset,normal) for name,target,surface,offset in BASE_PLAN for label,normal in NORMALS)


def eligible(target,surface,distance):return target!="null" and surface!=1 and (distance<4000. or target=="local")


def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native EarlyReflections run failed")
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","preset_asset_saved","cpp_compile_executed","trace_results_injected","tap_callbacks_replayed","static_functions_registered_as_mixins"):
        require(report[key] is False,"EarlyReflections scope overclaim: "+key)
    for key in ("preset_state_restored","current_dispatch_profiles_restored","owned_actors_destroyed","player_health_unchanged","router_profile_restored","original_static_signatures_preserved","dispatch_regression_passed","whiz_regression_passed"):
        require(report[key] is True,"EarlyReflections state/ABI regression missing: "+key)
    require(len(report["math_regression"])==8 and all(report["math_regression"]),"previous math regression missing")
    wall=report["owned_wall_preflight"]
    require(wall["owned_actor"] is (not report["open_geometry"]),"native owned collision mode preflight failed")
    require(len(report["tap_ids"])>=8 and len(report["early_pairs"])==len(PLAN),"native original preset/scene matrix incomplete")
    hits=misses=queries=taps=0
    for index,(row,plan) in enumerate(zip(report["early_pairs"],PLAN)):
        name,target,surface,offset,normal=plan;active=eligible(target,surface,row["distance"])
        require(row["index"]==index and row["name"]==name,"native reflection matrix reordered")
        require(row["fallback_dispatches"]==row["python_dispatches"]==2,"typed reflection caller/Profile missing")
        require(row["python_eligible"]==(2 if active else 0) and row["python_queries"]==(14 if active else 0) and row["python_taps"]==(16 if active else 0),"Python did not execute the actual seven-query/eight-Tap business")
        values=row["observations"];require(len(values)==4 and values.count(values[0])==4,"original/Python/direct/BP Tap inputs or complete preset state differs")
        events=values[0]["events"];require(len(events)==(8 if active else 0),"original reflection eligibility changed")
        if not active:continue
        queries+=28;taps+=32
        require(tuple(e["suffix"] for e in events)==ORDER and tuple(e["tap_id"] for e in events)==tuple(report["tap_ids"][i] for i in INDICES),"original eight-Tap ordering changed")
        require(events[0]["did_hit"] is (surface is not None),"Direct.Primary must use physical material validity")
        require(all(e["trace_distance"]==4000. for e in events),"authored trace distance changed")
        require(all(e["listener"]==[0.,0.,0.] for e in events[-2:]),"unconnected Side.First listeners were repaired")
        require(all(e["listener"]==row["listener"] for e in events[:-2]),"camera listener snapshot changed")
        hits+=sum(e["did_hit"] for e in events[1:]);misses+=sum(not e["did_hit"] for e in events[1:])
    require(hits>0 and misses>0,"real native trace hit/miss coverage missing")
    return dict(status="passed",cases=len(PLAN),static_and_bp_invocations=len(PLAN)*4,native_business_trace_queries=queries,native_tap_calls=taps,
        actual_trace_hits_in_reference_cases=hits,actual_trace_misses_in_reference_cases=misses,prior_regression_invocations=52,open_geometry=report["open_geometry"],full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
