"""Two real owners request the original equipped heal ability through native GAS.

Filesystem commands schedule the test; they do not emulate network replication,
activate a Python handler, invoke task delegates, or write Health attributes.
Server inventory grants, Health setup, stopped movement and aimed cameras are
explicit fixture operations. Hardware input, prediction under packet loss,
FiringRange placement and travel/rejoin remain separate gates.
"""
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_hud import state as hud_state, weapon_observer
from uep_lyra_hud.shutdown_validation import defer_until_shutdown
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_weapon_input import aim_above_players
from .inventory_pad_network_validation import InventoryNetwork
from .effect_pad_network_validation import PadNetworkProbe
from .inventory_pad_network_state import capture, services, path
from .inventory_pad_network_protocol import baseline_ready
from .effect_pad_mixin import valid, ability_system
from . import heal_ability_mixin as policy
from .heal_ability_network_protocol import PEERS, PLAN, FALSE_CLAIMS, near, require, validate_ack, validate_cases, expected_after_inventory

LONG_MONTAGE = "/Game/Weapons/Rifle/Animations/AM_MM_Rifle_Reload.AM_MM_Rifle_Reload"
ITEM = "/ShooterCore/Items/HealthPickup_Unused/ID_HealPickup.ID_HealPickup_C"


def counts_since(before):
    after = policy.snapshot()
    return {key: value-before[key] for key, value in after.items()
            if type(value) is int and key != "active_count"}


def equipped_ability(controller, cls):
    """Wait for real replicated spec/equipment, never fabricate a SourceObject."""
    _, quickbar = services(controller)
    item = quickbar.call_function("GetActiveSlotItem")
    if not valid(item) or path(item.ItemDef) != ITEM:
        return None
    asc = ability_system(controller.get_controlled_pawn())
    if not valid(asc):
        return None
    matches = []
    for spec in asc.get_property("ActivatableAbilities").Items:
        if not valid(spec.Ability) or spec.Ability.get_class() != cls:
            continue
        source = spec.SourceObject
        if not valid(source) or not source.is_a(ue.find_class("LyraRangedWeaponInstance")):
            continue
        if source.call_function("GetInstigator") != item:
            continue
        matches.extend(value for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value))
    return (asc, matches[0]) if len(matches) == 1 else None


class HealNetwork(InventoryNetwork):
    def __init__(self):
        super().__init__()
        self.timeout_seconds = 620
        self.cls = ue.load_class(policy.CLASS)
        self.current_visual = self.ability = self.anim = self.montage = None
        self.prepared_index = self.request_index = self.observed_index = -1
        self.original_health = {}
        self.stats_before = policy.snapshot()
        self.active_observed = self.montage_observed = self.cancel_requested = False
        self.native_elapsed = None

    def health_values(self):
        return {peer: float(owner["pawn"].get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth"))
                for peer, owner in self.owners.items()}

    def set_health(self, peer, value):
        current = self.health_values()[peer]
        if near(current, value):
            return
        result = self.bridge.call_function("ApplyAuthorityHealthDeltaToPlayer", "heal-network."+str(self.index)+"."+peer+"."+str(value),
            value-current, self.roster[peer]["player_token"])
        require(result.bApplied and near(float(result.HealthAfter), value), "native heal GAS fixture setup refused")

    def game_time(self):
        return float(self.gameplay_statics.call_function("GetTimeSeconds", self.world))

    def _status(self):
        result = super()._status()
        result.update(health_visual=copy.deepcopy(self.current_visual), heal_case=self.index, heal_stage=self.stage,
            heal_active=bool(self.ability.get_property("bIsActive")) if valid(self.ability) else False)
        if self.peer != "server":
            result["ready"] = result["ready"] and self.current_visual is not None
        return result

    def prepare(self, roster):
        InventoryNetwork.prepare(self, roster)
        # Warmup/loading has its own 300s readiness budget. Do not charge it
        # against the first 45s case before any gameplay trial has started.
        self.phase_started = time.monotonic()
        self.pristine = copy.deepcopy(self.baseline)
        self.original_health = self.health_values()
        self.original_rotations = {peer: owner["controller"].call_function("GetControlRotation") for peer, owner in self.owners.items()}
        instance = ue.load_class("/ShooterCore/Items/HealthPickup_Unused/WID_HealPickup.WID_HealPickup_C").get_cdo().InstanceType
        require(valid(instance) and instance.get_cdo().is_a(ue.find_class("LyraRangedWeaponInstance")),
                "heal original equipment cannot satisfy native ranged superclass; refuse unsafe activation")

    def begin(self):
        target, scenario, profile = PLAN[self.index]
        for peer in PEERS:
            self.set_health(peer, 75. if peer == target else 100.)
        inventory, quickbar = services(self.owners[target]["controller"])
        slot = int(quickbar.call_function("GetNextFreeItemSlot"))
        require(slot >= 0, "heal native owner inventory has no free slot")
        item = inventory.call_function("AddItemDefinition", ue.load_class(ITEM), 1)
        require(valid(item), "heal original native inventory grant failed")
        quickbar.call_function("AddItemToSlot", slot, item)
        quickbar.call_function("SetActiveSlotIndex", slot)
        self.ability = None
        self.stage, self.phase_started = "equipment", time.monotonic()

    def publish(self, stage):
        atomic_write(self.root/"heal-command.json", dict(self.current, stage=stage))

    def read_acks(self, stage):
        values = {peer: read_json(self.root/"heal-acks"/(str(self.index)+"-"+stage+"-"+peer+".json")) for peer in PEERS}
        return values if all(values.values()) else None

    def arm_server(self):
        target, scenario, profile = PLAN[self.index]
        resolved = equipped_ability(self.owners[target]["controller"], self.cls)
        prepared = {peer: capture(owner["controller"]) for peer, owner in self.owners.items()}
        if resolved is None or not all(prepared.values()):
            return
        self.asc, self.ability = resolved
        require(not self.ability.get_property("bIsActive"), "heal server active before owner request")
        ue.set_mixin_profile(self.ability, profile)
        if scenario == "native-timer":
            self.ability.set_property("Heal Montage", ue.load_object(ue.find_class("AnimMontage"), LONG_MONTAGE))
        self.montage = self.ability.get_property("Heal Montage")
        self.anim = self.owners[target]["pawn"].Mesh.call_function("GetAnimInstance")
        statuses = {peer: self._peer_status(peer) for peer in PEERS}
        self.current = dict(run_id=self.run_id, case_index=self.index, target=target, scenario=scenario, profile=profile,
            ability_class=path(self.cls), roster=copy.deepcopy(self.roster), prepared_inventory=prepared,
            original_inventory=copy.deepcopy(self.pristine), original_health=copy.deepcopy(self.original_health),
            prepared_health=self.health_values(), client_pawns={peer: statuses[peer]["player"]["pawn_path"] for peer in PEERS},
            client_worlds={peer: statuses[peer]["player"]["world_token"] for peer in PEERS}, acks={},
            native_inventory_equipment_ability_grant=True, native_source_verified=True, native_type_preserved=self.ability.get_class() == self.cls,
            instancing_policy=int(self.ability.InstancingPolicy), net_execution_policy=int(self.ability.NetExecutionPolicy))
        self.stats_before, self.active_observed = policy.snapshot(), False
        self.publish("prepare")
        self.stage = "prepared"

    def server_tick(self):
        if self.stage == "release":
            release = read_json(self.root/"release.json")
            if release is not None:
                require(release["run_id"] == self.run_id, "foreign heal release")
                self.finish()
            return
        if self.stage == "ready":
            roster = self._roster(PEERS)
            if roster is not None:
                self.prepare(roster)
            return
        if self.stage == "baseline":
            if baseline_ready({peer: self._peer_status(peer) for peer in PEERS}, self.pristine):
                self.begin()
        elif self.stage == "equipment":
            self.arm_server()
        elif self.stage == "prepared":
            acks = self.read_acks("prepare")
            if acks is None:
                return
            for peer, ack in acks.items():
                require((ack["run_id"], ack["case_index"], ack["peer"]) == (self.run_id, self.index, peer), "foreign heal prepared ACK")
                require(ack["source_ready"] is (peer == self.current["target"]), "heal prepared source crossed owner")
            self.publish("activate")
            self.stage = "active"
        elif self.stage == "active":
            active = bool(self.ability.get_property("bIsActive"))
            self.active_observed = self.active_observed or active
            if active or not self.active_observed:
                return
            after = self.health_values()
            inventories = {peer: capture(owner["controller"]) for peer, owner in self.owners.items()}
            if not all(near(value, 100.) for value in after.values()) or not all(inventories.values()):
                return
            self.current.update(after_health=after, server_native_active_observed=self.active_observed,
                after_inventory=inventories, server_ability_active_after=active, server_python_counters=counts_since(self.stats_before))
            require(inventories == expected_after_inventory(self.current), "native heal cost changed inventory beyond one use")
            self.publish("observe")
            self.stage = "observe"
        elif self.stage == "observe":
            acks = self.read_acks("observe")
            if acks is None:
                return
            for peer in PEERS:
                validate_ack(self.current, acks[peer], peer, "observe")
            self.current["acks"]["observe"] = acks
            if valid(self.anim):
                self.anim.call_function("Montage_Stop", 0., self.montage)
            InventoryNetwork.rollback(self)
            self.current["original_inventory_restored"] = all(self.fingerprint(owner["controller"]) == owner["fingerprint"]
                for owner in self.owners.values())
            for peer in PEERS:
                self.set_health(peer, self.original_health[peer])
            self.publish("rollback")
            self.stage = "rollback"
        elif self.stage == "rollback":
            acks = self.read_acks("rollback")
            if acks is None:
                return
            for peer in PEERS:
                validate_ack(self.current, acks[peer], peer, "rollback")
            self.current["acks"]["rollback"] = acks
            self.history.append(copy.deepcopy(self.current))
            ue.log("UEP_HEAL_NETWORK_CASE_PASSED "+str(self.index))
            self.index += 1
            self.phase_started = time.monotonic()
            if self.index == len(PLAN):
                validate_cases(self.history)
                self.restore()
                self.stage = "release"
                atomic_write(self.root/"ready-server.json", {"run_id": self.run_id})
            else:
                self.stage = "baseline"

    def client_track(self):
        if self.request_index != self.index or not valid(self.ability):
            return
        active = bool(self.ability.get_property("bIsActive"))
        self.active_observed = self.active_observed or active
        self.montage_observed = self.montage_observed or bool(self.anim.call_function("Montage_IsPlaying", self.montage))
        elapsed = self.game_time()-self.native_started
        if active and self.current["scenario"] == "native-cancel" and not self.cancel_requested and elapsed > .15:
            self.cancel_requested = True
            self.ability.call_function("K2_CancelAbility")
        elif not active and self.active_observed and self.native_elapsed is None:
            self.native_elapsed = elapsed

    def client_ack(self, stage):
        target = self.peer == self.current["target"]
        active = bool(self.ability.get_property("bIsActive")) if valid(self.ability) else False
        ack = dict(run_id=self.run_id, case_index=self.index, peer=self.peer, stage=stage, player=copy.deepcopy(self.player),
            inventory=copy.deepcopy(self.local_inventory), health_visual=copy.deepcopy(self.current_visual), ability_active=active)
        if stage == "observe":
            ack.update(native_asc_activation_requests=int(self.request_index == self.index), native_active_observed=self.active_observed,
                native_source_verified=target and valid(self.ability), native_cancel_requested=self.cancel_requested,
                python_counters=counts_since(self.stats_before), montage_was_playing=self.montage_observed,
                montage_still_playing=bool(self.anim.call_function("Montage_IsPlaying", self.montage)) if target else False,
                native_elapsed_seconds=self.native_elapsed, ability_class=path(self.ability.get_class()) if target else None,
                native_type_preserved=self.ability.get_class() == self.cls if target else True,
                instancing_policy=int(self.ability.InstancingPolicy) if target else None,
                net_execution_policy=int(self.ability.NetExecutionPolicy) if target else None)
        validate_ack(self.current, ack, self.peer, stage)
        atomic_write(self.root/"heal-acks"/(str(self.index)+"-"+stage+"-"+self.peer+".json"), ack)
        return ack

    def client_tick(self):
        packet = read_json(self.root/"heal-command.json")
        if packet is None or packet["case_index"] <= self.last_ack or self.local_inventory is None:
            return
        require(packet["run_id"] == self.run_id, "foreign heal command")
        self.index, self.current = packet["case_index"], packet
        target = self.peer == packet["target"]
        if self.prepared_index != self.index:
            if packet["stage"] != "prepare" or self.local_inventory != packet["prepared_inventory"][self.peer]:
                return
            expected_health = packet["prepared_health"][self.peer]
            if not near(self.player["health"], expected_health) or self.current_visual is None:
                return
            self.ability = self.anim = self.montage = None
            if target:
                controller = ue.find_object(self.player["controller_path"])
                resolved = equipped_ability(controller, self.cls)
                if resolved is None:
                    return
                self.asc, self.ability = resolved
                require(not self.ability.get_property("bIsActive"), "heal owner active before native ASC request")
                ue.set_mixin_profile(self.ability, packet["profile"])
                if packet["scenario"] == "native-timer":
                    self.ability.set_property("Heal Montage", ue.load_object(ue.find_class("AnimMontage"), LONG_MONTAGE))
                self.montage = self.ability.get_property("Heal Montage")
                self.anim = controller.get_controlled_pawn().Mesh.call_function("GetAnimInstance")
                aim_above_players(controller)
            self.stats_before = policy.snapshot()
            self.active_observed = self.montage_observed = self.cancel_requested = False
            self.native_elapsed = None
            self.prepared_index = self.index
            atomic_write(self.root/"heal-acks"/(str(self.index)+"-prepare-"+self.peer+".json"),
                dict(run_id=self.run_id, case_index=self.index, peer=self.peer, source_ready=target))
        if packet["stage"] == "activate" and target and self.request_index != self.index:
            self.native_started = self.game_time()
            require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native owning ASC rejected heal request")
            self.request_index = self.index
        self.client_track()
        if packet["stage"] == "observe" and self.observed_index != self.index:
            if self.local_inventory != expected_after_inventory(packet)[self.peer] or self.current_visual is None or not near(self.player["health"], 100.) or (target and
                    (not self.active_observed or self.ability.get_property("bIsActive") or self.native_elapsed is None)):
                return
            self.history.append(self.client_ack("observe"))
            self.observed_index = self.index
        elif packet["stage"] == "rollback":
            if self.local_inventory != packet["original_inventory"][self.peer] or self.current_visual is None or not near(
                    self.player["health"], packet["original_health"][self.peer]):
                return
            if target and valid(self.anim):
                self.anim.call_function("Montage_Stop", 0., self.montage)
            self.client_ack("rollback")
            self.ability = self.anim = self.montage = None
            self.last_ack = self.index
            if self.index == len(PLAN)-1:
                atomic_write(self.root/("ready-"+self.peer+".json"), {"run_id": self.run_id})

    def restore(self):
        if self.peer == "server" and self.owners:
            if valid(self.ability) and self.ability.get_property("bIsActive"):
                self.ability.call_function("K2_CancelAbility")
            for peer in PEERS:
                self.set_health(peer, self.original_health[peer])
                self.owners[peer]["controller"].call_function("SetControlRotation", self.original_rotations[peer])
            InventoryNetwork.rollback(self)
            self.restored_players = {}
            for peer, owner in self.owners.items():
                pawn, movement = owner["pawn"], owner["movement"]
                pawn.set_actor_location(owner["location"])
                movement.call_function("StopMovementImmediately")
                movement.call_function("SetMovementMode", owner["mode"], owner["custom_mode"])
                actual = pawn.get_actor_location()
                restored = max(abs(getattr(actual, axis)-getattr(owner["location"], axis)) for axis in ("x", "y", "z")) < .01
                restored = restored and int(movement.MovementMode) == owner["mode"] and int(movement.CustomMovementMode) == owner["custom_mode"]
                require(restored and self.fingerprint(owner["controller"]) == owner["fingerprint"], "heal native owner restore incomplete")
                self.restored_players[peer] = True
            self.owners.clear()

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        aim_restored = self.peer == "server"
        try:
            self.restore()
            self.scope.close()
            if self.peer != "server" and self.original_aim is not None:
                controller = ue.find_object(self.player["controller_path"])
                if valid(self.ability) and self.ability.get_property("bIsActive"):
                    self.ability.call_function("K2_CancelAbility")
                controller.call_function("SetControlRotation", self.original_aim)
                actual = controller.call_function("GetControlRotation")
                aim_restored = max(abs(getattr(actual, key)-getattr(self.original_aim, key)) for key in ("pitch", "yaw", "roll")) < .01
                require(aim_restored, "heal native client aim not restored")
        except Exception:
            error = (error or "")+traceback.format_exc()
        report = dict(schema_version=1, status="failed" if error else "passed", error=error, run_id=self.run_id,
            peer=self.peer, cases=self.history, native_players_restored=getattr(self, "restored_players", {}),
            client_aim_restored=aim_restored, hud=hud_state.snapshot(), weapon_observer=weapon_observer.snapshot(),
            heal_ability_observers=policy.snapshot(), native_inventory_equipment_ability_grant=True,
            native_owner_asc_activation=True, gameplay_slice=dict(enabled=False), elapsed_seconds=self._wall_elapsed())
        report.update({field: False for field in FALSE_CLAIMS})
        if error is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        (ue.log_error if error else ue.log)("UEP_HEAL_NETWORK_"+("FAILED "+error if error else "PASSED"))
        self.shutdown_binding()
        self._request_quit()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            now = time.monotonic()
            require(self._wall_elapsed() < self.timeout_seconds, "heal network total timeout")
            if now < self.next_tick:
                return True
            self.next_tick = now+.03
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
                PadNetworkProbe.visual(self)
            atomic_write(self.root/"status"/(self.peer+".json"), self._status())
            if self.peer == "server":
                require(now-self.phase_started < (300 if self.stage == "ready" else 45), "heal case timeout: "+str(self.index)+"/"+self.stage)
                self.server_tick()
            else:
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run_id and len(self.history) == len(PLAN), "premature heal release")
                    self.finish()
                else:
                    self.client_tick()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False


if "-UEPHealAbilityNetwork" in sys.argv:
    runtime = HealNetwork()
    ticker = ue.add_ticker(runtime.tick)
