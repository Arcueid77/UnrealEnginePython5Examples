"""Natural impact/multicast/component observation parity; retain source defect."""
import argparse
from collections import Counter
import json
from pathlib import Path
from uep_lyra_abilities.network_identity import key,same
from .weapon_ability_fire_network_contract import PEERS,PLAN,FALSE
from .weapon_actor_helpers_contract import require

MESH="/ShooterCore/Blueprint/SM_XFacingCylinderUnit1.SM_XFacingCylinderUnit1"
MATERIAL="/ShooterCore/Effects/Material/M_Launcher_Inst4.M_Launcher_Inst4"


def component_signature(row):
    return Counter((value["from_native_multicast"],key(value["wire"]) is not None,value["mesh"],value["material"],value["collision"],value["replicated"]) for value in row["components"])


def common(report,mode):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]==mode,"native NetShooter impact peer failed")
    for name in FALSE+("gameplay_projectile_spawn_requested_by_fixture","projectile_physics_written","life_callback_replayed","impact_or_strand_replication_accepted"):
        require(report[name] is False,"NetShooter impact scope overclaim: "+name)
    require(report["original_template_baseline_fixture_actors"]==1 and report["native_seed_set_at_actual_hit"] and report["actor_observers_and_selector_restored"] and report["observers_restored"] and report["original_inventory_restored"],"native source baseline/observer/selector/inventory restore missing")
    require(len(report["cases"])==len(PLAN),"native impact matrix incomplete")


def validate(server,clients):
    common(server,"DedicatedServer");require(set(clients)==set(PEERS),"two actual impact clients required")
    require(server["server_waited_for_client_process_exit"] and server["original_native_pose_movement_restored"] and server["native_fixture_colliders_destroyed"],"native impact authority cleanup incomplete")
    for report in clients.values():common(report,"Client");require(report["control_rotation_restored"],"native impact client control not restored")
    for position,(owner,profile) in enumerate(PLAN):
        authority=server["cases"][position];require((authority["position"],authority["owner"],authority["profile"])==(position,owner,profile),"native impact plan differs")
        require(len(authority["activations"])==len(authority["target_data"])==len(authority["native_hit_events"])==1 and authority["natural_hit_entries"]==1,"natural native authority impact missing")
        hit=authority["native_hit_events"][0];activation=authority["activations"][0]
        require(hit["profile"]==profile and activation["profile"]==profile and activation["authority"] and activation["mode"]==0 and activation["native_spawn_delta"]==1 and activation["prediction_key"]>0,"native authority Profile/prediction/spawn differs")
        require(not authority["authority_fixture_cleanup"] and authority["native_delay_elapsed"]>=11.9 and authority["projectile_destruction_observed"],"original native12s Delay/destruction not observed")
        require(authority["ammo_before"]-authority["ammo_after"]==1 and authority["parent_target_data_calls"]==0 and authority["human_health_unchanged"],"native impact cost/empty child callback/Health differs")
        require(authority["target_data"][0]["authority"] and authority["target_data"][0]["prediction_key"]==activation["prediction_key"],"native impact authority target-data prediction differs")
        events=authority["native_rpc_events"];require(1<=len(events)<=13 and len(authority["components"])==len(events),"native inclusive ray/multicast count differs")
        wire_ids={key(value["wire"]) for value in authority["components"]};require(None not in wire_ids and len(wire_ids)==len(events),"native authority component identities missing")
        for peer in PEERS:
            replica=clients[peer]["cases"][position]
            require((replica["position"],replica["owner"],replica["profile"])==(position,owner,profile) and same(replica["projectile_identity"],authority["projectile_identity"]) and same(replica["source_identity"],authority["source_identity"]),"native projectile/source peer identity differs")
            require(replica["projectile_destruction_observed"] and replica["natural_hit_entries"]==0 and replica["components_stable_ticks"]>=6 and replica["human_health_unchanged"],"native remote authority gate/steady components/destruction/Health differs")
            require(len(replica["native_rpc_events"])==len(events) and {key(value["wire"]) for value in replica["components"] if key(value["wire"]) is not None}==wire_ids,"native multicast/component wire replication differs")
            require(replica["weapon_fire_entries"]==1 and replica["parent_target_data_calls"]==0,"native impact predicted/remote Cue or empty target body differs")
            if peer==owner:
                require(replica["input_gestures"]==1 and replica["input_released"] and len(replica["activations"])==len(replica["target_data"])==1,"native impact owning input/RPC missing")
                request=replica["activations"][0];require(request["mode"]==2 and request["profile"]==profile and request["native_spawn_delta"]==0 and request["prediction_key"]==activation["prediction_key"] and replica["ammo_after"]==authority["ammo_after"],"native impact prediction/key/authority-only spawn/owner ammo differs")
                data=replica["target_data"][0];require(not data["authority"] and data["prediction_key"]==activation["prediction_key"] and data["count"]==authority["target_data"][0]["count"],"native impact owning target-data RPC differs")
            else:require(replica["input_gestures"]==0 and replica["activations"]==replica["target_data"]==[] and replica["ammo_after"]==replica["ammo_before"],"foreign client activated NetShooter")
        for row in [authority]+[clients[peer]["cases"][position] for peer in PEERS]:
            require(all(event["profile"]==profile and same(event["source_identity"],authority["source_identity"]) and event["new_components"]==1 and event["native_geometry_matches"] and event["sphere_hidden"] for event in row["native_rpc_events"]),"actual native multicast source/Profile/strand geometry/hide differs")
            require(all(value["mesh"]==MESH and value["material"]==MATERIAL for value in row["components"] if value["from_native_multicast"]),"original multicast component template differs")
    for first in (0,2):
        require(server["cases"][first]["native_hit_events"][0]["next_native_random"]==server["cases"][first+1]["native_hit_events"][0]["next_native_random"],"natural original/Python native RNG consumption differs")
        for report in [server,*clients.values()]:require(component_signature(report["cases"][first])==component_signature(report["cases"][first+1]),"original/Python component replication baseline differs")
    return dict(status="passed",native_natural_predicted_impacts=4,native_component_state_original_python_parity=True,native_original_delay_destruction_cases=4,full_component_replication_correctness_accepted=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--directory",required=True);root=Path(parser.parse_args().directory)
    def read(peer):return json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig"))
    print(json.dumps(validate(read("server"),{peer:read(peer) for peer in PEERS})))
