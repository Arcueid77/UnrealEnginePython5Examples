"""Two actual local UI owners; LocalOnly GAS must remain inactive on server.

Files schedule/observe tests. They never deliver gameplay/UI payloads or RPCs.
The non-target client independently observes its own real UI/ability unchanged.
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
from uep_lyra_world.inventory_pad_network_state import capture
from . import widget_held_mixin as policy
from .widget_held_validation import Validation as NativeUI
from .widget_held_contract import CLASSES, NETWORK_PLAN, require
from .jump_network_validation import Server as PlayingFixture, arg

PEERS = ("A", "B0")


class Client(NativeUI):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root = peer, run, Path(result).parent
        self.targets, self.plan, self.timeout, self.safety = ("tdm",), NETWORK_PLAN, 480., False
        self.passive_seen = set()
        self.report.update(peer=peer, run_id=run, passive_held_observations=[], packet_loss_tested=False,
            travel_rejoin_tested=False, gameplay_state_delivered_by_files=False, localonly_ui_replication_claimed=False)

    def ready(self):
        gate = read_json(self.root / "playing-ready.json")
        if gate is None: return
        require(gate["run_id"] == self.run and gate["native_playing_phase"], "foreign/nonplaying held-widget readiness")
        NativeUI.ready(self)

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report.update(player_id=int(self.controller.PlayerState.PlayerId),
            native_net_mode=str(bridge.call_function("CaptureSnapshot").NetMode), native_owner_role=int(self.pawn.call_function("GetLocalRole")))
        require(self.report["native_net_mode"] == "Client" and self.report["native_owner_role"] == 2,
                "held-widget owner is not an actual autonomous client")
        atomic_write(self.root / (self.peer + "-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        atomic_write(self.root / (self.peer + "-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def may_finish_hold(self):
        atomic_write(self.root / (self.peer + "-held.json"), dict(run_id=self.run, peer=self.peer, index=self.index,
            native_widget_activated=self.row["native_widget_activated"], native_widget_in_original_layer=self.row["native_widget_in_original_layer"]))
        value = read_json(self.root / (self.peer + "-act.json"))
        if value is None: return False
        require(value["run_id"] == self.run, "foreign held-widget action permit")
        return value["index"] == self.index

    def observe_foreign_trial(self):
        if not hasattr(self, "abilities"): return
        value = read_json(self.root / "observe.json")
        if value is None or value["target"] == self.peer: return
        require(value["run_id"] == self.run and value["target"] in PEERS, "foreign held-widget observation request")
        state = self.state()
        unchanged = state == dict(model=self.original_model, active=False, tasks=0, menu_active=False)
        require(unchanged, "other client's held-widget affected this local owner")
        row = dict(run_id=self.run, peer=self.peer, target=value["target"], index=value["index"], stage=value["stage"],
            native_owner_unchanged=True, native_ability_inactive=not state["active"], native_tasks=state["tasks"],
            native_menu_empty=not state["menu_active"], player_id=self.report["player_id"])
        atomic_write(self.root / (self.peer + "-passive.json"), row)
        key = (value["target"], value["index"], value["stage"])
        if value["stage"] == "held" and key not in self.passive_seen:
            self.passive_seen.add(key); self.report["passive_held_observations"].append(row)

    def complete_trial(self):
        atomic_write(self.root / (self.peer + "-" + str(self.index) + "-ack.json"),
            dict(run_id=self.run, peer=self.peer, index=self.index, row=copy.deepcopy(self.row)))
        NativeUI.complete_trial(self)

    def finish(self, error=None):
        if error: return NativeUI.finish(self, error)
        atomic_write(self.root / (self.peer + "-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < self.timeout, "held-widget owner network barrier timeout")
            self.observe_foreign_trial()
            if self.phase == "network-permit":
                value = read_json(self.root / (self.peer + "-permit.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign held-widget permit")
                    if value["index"] == self.index: NativeUI.begin(self)
            elif self.phase == "network-complete":
                value = read_json(self.root / "release.json")
                if value is not None:
                    require(value["run_id"] == self.run, "foreign held-widget release")
                    NativeUI.finish(self)
            else:
                return NativeUI.tick(self, delta)
            return not self.finished
        except Exception:
            NativeUI.finish(self, traceback.format_exc()); return False


class Server(PlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.ability_class, self.prepared, self.originals, self.released = CLASSES["tdm"], False, {}, False
        self.report.update(original_player_states_restored=False, native_localonly_authority_inactive=True,
            gameplay_state_delivered_by_files=False, localonly_ui_replication_claimed=False, network_pause_tested=False)

    def state(self, peer):
        owner = self.owners[peer]
        return dict(model=capture(owner["controller"]), active=bool(owner["ability"].get_property("bIsActive")),
                    tasks=len(owner["ability"].get_property("ActiveTasks")))

    def prepare(self):
        values = {peer: self.state(peer) for peer in PEERS}
        if not all(row["model"] is not None for row in values.values()): return
        require(all(not row["active"] and row["tasks"] == 0 for row in values.values()), "LocalOnly authority ability unexpectedly active")
        require(all(int(owner["ability"].get_property("NetExecutionPolicy")) == 1 and
                    int(owner["pawn"].call_function("GetLocalRole")) == 3 for owner in self.owners.values()), "LocalOnly authority source differs")
        self.originals, self.prepared = values, True

    def start_case(self):
        peer, index = PEERS[self.position // (len(NETWORK_PLAN) * 2)], self.position % (len(NETWORK_PLAN) * 2)
        value = read_json(self.root / (peer + "-request.json"))
        if value is None or value["index"] != index: return
        require(value["run_id"] == self.run, "foreign held-widget request")
        self.case_started = time.monotonic()
        self.current = dict(target=peer, index=index, name=NETWORK_PLAN[index // 2],
            profile=("BlueprintFallback", "Python")[index % 2], authority_inactive_samples=0,
            native_localonly_authority_unchanged=True, foreign_local_owner_observed=False)
        atomic_write(self.root / "observe.json", dict(run_id=self.run, target=peer, index=index, stage="starting"))
        atomic_write(self.root / (peer + "-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        require(time.monotonic() - self.case_started < 24., "held-widget native owner/foreign observation timeout")
        unchanged = all(self.state(value) == self.originals[value] for value in PEERS)
        require(unchanged, "LocalOnly UI/input unexpectedly changed native authority state")
        row["native_localonly_authority_unchanged"] &= unchanged; row["authority_inactive_samples"] += 1
        held = read_json(self.root / (peer + "-held.json"))
        if held is not None:
            require(held["run_id"] == self.run, "foreign held-widget owner state")
            if held["index"] == row["index"]:
                require(held["native_widget_activated"] and held["native_widget_in_original_layer"], "owner did not actually push native UI")
                atomic_write(self.root / "observe.json", dict(run_id=self.run, target=peer, index=row["index"], stage="held"))
                other = next(value for value in PEERS if value != peer)
                passive = read_json(self.root / (other + "-passive.json"))
                if passive is not None:
                    require(passive["run_id"] == self.run, "foreign passive held-widget state")
                    if (passive["target"], passive["index"], passive["stage"]) == (peer, row["index"], "held"):
                        require(passive["native_owner_unchanged"] and passive["native_ability_inactive"] and
                                passive["native_menu_empty"] and passive["native_tasks"] == 0, "foreign local UI/ability changed")
                        row["foreign_local_owner_observed"] = True; row["passive"] = passive
                        atomic_write(self.root / (peer + "-act.json"), dict(run_id=self.run, index=row["index"]))
        ack = read_json(self.root / (peer + "-" + str(row["index"]) + "-ack.json"))
        if ack is None: return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]), "foreign held-widget completion")
        require(row["foreign_local_owner_observed"], "no independent foreign native UI observation")
        row["client"] = ack
        self.report["cases"].append(copy.deepcopy(row)); self.position += 1; self.current = None
        ue.log("UEP_WIDGET_HELD_NETWORK_CASE_OBSERVED " + peer + "/" + str(row["index"]))

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < 480., "held-widget authority barrier timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS) * len(NETWORK_PLAN) * 2:
                    complete = [read_json(self.root / (peer + "-complete.json")) for peer in PEERS]
                    if all(value is not None and value["run_id"] == self.run for value in complete):
                        if not self.released:
                            self.report["original_player_states_restored"] = all(self.state(peer) == self.originals[peer] for peer in PEERS)
                            atomic_write(self.root / "release.json", dict(run_id=self.run)); self.released = True
                        exits = [read_json(self.root / (peer + "-exited.json")) for peer in PEERS]
                        if all(value is not None and value["run_id"] == self.run and value["exit_code"] == 0 for value in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root / "server-status.json", dict(position=self.position, current=self.current,
                native_playing_gate=self.playing_gate, elapsed_seconds=time.monotonic() - self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error: self.report["failed_native_observation"] = copy.deepcopy(self.current)
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_WIDGET_HELD_NETWORK_" + ("FAILED " + error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_WIDGET_HELD_NETWORK_" + self.report["status"].upper())


if any(value.startswith("-UEPWidgetHeldNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPWidgetHeldNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
