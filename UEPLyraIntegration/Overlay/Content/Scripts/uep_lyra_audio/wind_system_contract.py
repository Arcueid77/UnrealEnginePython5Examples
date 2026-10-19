"""Original native MultiGate progress must survive mixed Profile wind updates."""
import argparse
from itertools import product
import json
from pathlib import Path
from uep_lyra_weapons.weapon_actor_helpers_contract import require

PLAN=tuple(product((2000.,0.,-100.,1234.125),(0,1),("exterior","pause")))
TICKS=30
def exterior(pattern,tick):return pattern=="exterior" or tick not in range(4,9) and tick not in range(19,22)
def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native wind run failed")
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","multigate_state_reimplemented_in_python","trace_results_injected","cpp_compile_executed"):
        require(report[key] is False,"wind scope/scheduler changed: "+key)
    require(report["owned_actors_destroyed"] and report["player_health_unchanged"],"wind fixture restoration missing")
    require(report["natural_python_ticks"]>=5,"actual engine wind Tick did not run")
    require(len(report["cases"])==len(PLAN),"wind paired-actor matrix incomplete")
    queries=0
    for index,(row,plan) in enumerate(zip(report["cases"],PLAN)):
        distance,size,pattern=plan;require(row["index"]==index and len(row["ticks"])==TICKS,"wind sequence incomplete")
        step=0
        for tick,item in enumerate(row["ticks"]):
            active=exterior(pattern,tick);stage=step%5 if active else None
            require(item["index"]==tick and item["stages"]==[stage,stage],"native MultiGate progress restarted or advanced during interior pause")
            require(item["states"][0]==item["states"][1],"original/Python state or actual audio parameter differs")
            require(all(s["player_array_size"]==size for s in item["states"]),"native no-resize Array_Set behavior changed")
            require(item["python_queries"]==int(active),"actual Python trace did not execute exactly for selected native stage")
            step+=int(active);queries+=int(active)
    return dict(status="passed",paired_cases=len(PLAN),native_event_calls=len(PLAN)*TICKS*2,actual_python_native_traces=queries,native_scheduler_reused=True,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
