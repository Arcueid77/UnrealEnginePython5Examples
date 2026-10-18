"""Independent real two-owner Grenade UI/native replication semantic gate."""
import argparse
import json
from pathlib import Path
from .grenade_widget_contract import require
from .network_identity import key as wire_key,same as same_wire

PEERS=("A","B0")
PLAN=tuple((peer,profile) for peer in PEERS for profile in ("BlueprintFallback","Python"))
CLASS="/ShooterCore/Input/Abilities/GA_Grenade.GA_Grenade_C"


def lazy_observation(report):
    value=report.get("lazy_lifecycle_observation")
    if value is None: return
    require(value["installed"] is True and value["restored"] is True and value["preloaded"] is False and
        value["cdo_written"] is False and bool(value["event_files"]),"lazy lifecycle observation was not actually installed/restored without preload")


def events(rows,profile,owner,*,local):
    require(len(rows)==3,"native Grenade avatar/avatar/removal event count differs")
    before=(False,True,True) if local else (False,False,False)
    after=(True,True,True) if local else (False,False,False)
    for row,method,left,right in zip(rows,("K2_OnPawnAvatarSet","K2_OnPawnAvatarSet","K2_OnAbilityRemoved"),before,after):
        require(row["method"]==method and row["profile"]==profile and row["owner"]==owner and row["cls"]==CLASS and row["native_callback"] is True,"native Grenade event identity/context differs")
        require(row["before"]["valid"] is left and row["after"]["valid"] is right and row["before"]["arity"]==row["after"]["arity"]==2,"native local/nonlocal opaque UI handle transition differs")
    python=profile=="Python"
    expected=dict(avatar_python=2 if python else 0,removed_python=int(python),avatar_fallback=0 if python else 2,removed_fallback=int(not python),
        existing_noops=int(python and local),nonlocal_noops=2 if python and not local else 0,missing_subsystem_noops=0,
        registrations=int(python and local),unregistrations=int(python),opaque_default_noops=int(python))
    require(rows[-1]["counts"]==expected,"native Grenade local/nonlocal branch counts differ")


def client(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Client" and report["native_role"]==2 and report["peer"] in PEERS,"actual native owner client missing")
    for field in ("client_native_give_clear_called","native_give_clear_called_by_fixture","callback_replay","health_properties_written","ability_spec_properties_written","inventory_properties_written","native_ui_pool_written","full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","grenade_throw_projectile_damage_migrated","packet_loss_tested","travel_rejoin_tested"):
        require(report[field] is False,"client UI scope overclaim: "+field)
    require(report["observers_restored"] and report["test_owned_specs_removed"] and report["observation_errors"]==[],"client native cleanup/observation error")
    lazy_observation(report)
    require(len(report["cases"])==len(PLAN),"native client UI matrix incomplete")
    if report.get("network_identity_required"):
        probe=report["native_identity_null_probe"]
        require(probe["valid"] is False and probe["transport"]=="InvalidObject" and probe["wire_id"]=="","native null identity fabricated")
    for position,(row,(owner,profile)) in enumerate(zip(report["cases"],PLAN)):
        local=owner==report["peer"]
        require((row["position"],row["owner"],row["profile"],row["own"])==(position,owner,profile,local),"native viewer case identity differs")
        require(row["quiet_ticks"]>=20 and row["original_widgets_restored"] and row["original_specs_restored"],"native client quiet/restoration missing")
        require(len(row["waves"])==2,"two native replicated Pawn replacements missing")
        for number,wave in enumerate(row["waves"],1):
            require(wave["number"]==number and wave["pawn"]!=wave["old_pawn"] and wave["source_role"]==(2 if local else 1) and
                wave["health"]==100. and wave["canonical_bound_asc"] is True and wave["own"] is local,
                "actual native owner/foreign healthy canonical Pawn replacement missing")
            require(len(wave["widgets"])==(2 if local else 1),"own UI duplicate or foreign UI interference")
            if report.get("network_identity_required"):
                identity=wave["network_identity"]
                require(wire_key(identity) is not None and identity["local_role"]==wave["source_role"],"native viewer wire identity/role missing")
        require(row["waves"][0]["pawn"]==row["waves"][1]["old_pawn"] and row["waves"][0]["widgets"]==row["waves"][1]["widgets"],"native reset sequence/UI persistence differs")
        if local: events(row["native_callbacks"],profile,report["owning_player_state"],local=True)
        else: require(row["native_callbacks"]==[],"foreign owner executed local cloned ability")
    return True


def validate(server,viewers):
    require(server["status"]=="passed" and server["error"] is None and server["native_mode"]=="DedicatedServer" and
        set(viewers)==set(PEERS) and len(set(server["player_ids"].values()))==2,"two real owners/dedicated authority missing")
    lazy_observation(server)
    for name in ("server_waited_for_client_process_exit","observers_restored","test_owned_specs_removed"):
        require(server[name] is True,"authority cleanup/exit gate missing: "+name)
    for name in ("health_properties_written","callback_replay","native_ui_pool_written","full_acceptance","packaged_runtime","physical_input_tested","packet_loss_tested","travel_rejoin_tested"):
        require(server[name] is False,"authority scope overclaim: "+name)
    require(server["observation_errors"]==[] and len(server["cases"])==len(PLAN),"authority native UI matrix/error")
    cleanup=server["native_pre_release_specs"]
    require(set(cleanup)==set(PEERS),"live pre-release native spec snapshot missing")
    for row in cleanup.values():
        require(row["native_asc_alive"] is True and len(row["original_handles"])==1 and row["current_handles"]==row["original_handles"] and
            row["original_specs_restored"] is True,"authority spec restoration was not proven before native peer teardown")
    for peer,value in viewers.items():
        client(value);require(value["player_id"]==server["player_ids"][peer],"real native player identity differs")
        require(bool(value.get("network_identity_required"))==bool(server.get("network_identity_required")),"partial native wire identity treatment")
        require(bool(value.get("join_reset_stress_requested"))==bool(server.get("join_reset_stress")),"partial native join Reset treatment")
    stress=server.get("join_reset_stress")
    if stress is not None:
        require(stress["enabled"] is True and stress["completed"] is True and stress["callback_replay"] is False and stress["health_or_asc_written"] is False and
            stress["entry"]=="SendGameplayEventToActor(GameplayEvent.RequestReset)" and stress["requests_per_owner"]==2,"native bounded join Reset input proof missing")
        requests=stress["requests"]
        require(len(requests)==4 and {row["player_id"] for row in requests}==set(server["player_ids"].values()),"two-owner native join input budget not actually exercised")
        for player_id in server["player_ids"].values():
            rows=[row for row in requests if row["player_id"]==player_id]
            require([row["request_number"] for row in rows]==[1,2] and rows[0]["old_actor"]!=rows[1]["old_actor"] and
                not same_wire(rows[0]["old_network_identity"],rows[1]["old_network_identity"]),"join inputs did not target successive real native Pawns")
            require(all(row["native_reset_class"]=="/Script/LyraGame.LyraGameplayAbility_Reset" and row["native_reset_existing_specs"]==1 and
                row["native_reset_callback_delta"]==1 and row["old_network_identity"]["local_role"]==3 and wire_key(row["old_network_identity"]) is not None for row in rows),"join input lacks native existing Reset/actual callback/authoritative mapped Pawn")
    if server.get("network_identity_required"):
        probe=server["native_identity_null_probe"]
        require(probe["valid"] is False and probe["transport"]=="InvalidObject" and probe["wire_id"]=="","authority null identity fabricated")
    for position,(row,(owner,profile)) in enumerate(zip(server["cases"],PLAN)):
        require((row["position"],row["owner"],row["profile"])==(position,owner,profile) and row["reset_requests"]==2 and
            row["native_locally_controlled"] is False and row["original_specs_restored"],"authority remote-owner lifecycle differs")
        events(row["native_callbacks"],profile,row["owning_player_state"],local=False)
        require(len(row["waves"])==2 and row["waves"][0]["pawn"]==row["waves"][1]["old_pawn"],"authority native reset sequence missing")
        if server.get("network_identity_required"):
            require(not same_wire(row["waves"][0]["network_identity"],row["waves"][1]["network_identity"]),"native resets reused one network Actor identity")
        for number,wave in enumerate(row["waves"],1):
            require(wave["number"]==number and wave["pawn"]!=wave["old_pawn"] and wave["health"]==100.,"authority new native healthy Pawn missing")
            if server.get("network_identity_required"):
                identity=wave["network_identity"]
                require(wire_key(identity) is not None and identity["local_role"]==3,"native authority wire identity missing")
            for peer in PEERS:
                require(wave["viewers"][peer]==viewers[peer]["cases"][position]["waves"][number-1],"native wave acknowledgement differs")
                if server.get("network_identity_required"):
                    require(same_wire(identity,wave["viewers"][peer]["network_identity"]),"viewer bound a different network Actor despite matching player/health")
        for peer in PEERS: require(row["viewers"][peer]==viewers[peer]["cases"][position],"native final viewer acknowledgement differs")
    return dict(status="passed",actual_owners=2,native_grant_clear_trials=4,native_reset_requests=8,
        authority_avatar_callbacks=8,owner_avatar_callbacks=8,native_removal_callbacks=8,replicated_viewer_waves=16,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True);args=parser.parse_args();root=Path(args.directory)
    read=lambda peer:json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
    print(json.dumps(validate(read("server"),{peer:read(peer) for peer in PEERS})))
