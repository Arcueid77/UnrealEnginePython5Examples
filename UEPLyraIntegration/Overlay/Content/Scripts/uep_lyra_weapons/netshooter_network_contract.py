"""Native two-owner prediction and moving projectile replication, before impact."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.network_identity import same,key
from .weapon_ability_fire_network_contract import PEERS,PLAN,FALSE,accept_command
from .weapon_actor_helpers_contract import require


def common(report,mode):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]==mode and report["network_acceptance"],"native NetShooter network peer failed")
    for field in FALSE+("projectile_spawn_requested_by_fixture","impact_or_strand_replication_accepted","projectile_physics_written"):
        require(report[field] is False,"NetShooter network scope overclaim: "+field)
    require(report["observation_errors"]==[] and report["observers_restored"] and report["original_inventory_restored"] and len(report["cases"])==len(PLAN),"NetShooter native observation/inventory/matrix missing")


def moving(row,authority):
    require(key(row["projectile_identity"]) is not None and row["projectile_identity"]["local_role"]==(3 if authority else 1),"native projectile role/identity missing")
    require(row["projectile_replicates"] and row["projectile_replicates_movement"] and row["native_moving_samples"]>=3 and row["distance_moved"]>=100.,"actual native projectile movement/replication missing")
    require(row["natural_hit_entries"]==0 and row["projectile_destruction_observed"] and row["human_health_unchanged"],"pre-impact projectile boundary/destruction/Health differs")


def validate(server,clients):
    common(server,"DedicatedServer");require(set(clients)==set(PEERS),"two actual NetShooter clients required")
    require(server["server_waited_for_client_process_exit"] and len(set(server["player_ids"].values()))==2 and server["original_native_pose_movement_restored"],"native NetShooter authority exit/owner/pose proof missing")
    for peer,report in clients.items():
        common(report,"Client");require(report["player_id"]==server["player_ids"][peer] and report["control_rotation_restored"],"native NetShooter client ownership/control restore missing")
    require(len({key(row["projectile_identity"]) for row in server["cases"]})==len(PLAN),"four distinct native authority projectile identities required")
    for position,(owner,profile) in enumerate(PLAN):
        row=server["cases"][position];moving(row,True)
        require((row["position"],row["owner"],row["profile"])==(position,owner,profile),"native authority NetShooter matrix differs")
        require(row["ammo_before"]-row["ammo_after"]==1 and row["ability_ended"] and len(row["activations"])==len(row["target_data"])==1,"native NetShooter authority cost/activation/target/end missing")
        activation=row["activations"][0];data=row["target_data"][0]
        require(activation["profile"]==profile and activation["authority"] and activation["mode"]==0 and not activation["locally_controlled"] and activation["native_spawn_delta"]==1 and activation["prediction_key"]>0,"native client-owned authority activation/spawn missing")
        require(data["prediction_key"]==activation["prediction_key"] and data["authority"] and row["parent_target_data_calls"]==0,"native NetShooter empty target-data RPC differs")
        require(row["authority_fixture_cleanup"] and row["native_aim_sync"],"native pre-impact authority cleanup/control sync missing")
        for peer in PEERS:
            replica=clients[peer]["cases"][position];moving(replica,False)
            require((replica["position"],replica["owner"],replica["profile"])==(position,owner,profile) and same(replica["source_identity"],row["source_identity"]) and same(replica["projectile_identity"],row["projectile_identity"]),"native projectile/source wire identity mismatch")
            require(replica["weapon_fire_entries"]==1 and replica["parent_target_data_calls"]==0,"native predicted/remote Cue or empty target body differs")
            if peer==owner:
                require(replica["input_gestures"]==1 and replica["input_released"] and replica["ability_ended"] and len(replica["activations"])==len(replica["target_data"])==1,"native NetShooter owner input/target/end missing")
                request=replica["activations"][0];local=replica["target_data"][0]
                require(request["profile"]==profile and not request["authority"] and request["locally_controlled"] and request["mode"]==2 and request["native_spawn_delta"]==0 and request["prediction_key"]==activation["prediction_key"]==local["prediction_key"],"actual native predicted ownership/key/authority-only spawn differs")
                require(not local["authority"] and local["count"]==data["count"] and replica["ammo_after"]==row["ammo_after"] and replica["ammo_before"]-replica["ammo_after"]==1,"native target RPC count/owner ammo differs")
            else:require(replica["input_gestures"]==0 and replica["activations"]==replica["target_data"]==[] and replica["ammo_before"]==replica["ammo_after"],"foreign client activated or consumed NetShooter ammo")
    return dict(status="passed",native_predicted_owner_inputs=4,native_authority_projectiles=4,native_moving_replica_observations=8,impact_or_strand_replication_accepted=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True);root=Path(parser.parse_args().directory)
    def read(peer):return json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
    print(json.dumps(validate(read("server"),{peer:read(peer) for peer in PEERS})))
