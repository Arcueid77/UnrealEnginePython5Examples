"""Real level spawners, two owners, nine BP/Python scenario pairs per owner."""
import copy
import math
from .spawner_contract import CASES

PEERS=("A","B0")
PLAN=tuple((target,name,profile) for target in PEERS for name in CASES for profile in ("BlueprintFallback","Python"))

def require(value,message):
    if not value:raise RuntimeError(message)

def near(a,b):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b)<.01

def expected_inventory(packet,peer):
    value=copy.deepcopy(packet["expected"][peer])
    if peer==packet["target"] and packet["scenario"]==CASES[0]:value["magazine"]-=1
    return value

def validate_ack(packet,ack,peer,stage):
    require(ack["run_id"]==packet["run_id"] and ack["case_index"]==packet["case_index"] and ack["peer"]==peer and ack["stage"]==stage,
            "wrong spawner network ACK")
    player=ack["player"]
    require(player["player_id"]==packet["roster"][peer]["player_id"] and player["pawn_path"]==packet["client_pawns"][peer] and
            player["world_token"]==packet["client_worlds"][peer],"spawner ACK crossed owner/Pawn/world")
    state=packet["prepared"] if stage=="prepared" else packet["original"] if stage=="restored" else None
    inventory=state[peer] if state is not None else expected_inventory(packet,peer)
    require(ack["inventory"]==inventory,"spawner native inventory/equipment/ammo did not replicate")
    health=packet["prepared_health"] if stage=="prepared" else packet["original_health"] if stage=="restored" else packet["expected_health"]
    require(near(player["health"],health[peer]),"spawner native owner Health differs")
    visual=ack["health_visual"]
    require(near(visual["number"],health[peer]) and near(visual["target"],health[peer]) and
            near(visual["ratio"],health[peer]/player["max_health"]),"spawner native owner Health HUD differs")
    desired_available=not packet["success"] if stage=="observed" else True
    require(ack["pad"]["name"]==packet["pad_name"] and ack["pad"]["class"]==packet["pad_class"] and
            ack["pad"]["profile"]==packet["profile"] and ack["pad"]["available"] is desired_available and
            ack["pad"]["light"] is desired_available and ack["pad"]["weapon_visible"] is desired_available,
            "spawner native level actor/Profile/availability FX differs")
    if stage=="observed":
        fire=peer==packet["target"] and packet["scenario"]==CASES[0]
        require((ack["input_frames"]>0) is fire,"spawner wrong owner/native fire input")
        failure=peer==packet["target"] and packet["scenario"]==CASES[3]
        require(ack["failure_delta"]==int(failure),"spawner failure message crossed owner or replayed")
        if failure:require(ack["failure_text"]=="Spare Ammo Full","spawner native failure FText differs")

def baseline_ready(statuses,inventory,health):
    return all(isinstance(statuses.get(peer),dict) and statuses[peer].get("inventory")==inventory[peer] and
        statuses[peer].get("health_visual") is not None and near(statuses[peer]["player"]["health"],health[peer]) for peer in PEERS)

def validate_cases(cases):
    require(len(cases)==len(PLAN),"spawner network matrix incomplete")
    for index,(row,identity) in enumerate(zip(cases,PLAN)):
        target,name,profile=identity
        require(row["case_index"]==index and (row["target"],row["scenario"],row["profile"])==identity,"spawner case order differs")
        require(row["physical_events"]==["begin","end"] and row["fixture_scope_closed"] is True and
                row["original_level_actor_preserved"] is True and row["pad_replicates"] is True and
                row["cooldown_duration"]==10.0,"spawner native collision/type/data/lifetime missing")
        other=next(peer for peer in PEERS if peer!=target)
        require(row["after"][other]==row["original"][other] and near(row["expected_health"][other],row["original_health"][other]),
                "spawner changed other owner's inventory/Health")
        require(len(row["expected"][target]["items"])-len(row["prepared"][target]["items"])==int(name in (CASES[0],CASES[4],CASES[5],CASES[6])),
                "spawner authority grant/rejection differs")
        require(row["success"] is (name not in (CASES[1],CASES[3],CASES[8])),"spawner success/rejection differs")
        if name==CASES[2]:require(row["expected"][target]["spare"]-row["prepared"][target]["spare"]==5,"spawner native refill missing")
        if name==CASES[7]:require(near(row["expected_health"][target],100.0),"spawner native heal missing")
        if row["success"]:require(9.8<=row["cooldown_seconds"]<=11.0,"spawner native default cooldown shortened/late")
        for stage in ("prepared","observed","restored"):
            require(set(row["acks"][stage])==set(PEERS),"spawner peer ACK missing")
            for peer in PEERS:validate_ack(row,row["acks"][stage][peer],peer,stage)
        for peer in PEERS:require(row["after"][peer]==row["acks"]["observed"][peer]["inventory"],"spawner client prediction not confirmed by authority")
        if profile=="Python":
            previous=cases[index-1]
            require(row["expected"]==previous["expected"] and row["after"]==previous["after"] and row["expected_health"]==previous["expected_health"],
                    "spawner BP/Python network result differs")
            require(row["python_gives"]==1 and row["python_failures"]==int(name==CASES[3]),"Python spawner business bypassed/replayed")
        else:require(row["fallback_gives"]==1,"original BP spawner producer bypassed/replayed")
    return True
