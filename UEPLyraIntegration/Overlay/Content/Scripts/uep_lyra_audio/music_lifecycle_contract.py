"""Native exact message delivery and delayed native listener cleanup parity."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.weapon_actor_helpers_contract import require

PLAN=(("Lyra.Elimination.Message","local_state",1.),("Lyra.Elimination.Message","local_pawn",.2),
      ("Lyra.Elimination.Message","foreign_state",.2),("Lyra.Elimination.Message","null",.2),
      ("Lyra.Damage.Taken.Message","local_pawn",1.),("Lyra.Damage.Taken.Message","foreign_pawn",.2),
      ("Lyra.Damage.Taken.Message","local_state",.2),("Lyra.Damage.Taken.Message","null",.2),
      ("Lyra.Elimination","local_pawn",.2))


def validate(report):
    require(report["status"]=="passed" and report["error"] is None,"native music lifecycle run failed")
    for field in ("full_acceptance","network_acceptance","child_delay_business_migrated","begin_play_replayed","callback_replayed","python_subscription_roots_added","native_proxies_cancelled_by_probe","cpp_compile_executed"):
        require(report[field] is False,"music lifecycle scope/ownership changed: "+field)
    for field in ("original_music_pointer_restored","natural_manager_fields_restored","player_health_unchanged","owned_actors_destroyed","all_owned_proxy_gi_references_released"):
        require(report[field] is True,"music lifetime/fixture restoration missing: "+field)
    require(report["natural_python_begin_before_probe"]==1,"natural descendant BeginPlay did not enter Python exactly once")
    require(len(report["cases"])==4,"music startup/Profile matrix incomplete")
    for index,row in enumerate(report["cases"]):
        require(row["index"]==index and row["native_begin_calls"]==1 and row["native_proxies_added"]==2,"native startup/listener count differs")
        require(row["component_gi_music_same"] and row["created_new_music"] is (row["mode"]=="create"),"GI persistent music reuse/create policy differs")
        require(len(row["messages"])==len(PLAN),"typed native message matrix incomplete")
        for item,plan in zip(row["messages"],PLAN):
            require(item["channel"]==plan[0] and item["target"]==plan[1] and item["intensity"]==plan[2],"native typed message transform/filter differs")
            require(item["callback_entries"]==int(plan[0]!="Lyra.Elimination"),"exact music listener dispatch count differs")
        require(row["profile_switch_proxy_count_unchanged"] and row["switched_message_intensity"]==1. and row["switched_callback_entries"]==1,"existing subscription did not route current Profile")
        require(row["component_destroyed"] and row["proxy_gi_references_immediately_after_destroy"]==2,"original delayed native cleanup was replaced")
        require(row["native_gc_boundary_observed"] and row["proxy_gi_references_after_broadcast"]==0 and row["owned_proxies_inactive_after_broadcast"],"native unbound listener did not release after GC/message")
    return dict(status="passed",native_component_begin_calls=4,native_listener_proxies=8,typed_message_broadcasts=40,native_after_destroy_broadcasts=16,
        original_native_delayed_cleanup_preserved=True,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
