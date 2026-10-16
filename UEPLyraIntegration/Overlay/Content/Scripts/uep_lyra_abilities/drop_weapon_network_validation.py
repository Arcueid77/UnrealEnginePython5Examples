"""Local prediction -> original native GAS RPC -> authority inventory deletion."""
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
from . import drop_weapon_mixin as policy
from .drop_weapon_validation import Validation as NativeDrop, DEFINITIONS
from .drop_weapon_contract import PLAN, require
from .quickslot_network_validation import fingerprint
from .jump_network_validation import Server as PlayingFixture, arg, PEERS


class Client(NativeDrop):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root, self.network_fixture = peer, run, Path(result).parent, True
        self.report.update(peer=peer, run_id=run, local_inventory_written=False, native_rpc_bypassed=False,
            gameplay_event_replication_tested=False, packet_loss_tested=False, travel_rejoin_tested=False)

    def ready(self):
        value = read_json(self.root/"playing-ready.json")
        if value is None: return
        require(value["run_id"] == self.run and value["native_playing_phase"], "foreign/nonplaying DropWeapon gate")
        NativeDrop.ready(self)

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report["native_net_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_net_mode"] == "Client", "DropWeapon owner is not a native client")
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def prepare_inventory(self, count, initial):
        require(int(self.quickbar.call_function("GetActiveSlotIndex")) == initial and len(self.inventory.call_function("GetAllItems")) == count+1,
            "authority DropWeapon fixture has not replicated")

    def complete_trial(self): self.enter("network-settled")

    def finish(self, error=None):
        if error: return self.exit_native(error)
        atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "current_observation"): self.report["failed_native_inventory"] = copy.deepcopy(self.current_observation)
        try:
            if hasattr(self, "action"): self.controller.inject_enhanced_input_for_action(self.action, False)
            if hasattr(self, "ability"):
                self.report["original_player_restored"] = fingerprint(self.controller) == self.original and capture(self.controller) == self.original_model
                ue.set_mixin_profile(self.ability, "Python")
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_DROP_WEAPON_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def tick(self, seconds):
        if not self.phase.startswith("network-"): return NativeDrop.tick(self, seconds)
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native DropWeapon owner barrier timeout")
            if self.phase == "network-permit":
                value = read_json(self.root/(self.peer+"-permit.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign DropWeapon native permit")
                    count, initial = PLAN[self.index//2][1:3]
                    if value["index"] == self.index and int(self.quickbar.call_function("GetActiveSlotIndex")) == initial and len(self.inventory.call_function("GetAllItems")) == count+1:
                        NativeDrop.begin(self)
            elif self.phase == "network-settled" and time.monotonic()-self.phase_started > .25:
                require(all(policy.snapshot()[key] == self.at_drop_end[key] for key in ("activations", "fallback_activations")), "late native client DropWeapon reactivation")
                self.row["no_late_activation"] = True
                atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, peer=self.peer,
                    index=self.index, row=copy.deepcopy(self.row)))
                self.enter("network-restored")
            elif self.phase == "network-restored":
                value = read_json(self.root/(self.peer+"-restored.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign native DropWeapon restoration")
                    if value["index"] == self.index and fingerprint(self.controller) == self.original and capture(self.controller) == self.original_model:
                        self.row["fixture_original_restored"] = True; self.sides.append(copy.deepcopy(self.row))
                        if self.index % 2:
                            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
                            ue.log("UEP_DROP_WEAPON_CASE_OBSERVED "+self.name)
                        self.index += 1
                        if self.index == len(PLAN)*2: self.finish()
                        else: self.begin()
            elif self.phase == "network-complete":
                value = read_json(self.root/"release.json")
                if value is not None:
                    require(value["run_id"] == self.run, "foreign DropWeapon release"); self.exit_native()
            return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


class Server(PlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.ability_class, self.prepared, self.released = policy.CLASS, False, False
        self.originals, self.original_models = {}, {}
        self.report.update(fixture_authority_inventory_setup=True, original_inventory_restored=False,
            native_rpc_bypassed=False, inventory_properties_written=False, gameplay_event_replication_tested=False)

    def select(self, peer):
        self.controller = self.owners[peer]["controller"]
        self.inventory, self.quickbar = services(self.controller)
        self.original = self.originals[peer]; self.original_items = set(self.original["items"])

    def prepare(self):
        values = {peer: capture(owner["controller"]) for peer, owner in self.owners.items()}
        if not all(values.values()): return
        self.original_models = values
        self.originals = {peer: fingerprint(owner["controller"]) for peer, owner in self.owners.items()}
        require(all(len(row["items"]) == 1 and row["active"] == 0 and row["slots"][1:] == [None, None] for row in self.originals.values()),
            "native DropWeapon authority baseline is not original pistol-only inventory")
        self.prepared = True

    def start_case(self):
        peer, index = PEERS[self.position//(len(PLAN)*2)], self.position % (len(PLAN)*2)
        value = read_json(self.root/(peer+"-request.json"))
        if value is None or value["index"] != index: return
        require(value["run_id"] == self.run, "foreign native DropWeapon request")
        self.select(peer)
        require(fingerprint(self.controller) == self.original and capture(self.controller) == self.original_models[peer], "authority original inventory not restored")
        name, count, initial, expected = PLAN[index//2]
        ability = self.owners[peer]["ability"]
        ue.set_mixin_profile(ability, ("BlueprintFallback", "Python")[index % 2])
        NativeDrop.prepare_inventory(self, count, initial)
        self.before, self.case_started = policy.snapshot(), time.monotonic()
        self.current = dict(target=peer, index=index, name=name, authoritative_role=int(self.owners[peer]["pawn"].call_function("GetLocalRole")),
            expected_slot=expected, initial_slot=initial, removed_item_path=path(self.quickbar.call_function("GetSlots")[initial]),
            foreign_owner_unchanged=True)
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        require(time.monotonic()-self.case_started < 20., "authority DropWeapon mutation/replication timeout")
        self.select(peer)
        current, model = fingerprint(self.controller), capture(self.controller)
        row["last_authority_inventory"] = current
        for key, owner in self.owners.items():
            if key != peer:
                row["foreign_owner_unchanged"] &= fingerprint(owner["controller"]) == self.originals[key] and capture(owner["controller"]) == self.original_models[key]
        require(row["foreign_owner_unchanged"], "DropWeapon changed another owner's native inventory/equipment")
        ack = read_json(self.root/(peer+"-"+str(row["index"])+"-ack.json"))
        removed = row["removed_item_path"] is None or row["removed_item_path"] not in current["items"]
        if not (ack is not None and removed and current["slots"][row["initial_slot"]] is None and current["active"] == row["expected_slot"] and model is not None): return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]), "foreign native DropWeapon ack")
        ability = self.owners[peer]["ability"]; stats = policy.snapshot()
        row.update(authority_inventory_model=model, removed_item_absent=removed, dropped_slot_empty=True,
            original_item_identities_preserved=self.original_items.issubset(set(current["items"])), native_ability_inactive=not ability.get_property("bIsActive"),
            authority_counters={key: value-self.before[key] for key, value in stats.items() if type(value) is int and key != "active_count"}, client=ack)
        NativeDrop.rollback(self)
        row["authority_original_restored"] = fingerprint(self.controller) == self.original and capture(self.controller) == self.original_models[peer]
        require(row["authority_original_restored"], "native DropWeapon authority original item/equipment restore failed")
        self.report["cases"].append(copy.deepcopy(row))
        atomic_write(self.root/("authority-"+str(self.position)+".json"), dict(run_id=self.run, row=row))
        atomic_write(self.root/(peer+"-restored.json"), dict(run_id=self.run, index=row["index"]))
        ue.log("UEP_DROP_WEAPON_NETWORK_CASE_OBSERVED "+peer+"/"+str(row["index"]))
        self.current = None; self.position += 1

    def restore(self):
        for peer in self.owners:
            self.select(peer); NativeDrop.rollback(self)
        self.report["original_inventory_restored"] = all(fingerprint(owner["controller"]) == self.originals[peer] and
            capture(owner["controller"]) == self.original_models[peer] for peer, owner in self.owners.items())

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native DropWeapon authority timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS)*len(PLAN)*2:
                    complete = [read_json(self.root/(peer+"-complete.json")) for peer in PEERS]
                    if all(value is not None and value["run_id"] == self.run for value in complete):
                        if not self.released:
                            self.restore(); atomic_write(self.root/"release.json", dict(run_id=self.run)); self.released = True
                        exits = [read_json(self.root/(peer+"-exited.json")) for peer in PEERS]
                        if all(value is not None and value["exit_code"] == 0 for value in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(position=self.position, current=self.current, elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error:
            self.report["failed_authority_observation"] = copy.deepcopy(self.current)
            if self.prepared and not self.released:
                try: self.restore()
                except Exception: error += traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_DROP_WEAPON_NETWORK_"+("FAILED "+error if error else "READY")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DROP_WEAPON_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPDropWeaponNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPDropWeaponNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
