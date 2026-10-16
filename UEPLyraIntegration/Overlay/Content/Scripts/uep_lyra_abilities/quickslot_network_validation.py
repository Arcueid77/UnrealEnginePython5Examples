"""Two owners: local GAS events -> native Quickbar Server RPC -> equipment.

Authority-only inventory setup/rollback is an explicit fixture. No local
inventory write, direct Python handler call, UI message fabrication or movement
write is used. GameplayEvent delivery itself is not a replicated bus.
"""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture, services, path
from uep_lyra_world.effect_pad_mixin import valid
from . import quickslot_mixin as policy
from .quickslot_contract import PLAN, require
from .quickslot_validation import Validation as NativeQuickslot
from .jump_network_validation import Server as NativePlayingFixture, arg

PEERS = ("A", "B0")


def fingerprint(controller):
    inventory, quickbar = services(controller)
    return dict(items=sorted(path(value) for value in inventory.call_function("GetAllItems")),
        slots=[path(value) for value in quickbar.call_function("GetSlots")], active=int(quickbar.call_function("GetActiveSlotIndex")))


class Client(NativeQuickslot):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root, self.network_fixture = peer, run, Path(result).parent, True
        self.report.update(peer=peer, run_id=run, local_inventory_written=False, local_movement_written=False,
            ui_presentation_comparison_tested=False, gameplay_event_replication_tested=False)

    def ready(self):
        gate = read_json(self.root/"playing-ready.json")
        if gate is None: return
        require(gate["run_id"] == self.run and gate["native_playing_phase"], "foreign/nonplaying Quickslot gate")
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bAbilitySystemReady and snap.bHealthReady and
                    not snap.bDamageImmune and snap.Health > 0): continue
            require(str(snap.NetMode) == "Client", "Quickslot owner is not a real network client")
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if capture(controller) is None: continue
            self.world, self.controller, self.pawn = world, controller, controller.get_controlled_pawn()
            self.inventory, self.quickbar = services(controller)
            self.original = fingerprint(controller)
            self.original_items = set(self.original["items"])
            self.pristine_model = capture(controller)
            self.report["player_id"] = int(controller.PlayerState.PlayerId)
            atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, peer=self.peer,
                player_id=self.report["player_id"], original=copy.deepcopy(self.original)))
            self.begin(); return

    def prepare_inventory(self):
        require(len(self.quickbar.call_function("GetSlots")) == 3 and len(self.items()) == 3,
                "authority inventory fixture has not replicated all three real items")

    def begin(self):
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def record_trial(self, row):
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run,
            peer=self.peer, index=self.index, row=copy.deepcopy(row)))

    def tick(self, delta):
        if self.phase == "network-permit":
            try:
                require(time.monotonic()-self.started < 480., "Quickslot network permit timeout")
                permission = read_json(self.root/(self.peer+"-permit.json"))
                if permission is not None:
                    require(permission["run_id"] == self.run, "foreign Quickslot permit")
                    current = capture(self.controller)
                    if permission["index"] == self.index and current is not None and current["active"] == PLAN[self.index//2][1] and len(self.items()) == 3:
                        NativeQuickslot.begin(self)
                return True
            except Exception: self.finish(traceback.format_exc()); return False
        if self.phase == "network-complete":
            try:
                require(time.monotonic()-self.started < 480., "Quickslot native restore/release timeout")
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run, "foreign Quickslot release")
                    if fingerprint(self.controller) == self.original and capture(self.controller) == self.pristine_model:
                        self.native_end(); ue.set_mixin_profile(self.ability, "Python")
                        require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native default Quickslot reactivation failed")
                        self.report["original_player_restored"] = True
                        self.report["original_ability_active_restored"] = bool(self.ability.get_property("bIsActive")) and self.tasks() == 3
                        self.exit_native()
                return not self.finished
            except Exception: self.exit_native(traceback.format_exc()); return False
        return NativeQuickslot.tick(self, delta)

    def finish(self, error=None):
        if error: return self.exit_native(error)
        atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.result, self.report)
        (ue.log_error if error else ue.log)("UEP_QUICKSLOT_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()


class Server(NativePlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.ability_class, self.prepared, self.restored = policy.CLASS, False, False
        self.originals, self.original_models = {}, {}
        self.report.update(ability_activation_called_by_probe=False, fixture_authority_inventory_setup=True,
            inventory_properties_written=False, native_rpc_bypassed=False, ui_presentation_comparison_tested=False,
            gameplay_event_replication_tested=False, original_inventory_restored=False)

    def prepare(self):
        for peer, owner in self.owners.items():
            controller = owner["controller"]
            self.originals[peer], self.original_models[peer] = fingerprint(controller), capture(controller)
            require(self.original_models[peer] is not None, "native original equipment not ready")
            inventory, quickbar = services(controller)
            for definition in ("/ShooterCore/Weapons/Rifle/ID_Rifle.ID_Rifle_C", "/ShooterCore/Weapons/Shotgun/ID_Shotgun.ID_Shotgun_C"):
                slot = int(quickbar.call_function("GetNextFreeItemSlot"))
                require(slot >= 0, "authority fixture lacks a free original slot")
                item = inventory.call_function("AddItemDefinition", ue.load_class(definition), 1)
                quickbar.call_function("AddItemToSlot", slot, item)
        self.prepared = True

    def start_case(self):
        peer, index = PEERS[self.position//(len(PLAN)*2)], self.position % (len(PLAN)*2)
        request = read_json(self.root/(peer+"-request.json"))
        if request is None or request["index"] != index: return
        require(request["run_id"] == self.run, "foreign native Quickslot request")
        name, initial, expected = PLAN[index//2]
        controller = self.owners[peer]["controller"]
        _, quickbar = services(controller)
        quickbar.call_function("SetActiveSlotIndex", initial)
        models = {name: capture(owner["controller"]) for name, owner in self.owners.items()}
        if not all(models.values()): return
        self.current = dict(target=peer, index=index, name=name, profile=("BlueprintFallback", "Python")[index % 2],
            expected_slot=expected, authoritative_role=int(self.owners[peer]["pawn"].call_function("GetLocalRole")),
            other_inventory_unchanged=True, before_models=models)
        require(self.current["authoritative_role"] == 3, "Quickslot observer is not native authority")
        self.case_started = time.monotonic()
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        models = {name: capture(owner["controller"]) for name, owner in self.owners.items()}
        for name in PEERS:
            if name != peer:
                row["other_inventory_unchanged"] &= models[name] == row["before_models"][name]
        require(row["other_inventory_unchanged"], "native Quickslot changed the other owner's inventory/equipment")
        ack = read_json(self.root/(peer+"-"+str(row["index"])+"-ack.json"))
        actual = models[peer]
        if ack is None or actual is None or actual["active"] != row["expected_slot"]:
            require(time.monotonic()-self.case_started < 15., "native Quickbar RPC/equipment acknowledgement timeout")
            return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]), "foreign Quickslot ack")
        require(actual == ack["row"]["inventory"], "authority and owning client equipment/inventory differ")
        row.update(authority_inventory=actual, client=ack)
        self.report["cases"].append(row)
        ue.log("UEP_QUICKSLOT_NETWORK_CASE_PASSED "+peer+"/"+str(row["index"]))
        self.current = None; self.position += 1

    def restore(self):
        for peer, owner in self.owners.items():
            controller = owner["controller"]; inventory, quickbar = services(controller)
            original = self.originals[peer]
            quickbar.call_function("SetActiveSlotIndex", original["active"])
            for slot, item in enumerate(quickbar.call_function("GetSlots")):
                if valid(item) and path(item) not in original["items"]: quickbar.call_function("RemoveItemFromSlot", slot)
            for item in inventory.call_function("GetAllItems"):
                if path(item) not in original["items"]: inventory.call_function("RemoveItemInstance", item)
            require(fingerprint(controller) == original and capture(controller) == self.original_models[peer],
                    "authority native Quickslot fixture did not restore original item/slot/equipment identities")
        self.report["original_inventory_restored"] = True
        self.restored = True

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native Quickslot server timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS)*len(PLAN)*2:
                    complete = [read_json(self.root/(peer+"-complete.json")) for peer in PEERS]
                    if all(row is not None and row["run_id"] == self.run for row in complete):
                        if not self.restored:
                            self.restore(); atomic_write(self.root/"release.json", dict(run_id=self.run))
                        exits = [read_json(self.root/(peer+"-exited.json")) for peer in PEERS]
                        if all(row is not None and row["exit_code"] == 0 for row in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(ready=bool(self.owners), prepared=self.prepared,
                position=self.position, current=self.current, native_playing_gate=self.playing_gate,
                authority_readiness=self.report.get("authority_readiness"), elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and self.prepared and not self.restored:
            try: self.restore()
            except Exception: error += traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_QUICKSLOT_NETWORK_READY" if not error else error)
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                stats = self.report["policy_shutdown"]
                require(len(self.report["cases"]) == 40 and self.report["server_waited_for_client_process_exit"] and
                        self.report["original_inventory_restored"], "native Quickslot authority matrix/restore/exit incomplete")
                require(stats["activations"] > 0 and stats["active_count"] == 0 and
                        stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [], "authority Quickslot task scope leak")
                self.report["status"] = "passed"
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_QUICKSLOT_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPQuickslotNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPQuickslotNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
