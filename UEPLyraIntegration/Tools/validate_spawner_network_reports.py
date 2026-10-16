"""Validate final original-level-spawner native reports; never starts Unreal."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_world.spawner_network_protocol import PLAN,PEERS,require,validate_ack,validate_cases

root=Path(sys.argv[1])
reports={peer:json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS}
run_id=reports["server"]["run_id"]
for peer,row in reports.items():
    require(row["run_id"]==run_id and row["peer"]==peer and row["status"]=="passed" and row["error"] is None,"spawner native peer failed")
    require(len(row["cases"])==len(PLAN) and row["players_restored"] is True and row["policy"]["errors"]==[],"spawner cases/player/policy incomplete")
    require(row["original_level_actors_used"] is True and row["fixture_actors_created"]==row["fixture_actors_destroyed"]==0,"spawner original level actors replaced/destroyed")
    require(row["shutdown"]["status"]=="passed" and row["shutdown"]["hud"]["active_widget_count"]==0 and
            row["shutdown"]["weapon_observer"]["active_scopes"]==0 and not row["shutdown"]["weapon_observer"]["ticker_active"],"spawner native HUD/observer shutdown leak")
    for flag in ("full_acceptance","packaged_runtime","handler_called_by_probe","launch_called_by_probe","give_weapon_called_by_probe",
                 "timer_or_timeline_driven_by_probe","cooldown_duration_overridden","pad_replication_forced","ammo_properties_written",
                 "inventory_properties_written","health_properties_written","physical_client_input_tested","construction_profile_parity_tested",
                 "cue_audio_visual_parity_tested","culture_switch_tested"):
        require(row[flag] is False,"unsupported spawner network claim: "+flag)
server=reports["server"]
require(server["scopes_created"]==server["scopes_closed"]==len(PLAN) and server["native_players_restored"]=={peer:True for peer in PEERS},
        "spawner server collision/player cleanup incomplete")
validate_cases(server["cases"])
for peer in PEERS:
    for packet,ack in zip(server["cases"],reports[peer]["cases"]):validate_ack(packet,ack,peer,"restored")
print(json.dumps({"status":"passed","cases":len(PLAN),"clients":2,"run_id":run_id,
    "native_spawner_level_actor_inventory_health_cooldown_replication":True,"full_acceptance":False}))
