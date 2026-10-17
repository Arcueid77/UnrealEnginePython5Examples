"""Separate native clients inject input; only authority creates/restores test items."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture, services
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, arg
from uep_lyra_abilities.quickslot_mixin import CLASS as ABILITY
from .quickbar_input_network_validation import token
from .quickbar_input_validation import fingerprint, prepare, restore
from .enhanced_input_validation import Validation as Native, fill_slots
from .enhanced_input_contract import PLAN, CLASS, require
from .enhanced_input_network_contract import PEERS
from . import enhanced_input_mixin as policy, quickbar_input_mixin as helper
from .enhanced_input_bindings import function_names


class Client(Native):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.root, self.peer, self.run, self.network_fixture = Path(result).parent, peer, run, True
        self.require_auto_active = self.require_local_playing_phase = False
        self.foreign = None
        self.report.update(peer=peer, run_id=run, network_acceptance=True, local_inventory_written=False, gameplay_state_delivered_by_files=False)

    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is not None:
            require(gate["native_playing_phase"], "input client bypassed native Playing"); super().ready()

    def begin(self):
        if not self.initialized:
            if capture(self.controller) is None: return
            self.initialize()
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
            self.report["native_net_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)
            atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index)); self.enter("permit")

    def find_foreign(self):
        plan = token(self.root, "input-plan.json", self.run)
        if plan is None: return False
        other = next(peer for peer in PEERS if peer != self.peer)
        actors, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.load_class(CLASS))
        for actor in actors:
            state = actor.get_property("PlayerState")
            if valid(state) and int(state.PlayerId) == plan["player_ids"][other]:
                self.foreign = actor
                self.foreign_before = (dict(policy.evidence(actor)), dict(helper.evidence(actor)), str(ue.get_mixin_profile(actor)))
                return True
        return False

    def record_trial(self, row):
        row["foreign_actor_input_and_helper_counters_unchanged"] = valid(self.foreign) and (dict(policy.evidence(self.foreign)), dict(helper.evidence(self.foreign)), str(ue.get_mixin_profile(self.foreign))) == self.foreign_before
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, peer=self.peer, index=self.index, row=copy.deepcopy(row)))

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 420, "native input client timeout: "+self.phase)
            if self.phase == "permit":
                permit = token(self.root, self.peer+"-permit.json", self.run); model = capture(self.controller)
                if self.foreign is None and not self.find_foreign(): return True
                empty = PLAN[self.index][4]
                if permit is not None and permit["index"] == self.index and model is not None and model["active"] == PLAN[self.index][2] and len(model["items"]) == 3 and all((value is None) == (index == empty) for index, value in enumerate(model["slots"])): self.start_trial()
            elif self.phase == "network-complete":
                if token(self.root, "input-restored.json", self.run) is not None and fingerprint(self.controller) == self.original and capture(self.controller) == self.original_model:
                    self.report["original_inventory_restored"] = True
                    atomic_write(self.root/(self.peer+"-clean.json"), dict(run_id=self.run)); self.enter("release")
            elif self.phase == "release":
                if token(self.root, "release.json", self.run) is not None: self.exit_native()
            else: Native.tick(self, seconds)
            atomic_write(self.root/(self.peer+"-status.json"), dict(run_id=self.run, phase=self.phase, index=self.index, elapsed_seconds=time.monotonic()-self.started)); return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False

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
        (ue.log_error if error else ue.log)("UEP_CHARACTER_INPUT_"+("FAILED "+error if error else "NETWORK_READY")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_INPUT_SHUTDOWN_"+self.report["status"].upper())


class Server:
    def __init__(self, result, run):
        self.path, self.root, self.run = Path(result), Path(result).parent, run
        self.fixture = PlayingFixture(result, run); self.fixture.ability_class = ABILITY
        self.started, self.finished, self.position, self.current, self.prepared, self.restored = time.monotonic(), False, 0, None, False, False
        self.originals, self.models, self.slots, self.counts = {}, {}, {}, {}
        self.report = dict(status="running", error=None, run_id=run, cases=[], original_inventory_restored=False, server_waited_for_client_process_exit=False,
            all_cleanup_frozen_before_release=False, server_character_receivers_and_helpers_not_invoked=False, native_rpc_bypassed=False, gameplay_state_delivered_by_files=False, full_acceptance=False)

    def setup(self):
        self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"])
        self.report["native_input_bindings"] = function_names(self.fixture.owners["A"]["pawn"].get_class())
        for peer, owner in self.fixture.owners.items():
            controller, actor = owner["controller"], owner["pawn"]
            self.originals[peer], self.models[peer] = fingerprint(controller), capture(controller)
            self.counts[peer] = (dict(policy.evidence(actor)), dict(helper.evidence(actor)))
            require(self.models[peer] is not None, "input authority original equipment unavailable")
            prepare(controller); self.slots[peer] = list(services(controller)[1].call_function("GetSlots"))
        atomic_write(self.root/"input-plan.json", dict(run_id=self.run, player_ids=self.report["player_ids"])); self.prepared = True

    def start_trial(self):
        peer, index = PEERS[self.position//len(PLAN)], self.position % len(PLAN)
        request = token(self.root, peer+"-request.json", self.run)
        if request is None or request["index"] != index: return
        owner = self.fixture.owners[peer]; quickbar = services(owner["controller"])[1]
        fill_slots(quickbar, self.slots[peer]); quickbar.call_function("SetActiveSlotIndex", PLAN[index][2])
        empty = PLAN[index][4]
        if empty is not None: quickbar.call_function("RemoveItemFromSlot", empty)
        models = {name: capture(value["controller"]) for name, value in self.fixture.owners.items()}
        if not all(models.values()): return
        self.current = dict(peer=peer, index=index, authority_role=int(owner["pawn"].call_function("GetLocalRole")), other_owner_inventory_unchanged=True, before_models=models)
        self.case_started = time.monotonic(); atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row = self.current; peer = row["peer"]
        models = {name: capture(owner["controller"]) for name, owner in self.fixture.owners.items()}
        row["other_owner_inventory_unchanged"] &= all(models[name] == row["before_models"][name] for name in PEERS if name != peer)
        require(row["other_owner_inventory_unchanged"], "input changed other native owner's equipment")
        ack = token(self.root, peer+"-"+str(row["index"])+"-ack.json", self.run); actual = models[peer]
        if ack is None or actual is None or actual["active"] != PLAN[row["index"]][3]:
            require(time.monotonic()-self.case_started < 15, "native input RPC/equipment ack timeout"); return
        require((ack["peer"], ack["index"]) == (peer, row["index"]) and actual == ack["row"]["inventory"], "input owner/authority equipment differs")
        row.update(authority_inventory=actual); self.report["cases"].append(row)
        self.current = None; self.position += 1; ue.log("UEP_CHARACTER_INPUT_NETWORK_CASE_PASSED "+str(self.position))

    def rollback(self):
        for peer, owner in self.fixture.owners.items():
            fill_slots(services(owner["controller"])[1], self.slots[peer]); restore(owner["controller"], self.originals[peer])
            require(capture(owner["controller"]) == self.models[peer], "input authority original equipment not restored")
        self.report["original_inventory_restored"] = True
        self.report["server_character_receivers_and_helpers_not_invoked"] = all((dict(policy.evidence(owner["pawn"])), dict(helper.evidence(owner["pawn"]))) == self.counts[peer] for peer, owner in self.fixture.owners.items())
        self.restored = True

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 420, "native input authority timeout")
            if self.restored:
                # No controller/Pawn reads after one-way release/disconnect.
                if all(token(self.root, peer+"-clean.json", self.run) is not None for peer in PEERS):
                    self.report["all_cleanup_frozen_before_release"] = True; atomic_write(self.root/"release.json", dict(run_id=self.run))
                    exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                    if all(value is not None and value["exit_code"] == 0 for value in exits): self.report["server_waited_for_client_process_exit"] = True; self.finish()
            elif not self.fixture.playing_gate: self.fixture.wait_playing()
            elif not self.fixture.owners: self.fixture.setup()
            elif not self.prepared: self.setup()
            elif self.position == 2*len(PLAN):
                if all(token(self.root, peer+"-complete.json", self.run) is not None for peer in PEERS):
                    self.rollback(); atomic_write(self.root/"input-restored.json", dict(run_id=self.run))
            elif self.current is None: self.start_trial()
            else: self.observe()
            atomic_write(self.root/"server-status.json", dict(run_id=self.run, position=self.position, restored=self.restored, prepared=self.prepared, elapsed_seconds=time.monotonic()-self.started)); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and self.prepared and not self.restored:
            try: self.rollback()
            except Exception: error += traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_CHARACTER_INPUT_"+("FAILED "+error if error else "NETWORK_READY")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_INPUT_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPCharacterInputNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterInputNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
