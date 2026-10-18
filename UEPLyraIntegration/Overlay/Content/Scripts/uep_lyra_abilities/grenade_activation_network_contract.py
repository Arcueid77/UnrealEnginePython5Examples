"""Independent two-owner prediction/native RPC/authority-only-spawn report gate."""
import argparse
import json
import math
from pathlib import Path
from .grenade_activation_contract import CLASS,PROJECTILE,require,expected,close
from .network_identity import key,same

PEERS=("A","B0")
PLAN=tuple((peer,profile) for peer in PEERS for profile in ("BlueprintFallback","Python"))
FALSE=("full_acceptance","packaged_runtime","physical_input_tested","packet_loss_tested","travel_rejoin_tested","health_properties_written",
    "inventory_properties_written","ability_spec_properties_written","activation_event_replayed","task_callbacks_replayed","ability_granted_by_fixture",
    "native_rpc_bypassed","gameplay_state_delivered_by_files","projectile_replication_tested","projectile_actor_business_migrated","explosion_damage_tested","denied_body_native_tested","far_field_teleports")


def accept_command(command,processed,completed_position):
    position,stage=command["position"],command["stage"]
    require(type(position) is int and stage in ("prepare","activate","complete") and
        (position==len(PLAN) if stage=="complete" else 0<=position<len(PLAN)),"invalid bounded Grenade coordination command")
    return (position,stage)!=processed and (position>completed_position or stage=="complete")


def common(report,mode):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]==mode,"native predicted Grenade report failed")
    require(report["network_acceptance"] is True and report["observation_errors"]==[],"native prediction/observer evidence missing")
    for field in FALSE: require(report[field] is False,"Grenade network scope overclaim: "+field)
    for field in ("listener_closed","observers_restored"): require(report[field] is True,"native network observer cleanup missing: "+field)
    require(report["remaining_test_projectiles"]==0 and len(report["cases"])==len(PLAN),"Grenade native projectile/matrix incomplete")


def event(row,profile,authority):
    require(row["profile"]==profile and row["native_callback_count"]==1 and row["native_role"]==(3 if authority else 2) and row["native_authority"] is authority,"native Grenade activation identity/authority differs")
    for field in ("native_cost_ready","native_cooldown_ready","montage_continues_after_end"): require(row[field] is True,"native Grenade activation witness missing: "+field)
    require(row["active_after"] is False and row["tasks_after"]==0,"network Grenade End/task timing differs")
    point,direction=expected(row);close(row["location"],point);close(row["direction"],direction)
    require(row["before"]["activation_mode"]==(0 if authority else 2),"actual native authority/predicting activation mode missing")
    require(math.isfinite(row["cooldown"]) and row["cooldown"]>0 and math.isfinite(row["native_cooldown"]) and row["native_cooldown"]>=(0. if not authority else .000001),"native predicted cooldown missing")
    require(row["cooldown"]==(row["native_cooldown"] if authority else row["cooldown_before"]),"authority-only cooldown property write differs")
    require(len(row["messages"])==1,"one actual typed local duration message required,not replicated file delivery")
    message=row["messages"][0]
    require(message["channel"]=="Ability.Grenade.Duration.Message" and message["instigator"]==row["pawn"] and message["duration"]==row["cooldown"] and
        message["native_active"] is True and message["native_montage_task_count"]==1,"native typed message/montage/End order differs")
    require(len(row["projectiles"])==(1 if authority else 0),"only the real authority may spawn the native projectile")
    if authority:
        actor=row["projectiles"][0]
        require(actor["class"]==PROJECTILE and actor["instigator"]==row["pawn"] and actor["owner"] is None,"authority actual projectile identity differs")
        close(actor["location"],point);close(actor["rotation"],direction);close(actor["scale"],[1.,1.,1.])
    else:
        require(row["native_request_accepted"] is True and row["native_repeat_rejected"] is True,"native predicted ASC request/guard missing")
        require(math.isfinite(row["native_confirmed_cooldown_before_repeat"]) and row["native_confirmed_cooldown_before_repeat"]>0.,"native repeat guard must wait for actual replicated cooldown")
    py=profile=="Python";trace=row["before"]["trace"]
    require(type(trace["hit"]) is bool and math.isfinite(trace["distance"]) and trace["distance"]>=0.,"invalid native aim trace")
    wanted=dict(python_calls=int(py),fallback_calls=int(not py),cost_checks=int(py),cooldown_checks=int(py),commits=int(py),denied=0,aim_queries=int(py),
        near_control_rotation=int(py and trace["distance"]<45.),hit_aim=int(py and trace["distance"]>=45. and trace["hit"]),miss_aim=int(py and trace["distance"]>=45. and not trace["hit"]),
        projectiles=int(py and authority),cooldown_writes=int(py and authority),montage_tasks=int(py),duration_messages=int(py),native_ends=int(py),invalid_receiver_defaults=0)
    require(row["stats"]==wanted,"actual selected native network Grenade handler counts differ")
    require(key(row["source_identity"]) is not None and row["source_identity"]["local_role"]==row["native_role"],"native activation wire identity missing")


def source(row,identity,own):
    role=2 if own else 1
    require(row["healthy_bound"] is True and row["source_role"]==role and row["network_identity"]["local_role"]==role and same(row["network_identity"],identity),"viewer inspected a different native Pawn or wrong role")
    binding=row["binding"]
    require(binding["role"]==role and binding["health"]==100. and binding["death_state"]==0 and binding["destroying"] is False and binding["health_set"] is not None and
        binding["actor"]==binding["player_state_pawn"] and binding["actor_asc"] is not None and binding["actor_asc"]["avatar"]==binding["actor"] and
        binding["health_asc"] is not None and binding["health_asc"]["object"]==binding["actor_asc"]["object"] and same(binding["network_identity"],identity),"viewer canonical Pawn is not actually healthy/ASC-bound")


def client(report):
    common(report,"Client");require(report["peer"] in PEERS and report["native_role"]==2 and report["native_class"]==CLASS,"real owning native client required")
    for field in ("profile_restored","specs_preserved","handles_preserved","config_preserved","ui_preserved"): require(report[field] is True,"native owner cleanup missing: "+field)
    require(len(report["original_handles"])==1,"one original owner Grenade handle required")
    for position,(row,(owner,profile)) in enumerate(zip(report["cases"],PLAN)):
        own=owner==report["peer"]
        require((row["position"],row["owner"],row["profile"],row["own"])==(position,owner,profile,own) and row["quiet_ticks"]>=20,"native client matrix/quiet interval differs")
        for field in ("ui_preserved","specs_preserved","handles_preserved","all_pawn_health_unchanged","native_montage_completed"): require(row[field] is True,"native owner/foreign state changed: "+field)
        require(row["foreign_owner_untouched"] is (not own),"native foreign-owner control missing")
        if own: event(row["activation"],profile,False)
        else: require(row["activation"] is None,"foreign local ability must not activate")
    return dict(status="passed",native_owner_trials=2,foreign_trials=2)


def validate(server,viewers):
    common(server,"DedicatedServer");require(set(viewers)==set(PEERS) and server["server_waited_for_client_process_exit"] is True,"real two-owner server-last exit proof missing")
    require(server["native_class"]==CLASS,"actual authority Grenade class not preserved")
    require(set(server["player_ids"])==set(PEERS) and len(set(server["player_ids"].values()))==2,"two distinct actual players required")
    cleanup=server["native_pre_release_cleanup"];require(set(cleanup)==set(PEERS),"live authority cleanup snapshot missing")
    for row in cleanup.values():
        for field in ("native_asc_alive","profile_restored","specs_preserved","handles_preserved","config_preserved"): require(row[field] is True,"authority live-before-release restoration missing: "+field)
        require(len(row["original_handles"])==1 and row["current_handles"]==row["original_handles"],"persistent authority Grenade handle changed")
    for peer,value in viewers.items():
        client(value);require(value["run_id"]==server["run_id"] and value["peer"]==peer and value["player_id"]==server["player_ids"][peer],"native player/run association differs")
    identities=[]
    for position,(row,(owner,profile)) in enumerate(zip(server["cases"],PLAN)):
        require((row["position"],row["owner"],row["profile"])==(position,owner,profile) and row["native_reset_requests"]==1 and row["quiet_ticks"]>=20 and row["all_pawn_health_unchanged"] is True,"native authority matrix/reset/quiet witness missing")
        require(row["native_nonlocal_owner"] is True and row["native_ui_invalid"] is True,"dedicated authority must not register local UI")
        identity=row["source_identity"];require(key(identity) is not None and identity["local_role"]==3 and not same(identity,row["old_identity"]),"real mapped native Reset/Pawn replacement missing")
        require(key(identity) not in identities,"native trials reused one Pawn despite Reset");identities.append(key(identity))
        event(row["activation"],profile,True);require(same(identity,row["activation"]["source_identity"]),"authority activation used another Pawn")
        for peer in PEERS:
            own=peer==owner;prepared=row["prepared"][peer];observed=row["viewers"][peer]
            require(prepared["own"] is own and observed==viewers[peer]["cases"][position],"native acknowledgement/report differs")
            source(prepared,identity,own);source(observed["source"],identity,own)
            if own: require(same(observed["activation"]["source_identity"],identity),"prediction and authority used different native Pawn ids")
    return dict(status="passed",actual_owners=2,native_predicted_requests=4,native_authority_activations=4,authority_only_projectiles=4,
        actual_native_resets=4,wire_matched_owner_foreign_views=8,projectile_replication_tested=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True);args=parser.parse_args();root=Path(args.directory)
    read=lambda peer:json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
    print(json.dumps(validate(read("server"),{peer:read(peer) for peer in PEERS})))
