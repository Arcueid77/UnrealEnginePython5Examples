"""Owner BP -> local GAS -> native Server RPC, with authority-only item fixtures."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, arg
from uep_lyra_abilities.quickslot_mixin import CLASS as ABILITY
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture, services
from . import quickbar_input_mixin as policy
from .quickbar_input_validation import Validation as Native, fingerprint, prepare, restore
from .quickbar_input_contract import PLAN, require
from .quickbar_input_network_contract import server_gate

PEERS = ("A", "B0")


def token(root, name, run):
    value = read_json(root/name)
    if value is not None: require(value["run_id"] == run, "foreign Character slot rendezvous")
    return value


class Client(Native):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.root, self.peer, self.run, self.network_fixture = Path(result).parent, peer, run, True
        self.require_auto_active = self.require_local_playing_phase = False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, local_inventory_written=False, gameplay_state_delivered_by_files=False)

    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is None: return
        require(gate["native_playing_phase"], "Character slot bypassed actual Playing gate")
        self.report["authority_phase_gate_observed"] = True
        super().ready()

    def begin(self):
        if not self.initialized:
            if capture(self.controller) is None: return
            self.initialize()
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
            self.report["native_net_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)
            atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index)); self.enter("network-permit")

    def record_trial(self, row):
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, peer=self.peer, index=self.index, row=copy.deepcopy(row)))

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 400, "Character slot client timeout: "+self.phase)
            if self.phase == "network-permit":
                permit = token(self.root, self.peer+"-permit.json", self.run)
                model = capture(self.controller)
                if permit is not None and permit["index"] == self.index and model is not None and model["active"] == PLAN[self.index][2] and (
                        len(model["items"]) == 3 and (model["slots"][2] is None) == PLAN[self.index][6]): self.start_trial()
            elif self.phase == "network-complete":
                if token(self.root, "release.json", self.run) is not None and fingerprint(self.controller) == self.original and capture(self.controller) == self.original_model:
                    self.report["original_inventory_restored"] = True; self.exit_native()
            else: Native.tick(self, seconds)
            atomic_write(self.root/(self.peer+"-status.json"), dict(run_id=self.run, phase=self.phase, index=self.index,
                initialized=self.initialized, elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if error: return self.exit_native(error)
        try: self.restore_actor()
        except Exception: return self.exit_native(traceback.format_exc())
        atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run)); self.enter("network-complete")

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        if error:
            try: self.restore_actor()
            except Exception: error += traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_QUICKBAR_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()


class Server:
    def __init__(self, result, run):
        self.path, self.root, self.run = Path(result), Path(result).parent, run
        self.fixture = PlayingFixture(result, run); self.fixture.ability_class = ABILITY
        self.started, self.finished, self.position, self.current, self.prepared, self.restored = time.monotonic(), False, 0, None, False, False
        self.originals, self.models, self.slot_twos, self.actor_counts = {}, {}, {}, {}
        self.report = dict(status="running", error=None, run_id=run, cases=[], original_inventory_restored=False,
            server_waited_for_client_process_exit=False, server_character_helpers_not_invoked=False,
            native_rpc_bypassed=False, gameplay_state_delivered_by_files=False, full_acceptance=False)

    def setup(self):
        self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"])
        for peer, owner in self.fixture.owners.items():
            controller = owner["controller"]
            self.originals[peer], self.models[peer] = fingerprint(controller), capture(controller)
            self.actor_counts[peer] = dict(policy.evidence(owner["pawn"]))
            require(self.models[peer] is not None, "Character slot authority original equipment unavailable")
            prepare(controller); self.slot_twos[peer] = services(controller)[1].call_function("GetSlots")[2]
        self.prepared = True

    def start_trial(self):
        peer, index = PEERS[self.position//len(PLAN)], self.position % len(PLAN)
        request = token(self.root, peer+"-request.json", self.run)
        if request is None or request["index"] != index: return
        owner = self.fixture.owners[peer]; quickbar = services(owner["controller"])[1]
        empty, initial = PLAN[index][6], PLAN[index][2]
        current = quickbar.call_function("GetSlots")[2]
        if not empty and not valid(current): quickbar.call_function("AddItemToSlot", 2, self.slot_twos[peer])
        quickbar.call_function("SetActiveSlotIndex", initial)
        if empty and valid(current): quickbar.call_function("RemoveItemFromSlot", 2)
        models = {name: capture(value["controller"]) for name, value in self.fixture.owners.items()}
        if not all(models.values()): return
        self.current = dict(peer=peer, index=index, authority_role=int(owner["pawn"].call_function("GetLocalRole")),
            other_owner_inventory_unchanged=True, before_models=models)
        self.case_started = time.monotonic(); atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row = self.current; peer = row["peer"]
        models = {name: capture(owner["controller"]) for name, owner in self.fixture.owners.items()}
        for name in PEERS:
            if name != peer: row["other_owner_inventory_unchanged"] &= models[name] == row["before_models"][name]
        require(row["other_owner_inventory_unchanged"], "Character slot event changed the other native owner's inventory/equipment")
        ack = token(self.root, peer+"-"+str(row["index"])+"-ack.json", self.run)
        actual = models[peer]
        if ack is None or actual is None or actual["active"] != PLAN[row["index"]][5]:
            require(time.monotonic()-self.case_started < 15, "Character slot native RPC/equipment acknowledgement timeout"); return
        require((ack["peer"], ack["index"]) == (peer, row["index"]) and actual == ack["row"]["inventory"], "Character slot owner/authority equipment differs")
        row.update(authority_inventory=actual, client=ack["row"]); self.report["cases"].append(row)
        ue.log("UEP_CHARACTER_QUICKBAR_NETWORK_CASE_PASSED "+peer+"/"+str(row["index"]))
        self.current = None; self.position += 1

    def rollback(self):
        for peer, owner in self.fixture.owners.items():
            restore(owner["controller"], self.originals[peer])
            require(capture(owner["controller"]) == self.models[peer], "Character slot authority equipment not restored")
        self.report["original_inventory_restored"] = True
        self.report["server_character_helpers_not_invoked"] = all(policy.evidence(owner["pawn"]) == self.actor_counts[peer] for peer, owner in self.fixture.owners.items())
        self.restored = True

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 400, "Character slot authority timeout")
            if not self.fixture.playing_gate: self.fixture.wait_playing()
            elif not self.fixture.owners: self.fixture.setup()
            elif not self.prepared: self.setup()
            else:
                isolate_bots(self.fixture.statics, self.fixture.world, ue.find_class("LyraPlayerBotController"))
                if self.position == 2*len(PLAN):
                    if all(token(self.root, peer+"-complete.json", self.run) is not None for peer in PEERS):
                        if not self.restored: self.rollback()
                        atomic_write(self.root/"release.json", dict(run_id=self.run))
                        exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                        if all(value is not None and value["exit_code"] == 0 for value in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_trial()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(run_id=self.run, position=self.position, current=self.current,
                native_playing_gate=self.fixture.playing_gate, prepared=self.prepared, elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and self.prepared and not self.restored:
            try: self.rollback()
            except Exception: error += traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_CHARACTER_QUICKBAR_NETWORK_READY" if not error else error); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; server_gate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_QUICKBAR_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPCharacterQuickbarNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterQuickbarNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
