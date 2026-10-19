"""Native parent/Delay/CP message parity across original and Python continuations."""
import argparse
from itertools import product
import json
from pathlib import Path
from uep_lyra_weapons.weapon_actor_helpers_contract import require

CLASSES={"front_end":"/Game/Audio/Blueprints/B_MusicManagerComponent_FE.B_MusicManagerComponent_FE_C",
    "elimination":"/ShooterCore/Elimination/B_MusicManagerComponent_Elimination.B_MusicManagerComponent_Elimination_C",
    "control_point":"/ShooterCore/ControlPoint/B_MusicManagerComponent_ControlPoint.B_MusicManagerComponent_ControlPoint_C"}
PLAN=tuple(product(CLASSES,("BlueprintFallback","Python"),("normal","switch","destroy")))


def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native music family run failed")
    for key in ("full_acceptance","network_acceptance","begin_play_replayed","delay_callback_replayed","message_callback_replayed","python_subscription_roots_added","production_proxies_cancelled_by_probe","cpp_compile_executed"):
        require(report[key] is False,"family transport/lifetime scope changed: "+key)
    for key in ("original_gi_music_preserved","natural_manager_fields_restored","base_profile_family_restored","player_health_unchanged","owned_actors_destroyed","all_owned_proxy_gi_references_released","diagnostic_probe_roots_removed"):
        require(report[key] is True,"family restoration missing: "+key)
    require(len(report["cases"])==len(PLAN),"family matrix incomplete")
    for index,(row,plan) in enumerate(zip(report["cases"],PLAN)):
        label,profile,mode=plan;require(row["index"]==index and (row["class"],row["profile"],row["mode"])==plan,"family case order differs")
        require(row["native_parent_begin_calls"]==1 and row["immediate_proxy_count"]==2,"parent startup duplicated or bypassed")
        require(row["after_delay_calls"]==int(mode!="destroy"),"native child Delay continuation count differs")
        if mode!="destroy":
            require(.18<=row["after_delay_elapsed"]<1.2,"native original .2 Delay timing differs")
            require(row["audio_menu"] is (label=="front_end") and row["component_menu"] is False,"menu parameter/component split changed")
            require(row["proxy_count_after_delay"]==(3 if label=="control_point" else 2),"CP listener startup count differs")
            require(row["after_delay_profile"]==("Python" if profile=="BlueprintFallback" else "BlueprintFallback") if mode=="switch" else row["after_delay_profile"]==profile,"continuation did not use current Profile")
            if label=="control_point":
                require(row["stinger_positive_arguments"]==[True,False,False] and row["captured_callback_entries"]==3,"native team message transform differs")
        else:require(row["proxy_count_after_delay"]==2,"destroyed CP registered a late listener")
        require(row["proxy_refs_after_gc_and_messages"]==0 and row["proxies_inactive_after_gc_and_messages"],"original native listener cleanup failed")
    return dict(status="passed",cases=len(PLAN),native_parent_begins=18,native_delay_completions=12,native_destroyed_delay_suppression=6,control_point_messages=12,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
