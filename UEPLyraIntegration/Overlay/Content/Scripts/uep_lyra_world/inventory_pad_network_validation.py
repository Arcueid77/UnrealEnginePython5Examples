"""Authority-side physical pads; two owning-client native inventories and fire.

No pad replication setting, native inventory property or ammo stat is written.
Server-only spawning/teleports are explicit fixture setup; audio, client pad
profiles, physical client movement and travel/rejoin are not certified here.
"""
import copy
import sys
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_hud import state as hud_state, weapon_observer
from uep_lyra_hud.shutdown_validation import defer_until_shutdown
from uep_lyra_network import NetworkProbe
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_protocol import validate_hud
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_weapon_input import aim_above_players
from . import inventory_pad_mixin as policy
from .inventory_pad_network_state import capture, services, path
from .inventory_pad_network_protocol import PLAN, PEERS, require, validate_ack, validate_cases, baseline_ready


class InventoryNetwork(NetworkProbe):
    def __init__(self):
        super().__init__()
        require(self.peer in ("server",)+PEERS, "wrong inventory peer")
        self.stage, self.timeout_seconds = "ready", 600
        self.scope, self.pad, self.owners = SubscriptionScope(), None, {}
        self.local_inventory = self.original_aim = None
        self.last_ack, self.seen, self.input_frames = -1, -1, 0

    def _status(self):
        result = super()._status()
        result["inventory"] = copy.deepcopy(self.local_inventory)
        if self.peer != "server":
            result["ready"] = result["ready"] and self.local_inventory is not None and self.player["hero_input_ready"]
        return result

    def input(self, pressed):
        controller = ue.find_object(self.player["controller_path"])
        for name in ("IA_Weapon_Fire", "IA_Weapon_Fire_Auto"):
            action = ue.load_object(ue.find_class("InputAction"), "/Game/Input/Actions/"+name+"."+name)
            controller.inject_enhanced_input_for_action(action, pressed)

    def fingerprint(self, controller):
        inventory, quickbar = services(controller)
        return {"items": sorted(path(item) for item in inventory.call_function("GetAllItems")),
            "slots": [path(item) for item in quickbar.call_function("GetSlots")],
            "active": int(quickbar.call_function("GetActiveSlotIndex"))}

    def prepare(self, roster):
        if not self.owners:
            for peer, row in roster.items():
                controller, pawn = ue.find_object(row["controller_path"]), ue.find_object(row["pawn_path"])
                movement = pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
                require(valid(movement) and capture(controller) is not None, "native owner inventory/movement unavailable")
                self.owners[peer] = {"controller": controller, "pawn": pawn, "movement": movement,
                    "location": pawn.get_actor_location(), "mode": int(movement.MovementMode),
                    "custom_mode": int(movement.CustomMovementMode), "fingerprint": self.fingerprint(controller)}
                movement.call_function("StopMovementImmediately")
                movement.call_function("DisableMovement")
            self.definition = ue.load_class("/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C")
        self.roster = copy.deepcopy(roster)
        self.baseline = {peer: capture(owner["controller"]) for peer, owner in self.owners.items()}
        require(all(self.baseline.values()), "native baseline inventory unavailable")
        self.stage = "baseline"

    def begin(self):
        cls_name, kind, target, profile = PLAN[self.index]
        owner = self.owners[target]
        inventory, quickbar = services(owner["controller"])
        require(int(quickbar.call_function("GetNextFreeItemSlot")) >= 0, "baseline inventory has no free slot")
        if kind == "full":
            for slot, item in enumerate(quickbar.call_function("GetSlots")):
                if item is None:
                    quickbar.call_function("AddItemToSlot", slot, inventory.call_function("AddItemDefinition", self.definition, 1))
        self.prepared = capture(owner["controller"])
        self.stats_before, self.physical = policy.snapshot(), []
        cls = ue.load_class(policy.CLASS if cls_name == "B_GrantInventory_Pad_C" else policy.MESH_CLASS)
        origin = owner["location"]
        self.center = ue.FVector(origin.x+6000.0+self.index*900.0, origin.y, origin.z+500.0)
        transform = ue.FTransform()
        transform.translation = self.center
        self.pad = self.gameplay_statics.call_function("BeginDeferredActorSpawnFromClass", self.world, cls, transform, 1, None)
        require(valid(self.pad), "native inventory pad spawn failed")
        ue.set_mixin_profile(self.pad, profile)
        self.pad.set_property("ItemDefinition", self.definition)
        self.pad.set_property("bDestroyOnPickup", False)
        self.gameplay_statics.call_function("FinishSpawningActor", self.pad, transform)
        require(self.pad.get_class() == cls and ue.get_mixin_profile(self.pad) == profile, "inventory pad class/Profile differs")
        self.current = {"run_id": self.run_id, "case_index": self.index, "class": cls_name, "kind": kind,
            "target": target, "profile": profile, "roster": copy.deepcopy(self.roster), "baseline": copy.deepcopy(self.baseline),
            "native_pad_replicates": bool(self.pad.get_property("bReplicates")),
            "client_pawns": {peer: self._peer_status(peer)["player"]["pawn_path"] for peer in PEERS},
            "client_worlds": {peer: self._peer_status(peer)["player"]["world_token"] for peer in PEERS}}
        self.scope = SubscriptionScope()
        self.scope.bind_event(self.pad.Volume, "OnComponentBeginOverlap", lambda component, actor, *rest:
                              self.physical.append("begin") if actor == owner["pawn"] else None)
        self.scope.bind_event(self.pad.Volume, "OnComponentEndOverlap", lambda component, actor, *rest:
                              self.physical.append("end") if actor == owner["pawn"] else None)
        require(owner["pawn"].set_actor_location(self.pad.Volume.call_function("K2_GetComponentLocation")), "native server Pawn relocation rejected")
        self.stage, self.stage_started = "overlap", time.monotonic()

    def rollback(self):
        for owner in self.owners.values():
            controller = owner["controller"]
            inventory, quickbar = services(controller)
            original = owner["fingerprint"]
            for slot, item in enumerate(quickbar.call_function("GetSlots")):
                if valid(item) and path(item) not in original["items"]:
                    quickbar.call_function("RemoveItemFromSlot", slot)
            for item in inventory.call_function("GetAllItems"):
                if path(item) not in original["items"]:
                    inventory.call_function("RemoveItemInstance", item)
            if int(quickbar.call_function("GetActiveSlotIndex")) != original["active"]:
                quickbar.call_function("SetActiveSlotIndex", original["active"])
            require(self.fingerprint(controller) == original, "native rollback changed original item identity")

    def server_tick(self):
        if self.stage == "release":
            release = read_json(self.root/"release.json")
            if release is not None:
                require(release["run_id"] == self.run_id, "foreign inventory release")
                self.finish()
            return
        if self.stage == "ready":
            roster = self._roster(PEERS)
            if roster is not None:
                self.prepare(roster)
            return
        if self.stage == "baseline":
            if baseline_ready({peer: self._peer_status(peer) for peer in PEERS}, self.baseline):
                self.begin()
        elif self.stage == "overlap" and time.monotonic()-self.stage_started > .25:
            expected = {peer: capture(owner["controller"]) for peer, owner in self.owners.items()}
            if not all(expected.values()):
                return
            target = self.current["target"]
            delta = len(expected[target]["items"])-len(self.prepared["items"])
            require(delta == (1 if self.current["kind"] == "pickup" else 0), "native physical pickup count differs")
            if self.current["kind"] == "full":
                require(expected[target] == self.prepared, "native full inventory changed")
            self.current["expected"] = expected
            atomic_write(self.root/"inventory-command.json", dict(self.current, stage="observe"))
            self.stage = "ack"
        elif self.stage == "ack":
            acks = {peer: read_json(self.root/"inventory-acks"/(str(self.index)+"-"+peer+".json")) for peer in PEERS}
            if not all(acks.values()):
                return
            after = {peer: capture(owner["controller"]) for peer, owner in self.owners.items()}
            if not all(after[peer] == acks[peer]["inventory"] for peer in PEERS):
                return  # Client prediction is not authoritative inventory proof.
            for peer in PEERS:
                validate_ack(self.current, acks[peer], peer)
            self.current.update(acks=acks, after=after)
            owner = self.owners[self.current["target"]]
            require(owner["pawn"].set_actor_location(ue.FVector(self.center.x+500.0, self.center.y, self.center.z)), "native leave rejected")
            require(self.physical == ["begin", "end"], "native inventory overlap events missing/duplicated")
            self.scope.close()
            self.pad.actor_destroy()
            self.current.update(physical_events=list(self.physical), pad_destroyed=not valid(self.pad), fixture_scope_closed=self.scope.closed,
                python_grants=policy.snapshot()["authority_grants"]-self.stats_before["authority_grants"],
                python_full_rejections=policy.snapshot()["full_slots"]-self.stats_before["full_slots"])
            self.pad = None
            self.rollback()
            atomic_write(self.root/"inventory-command.json", dict(self.current, stage="rollback"))
            self.stage = "rollback"
        elif self.stage == "rollback":
            replies = {peer: read_json(self.root/"inventory-rollbacks"/(str(self.index)+"-"+peer+".json")) for peer in PEERS}
            if not all(replies.values()):
                return
            require(all(replies[peer]["inventory"] == self.baseline[peer] for peer in PEERS), "client inventory rollback differs")
            self.current["rollbacks"] = replies
            self.history.append(copy.deepcopy(self.current))
            ue.log("UEP_INVENTORY_NETWORK_CASE_PASSED "+str(self.index))
            self.index += 1
            self.phase_started = time.monotonic()
            if self.index == len(PLAN):
                validate_cases(self.history)
                self.restore()
                self.stage = "release"
                atomic_write(self.root/"ready-server.json", {"run_id": self.run_id})
            else:
                self.stage = "ready"

    def client_tick(self):
        packet = read_json(self.root/"inventory-command.json")
        if packet is None or packet["case_index"] <= self.last_ack or self.local_inventory is None:
            return
        require(packet["run_id"] == self.run_id, "foreign inventory command")
        index = packet["case_index"]
        if self.seen != index:
            self.seen, self.input_frames, self.fire_started = index, 0, time.monotonic()
        if packet["stage"] == "observe":
            target = packet["kind"] == "pickup" and packet["target"] == self.peer
            expected = copy.deepcopy(packet["expected"][self.peer])
            if target:
                expected["magazine"] -= 1
            if self.local_inventory != expected:
                if target and self.local_inventory == packet["expected"][self.peer]:
                    require(self.player["hero_input_ready"], "native hero input not ready")
                    require(time.monotonic()-self.fire_started < 20, "replicated new pistol did not fire")
                    aim_above_players(ue.find_object(self.player["controller_path"]))
                    self.input((time.monotonic()-self.fire_started) % .30 < .12)
                    self.input_frames += 1
                return
            self.input(False)
            ack = {"run_id": self.run_id, "peer": self.peer, "case_index": index,
                "player": copy.deepcopy(self.player), "inventory": copy.deepcopy(self.local_inventory), "input_frames": self.input_frames}
            validate_ack(packet, ack, self.peer)
            atomic_write(self.root/"inventory-acks"/(str(index)+"-"+self.peer+".json"), ack)
            self.pending_ack = ack
        elif packet["stage"] == "rollback" and self.local_inventory == packet["baseline"][self.peer]:
            self.input(False)
            reply = {"run_id": self.run_id, "peer": self.peer, "case_index": index, "inventory": copy.deepcopy(self.local_inventory)}
            atomic_write(self.root/"inventory-rollbacks"/(str(index)+"-"+self.peer+".json"), reply)
            self.history.append(self.pending_ack)
            self.last_ack = index
            if self.last_ack == len(PLAN)-1:
                atomic_write(self.root/("ready-"+self.peer+".json"), {"run_id": self.run_id})

    def restore(self):
        self.scope.close()
        if valid(self.pad):
            self.pad.actor_destroy()
            self.pad = None
        self.restored_players = getattr(self, "restored_players", {})
        if self.owners:
            self.rollback()
        for peer, owner in self.owners.items():
            pawn, movement = owner["pawn"], owner["movement"]
            require(pawn.set_actor_location(owner["location"]), "native player restore location rejected")
            movement.call_function("StopMovementImmediately")
            movement.call_function("SetMovementMode", owner["mode"], owner["custom_mode"])
            actual = pawn.get_actor_location()
            restored = (max(abs(getattr(actual, key)-getattr(owner["location"], key)) for key in ("x", "y", "z")) < .01 and
                int(movement.MovementMode) == owner["mode"] and int(movement.CustomMovementMode) == owner["custom_mode"])
            require(restored, "native server player position/movement not restored")
            self.restored_players[peer] = restored
        self.owners.clear()

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        aim_restored = self.peer == "server"
        try:
            self.restore()
            if self.peer != "server" and self.original_aim is not None:
                self.input(False)
                controller = ue.find_object(self.player["controller_path"])
                controller.call_function("SetControlRotation", self.original_aim)
                actual = controller.call_function("GetControlRotation")
                aim_restored = max(abs(getattr(actual, key)-getattr(self.original_aim, key)) for key in ("pitch", "yaw", "roll")) < .01
                require(aim_restored, "native client aim not restored")
        except Exception:
            error = (error or "")+traceback.format_exc()
        report = {"schema_version": 1, "status": "failed" if error else "passed", "error": error,
            "run_id": self.run_id, "peer": self.peer, "cases": self.history,
            "fixture_scope_closed": self.scope.closed, "native_players_restored": getattr(self, "restored_players", {}),
            "client_aim_restored": aim_restored, "hud": hud_state.snapshot(), "weapon_observer": weapon_observer.snapshot(),
            "gameplay_slice": {"enabled": False}, "shutdown": None, "elapsed_seconds": self._wall_elapsed(),
            "inventory_policy": policy.snapshot(), "fixture_server_spawn_and_teleport": True}
        for flag in ("full_acceptance", "packaged_runtime", "remote_audio_tested", "client_pad_profile_parity_tested",
                     "overlap_handler_called_by_probe", "ammo_properties_written", "inventory_properties_written",
                     "pad_replication_forced", "physical_client_input_tested", "travel_rejoin_tested"):
            report[flag] = False
        if error is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        (ue.log_error if error else ue.log)("UEP_INVENTORY_NETWORK_"+("FAILED "+error if error else "PASSED"))
        self.shutdown_binding()
        self._request_quit()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            now = time.monotonic()
            require(self._wall_elapsed() < self.timeout_seconds, "inventory network total timeout")
            if now < self.next_tick:
                return True
            self.next_tick = now+.05
            world = self._game_world()
            if not valid(world) or not self._attach(world):
                return True
            self.peer_frame_snapshots.clear()
            self.rows = [self._snapshot_report(row) for row in self.bridge.call_function("CapturePlayerSnapshots")]
            self.player = self.rows[0] if self.peer != "server" and len(self.rows) == 1 else None
            if self.peer == "server":
                self._isolate_bot_combat()
            elif self.player is not None:
                controller = ue.find_object(self.player["controller_path"])
                self.local_inventory = capture(controller)
                if self.original_aim is None and self.local_inventory is not None:
                    self.original_aim = controller.call_function("GetControlRotation")
            atomic_write(self.root/"status"/(self.peer+".json"), self._status())
            if self.peer == "server":
                limit = 300 if not self.owners and self.index == 0 else 120
                require(now-self.phase_started < limit, "inventory case timeout: "+str(self.index)+"/"+self.stage)
                self.server_tick()
            else:
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run_id and len(self.history) == len(PLAN), "premature inventory release")
                    self.finish()
                else:
                    self.client_tick()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False


if "-UEPInventoryPadNetwork" in sys.argv:
    runtime = InventoryNetwork()
    ticker = ue.add_ticker(runtime.tick)
