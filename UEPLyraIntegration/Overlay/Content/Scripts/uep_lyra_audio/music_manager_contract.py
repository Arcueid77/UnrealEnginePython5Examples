"""Controlled native base-method parity; lifecycle/listener migration stays open."""
import argparse
from itertools import product
import json
from pathlib import Path
from uep_lyra_weapons.weapon_actor_helpers_contract import require

MENU=tuple(product(("invalid","stopped","playing"),(False,True),(False,True)))
DEATH=tuple(product(("local","foreign","actor","null"),(.125,.8)))
FIRE=tuple(product(("local","foreign","actor","null"),(-2.,.1,.5,5.),(-.25,.4,1.25)))
STINGER=tuple(product(("invalid","stopped","playing"),(False,True),(0.,.9)))
TICK=tuple(product(("invalid","stopped","playing"),(False,True),(-.25,.949,1.25),(0.,1.,9999.)))
PLANS={"SetIsMenu":MENU,"Receive Player Death":DEATH,"Receive Weapon Fire":FIRE,"Fire Stinger":STINGER,"ReceiveTick":TICK}


def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native music control run failed")
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","begin_play_listeners_migrated","child_delay_business_migrated","cpp_compile_executed"):
        require(report[key] is False,"music control scope overclaim: "+key)
    for key in ("profile_restored","manager_fields_restored","owned_actors_destroyed","player_health_unchanged","original_signatures_preserved"):
        require(report[key] is True,"music state/ABI restoration missing: "+key)
    require(report["natural_python_tick_before_probe"]>0,"actual inherited native Tick never entered the base Python policy")
    calls=0
    for method,plan in PLANS.items():
        rows=report["pairs"][method];require(len(rows)==len(plan),"music case matrix incomplete: "+method)
        for index,(row,args) in enumerate(zip(rows,plan)):
            count=1 if method=="ReceiveTick" else 2;values=row["observations"]
            require(row["index"]==index and len(values)==count*2 and values.count(values[0])==len(values),"native original/Python/direct/BP state differs: "+method+str(index))
            require(row["fallback_dispatches"]==row["python_dispatches"]==count,"music selected Profile did not execute each call")
            state=values[0]
            if method=="SetIsMenu":require(state["menu"]==args[2],"SetIsMenu incorrectly wrote component variable")
            if method=="Receive Player Death":require(state["intensity"]==(1. if args[0]=="local" else args[1]),"death local-view guard differs")
            if method=="Receive Weapon Fire":require(state["intensity"]==(max(0.,min(1.,args[2]+args[1])) if args[0]=="local" else args[2]),"weapon-fire guard/clamp differs")
            if method=="Fire Stinger":require(state["intensity"]==0.,"negative/positive Stinger did not reset intensity")
            calls+=len(values)
    return dict(status="passed",native_cases=sum(map(len,PLANS.values())),native_calls=calls,base_methods=5,public_blueprint_caller_methods=4,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
