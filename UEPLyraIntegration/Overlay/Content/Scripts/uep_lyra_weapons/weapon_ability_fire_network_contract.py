"""Real predicted firing: native identity, target data, damage and owner ammo."""
import argparse
from pathlib import Path
import json
from uep_lyra_abilities.network_identity import same,key
from .weapon_actor_helpers_contract import require
from .weapon_ability_fire_contract import WEAPONS

PEERS=("A","B0")
PLAN=tuple((owner,profile) for owner in PEERS for profile in ("BlueprintFallback","Python"))
FALSE=("full_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested","packet_loss_tested","travel_rejoin_tested",
       "health_properties_written","ammo_properties_written","timer_properties_written","asc_binding_repaired","activation_handler_replayed",
       "target_data_callback_replayed","rpc_function_overridden","gameplay_state_delivered_by_files","client_inventory_written","authority_activation_requested_by_fixture")


def accept_command(command,completed,processed):
    position,stage=command["position"],command["stage"]
    require(type(position) is int and stage in ("prepare","fire","collect","complete"),"invalid network firing scheduling command")
    require(position==len(PLAN) if stage=="complete" else 0<=position<len(PLAN),"network firing position outside plan")
    attempt=command.get("attempt",0);require(type(attempt) is int and 0<=attempt<24,"invalid native target-pose attempt")
    previous=(*processed,0) if processed is not None and len(processed)==2 else processed
    return (position,stage,attempt)!=previous and (position>completed or stage=="complete")


def common(report,mode):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]==mode and report["network_acceptance"],"native firing peer failed")
    for field in FALSE:require(report[field] is False,"network firing scope overclaim: "+field)
    require(report["observation_errors"]==[] and report["observers_restored"] and len(report["cases"])==len(PLAN),"native firing observation/cleanup/matrix incomplete")


def near_vectors(left,right,tolerance=.51):
    return len(left)==len(right)==3 and all(abs(a-b)<=tolerance for a,b in zip(left,right))


def same_hits(left,right):
    if left["hit_identities"]==right["hit_identities"] and all(value is not None for value in left["hit_identities"]):return True
    a,b=left.get("hit_identity_details",[]),right.get("hit_identity_details",[])
    if len(a)!=left["count"] or len(b)!=right["count"] or len(a)!=len(b):return False
    for first,second in zip(a,b):
        if first["wire"] is not None and second["wire"] is not None:
            if first["wire"]!=second["wire"]:return False
        elif first["replicated"] or second["replicated"] or not first["static_guid"] or first["static_guid"]!=second["static_guid"]:return False
    return True


def validate(server,clients):
    common(server,"DedicatedServer");require(set(clients)==set(PEERS),"two real firing clients required")
    require(server["server_waited_for_client_process_exit"] and len(set(server["player_ids"].values()))==2 and server["original_inventory_restored"],"authority firing exit/owner/inventory proof missing")
    for peer,report in clients.items():
        common(report,"Client");require(report["player_id"]==server["player_ids"][peer] and report["control_rotation_restored"] and report["original_inventory_restored"],"client owner/inventory/control restore missing")
    for position,(owner,profile) in enumerate(PLAN):
        authority=server["cases"][position]
        require((authority["position"],authority["owner"],authority["profile"])==(position,owner,profile),"authority firing plan differs")
        require(authority["native_class"]==WEAPONS[server["weapon"]] and authority["ammo_before"]-authority["ammo_after"]==1,"authority class/native cost differs")
        require(authority["health_after"]<authority["health_before"] and authority["health_after"]>=0.,"authority native damage not observed")
        require(len(authority["activations"])==len(authority["target_data"])==1 and authority["ability_ended"],"authority firing activation/target callback/end missing")
        activation=authority["activations"][0];data=authority["target_data"][0]
        require(activation["authority"] and activation["mode"]==0 and not activation["locally_controlled"] and activation["source"]["local_role"]==3,"server bypassed client-owned targeting request")
        require(data["authority"] and data["target_hits"]>=1 and data["count"]>=1 and key(data["source"])==key(authority["source_identity"]),"authority replicated target data invalid")
        require(activation["prediction_key"]>0 and data["prediction_key"]==activation["prediction_key"],"authority native prediction key missing")
        for peer in PEERS:
            row=clients[peer]["cases"][position]
            require((row["position"],row["owner"],row["profile"])==(position,owner,profile),"client firing plan differs")
            require(same(row["source_identity"],authority["source_identity"]) and same(row["target_identity"],authority["target_identity"]),"native source/target wire identity mismatch")
            require(row["health_after"]==authority["health_after"] and row["human_health_unchanged"] and row["quiet_ticks"]>=6,"native damage replication/convergence incomplete")
            require(row["weapon_fire_entries"]==1,"native predicted or remote GameplayCue to Weapon Actor dispatch differs")
            if peer==owner:
                require(row["input_gestures"]==1 and row["input_released"] and len(row["activations"])==len(row["target_data"])==1 and row["ability_ended"],"owning native input/target/end missing")
                request=row["activations"][0];local=row["target_data"][0]
                require(not request["authority"] and request["mode"]==2 and request["locally_controlled"] and request["source"]["local_role"]==2,"owning activation was not real native prediction")
                require(request["prediction_key"]==activation["prediction_key"] and local["prediction_key"]==data["prediction_key"] and not local["authority"],"native predicted key/authority ownership differs")
                require(row["ammo_after"]==authority["ammo_after"] and row["ammo_before"]-row["ammo_after"]==1,"native owner ammo replication differs")
                require(local["count"]==data["count"] and same_hits(local,data) and len(local["points"])==len(data["points"]) and all(near_vectors(a,b) for a,b in zip(local["points"],data["points"])),"native target-data RPC identity/ImpactPoint payload differs")
            else:
                require(row["input_gestures"]==0 and row["activations"]==row["target_data"]==[],"foreign client executed owning firing ability")
        require(all(value==100. for value in authority["human_health_after"].values()),"network firing damaged an unrelated human owner")
    return dict(status="passed",weapon=server["weapon"],native_owner_input_shots=4,native_prediction_key_pairs=4,native_damage_replica_observations=8,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True);args=parser.parse_args();root=Path(args.directory)
    def read(peer):return json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
    print(json.dumps(validate(read("server"),{peer:read(peer) for peer in PEERS})))
