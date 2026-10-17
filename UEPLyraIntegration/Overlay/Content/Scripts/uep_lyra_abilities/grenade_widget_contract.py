"""Independent native grant/avatar/removal and attached-widget acceptance gate."""
import argparse
import json
from pathlib import Path


def require(condition,message):
    if not condition: raise RuntimeError(message)


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native Grenade UI report missing")
    for name in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","grenade_throw_projectile_damage_migrated","callback_replay","health_properties_written","ability_spec_properties_written","inventory_properties_written","native_ui_pool_written"):
        require(report[name] is False,"Grenade UI scope overclaim: "+name)
    for name in ("native_give_clear_called_by_fixture","observers_restored","test_owned_specs_removed"):
        require(report[name] is True,"native Grenade lifecycle/cleanup missing: "+name)
    require(report["observation_errors"]==[] and report["reset_request_entry"]=="SendGameplayEventToActor(GameplayEvent.RequestReset)","native event witness/reset input differs")
    require(len(report["cases"])==2,"both original/Python Grenade UI trials required")
    for row,profile in zip(report["cases"],("BlueprintFallback","Python")):
        require(row["profile"]==profile and row["native_class"]=="/ShooterCore/Input/Abilities/GA_Grenade.GA_Grenade_C","native Grenade class/profile changed")
        require(row["initial_ui_invalid"] and row["reset_requests"]==2 and len(set(row["new_pawns"]))==2 and row["quiet_ticks"]>=20,
            "real grant/two Pawn replacements/quiet interval missing")
        require(row["original_handle_preserved"] and row["original_widget_restored"] and row["specs_restored"],"original Grenade state not restored")
        require(len(row["registered_widgets"])==2,"native attached Grenade UI witness missing")
        events=row["native_callbacks"]
        require(len(events)==3,"native Avatar/Avatar/Removed callbacks incomplete or duplicated")
        for event,method,before,after in zip(events,("K2_OnPawnAvatarSet","K2_OnPawnAvatarSet","K2_OnAbilityRemoved"),(False,True,True),(True,True,True)):
            require(event["method"]==method and event["profile"]==profile and event["native_callback"] is True and event["cls"]==row["native_class"],"native event identity differs")
            require(event["before"]["valid"] is before and event["after"]["valid"] is after and event["before"]["arity"]==event["after"]["arity"]==2,"native UI handle transition missing")
        require(all(event["owner"]==report["owning_player_state"] for event in events),"Grenade owning PlayerState context changed")
        counts=events[-1]["counts"]
        expected=dict(avatar_python=2 if profile=="Python" else 0,removed_python=1 if profile=="Python" else 0,
            avatar_fallback=2 if profile=="BlueprintFallback" else 0,removed_fallback=1 if profile=="BlueprintFallback" else 0,
            existing_noops=int(profile=="Python"),nonlocal_noops=0,missing_subsystem_noops=0,
            registrations=int(profile=="Python"),unregistrations=int(profile=="Python"),opaque_default_noops=int(profile=="Python"))
        require(counts==expected,"selected Grenade handler branch counts differ")
    return dict(status="passed",native_profile_trials=2,native_avatar_callbacks=4,native_removal_callbacks=2,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True);args=parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
