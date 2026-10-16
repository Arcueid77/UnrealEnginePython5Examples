"""Two real Inventory Experience owners; native LocalOnly authority stays idle."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from . import widget_pressed_mixin as policy
from .widget_pressed_validation import Validation as NativeUI
from .widget_pressed_contract import NETWORK_PLAN, TARGETS, CLASSES, require
from .widget_held_validation import instances
from .jump_network_validation import arg

PEERS = ("A", "B0")
TRIALS = len(TARGETS) * len(NETWORK_PLAN) * 2


class Client(NativeUI):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root = peer, run, Path(result).parent
        self.plan, self.extras, self.timeout, self.passive_seen = NETWORK_PLAN, False, 480., set()
        self.report.update(peer=peer, run_id=run, passive_held_observations=[], packet_loss_tested=False,
            travel_rejoin_tested=False, gameplay_state_delivered_by_files=False, localonly_ui_replication_claimed=False)

    def idle_state(self):
        return dict(abilities=[dict(path=value.get_path_name(), active=bool(value.get_property("bIsActive")),
            tasks=len(value.get_property("ActiveTasks")), profile=str(ue.get_mixin_profile(value)))
            for values in self.abilities.values() for value in values], menu_active=valid(self.active_layer()), specs=self.specs())

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report.update(player_id=int(self.controller.PlayerState.PlayerId), native_net_mode=str(bridge.call_function("CaptureSnapshot").NetMode),
            native_owner_role=int(self.pawn.call_function("GetLocalRole")))
        require(self.report["native_net_mode"] == "Client" and self.report["native_owner_role"] == 2, "pressed UI owner is not an autonomous native client")
        self.passive_baseline = self.idle_state()
        atomic_write(self.root / (self.peer + "-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        atomic_write(self.root / (self.peer + "-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def may_finish_open(self):
        atomic_write(self.root / (self.peer + "-held.json"), dict(run_id=self.run, peer=self.peer, index=self.index,
            native_widget_active=self.row["native_widget_active"], native_original_layer=self.row["native_original_layer"]))
        value = read_json(self.root / (self.peer + "-act.json"))
        if value is None: return False
        require(value["run_id"] == self.run, "foreign pressed UI action permit")
        return value["index"] == self.index

    def observe_foreign(self):
        if not hasattr(self, "passive_baseline"): return
        request = read_json(self.root / "observe.json")
        if request is None or request["target"] == self.peer: return
        require(request["run_id"] == self.run and request["target"] in PEERS, "foreign pressed UI observation request")
        state = self.idle_state()
        require(state == self.passive_baseline and not state["menu_active"] and all(not row["active"] and row["tasks"] == 0 for row in state["abilities"]),
                "other native client changed this owner's UI/ability/Profile/spec state")
        row = dict(run_id=self.run, peer=self.peer, target=request["target"], index=request["index"], stage=request["stage"],
            player_id=self.report["player_id"], native_owner_unchanged=True, native_menu_empty=True,
            native_ability_count=len(state["abilities"]), native_all_inactive=True, native_profiles_preserved=True, native_specs_preserved=True)
        atomic_write(self.root / (self.peer + "-passive.json"), row)
        key = request["target"], request["index"], request["stage"]
        if request["stage"] == "held" and key not in self.passive_seen:
            self.passive_seen.add(key); self.report["passive_held_observations"].append(row)

    def complete_trial(self):
        atomic_write(self.root / (self.peer + "-" + str(self.index) + "-ack.json"),
            dict(run_id=self.run, peer=self.peer, index=self.index, row=copy.deepcopy(self.row)))
        NativeUI.complete_trial(self)

    def finish(self, error=None):
        if error: return NativeUI.finish(self, error)
        self.passive_baseline = self.idle_state()
        atomic_write(self.root / (self.peer + "-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < self.timeout, "pressed UI owner network timeout")
            self.observe_foreign()
            if self.phase == "network-permit":
                value = read_json(self.root / (self.peer + "-permit.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign pressed UI permit")
                    if value["index"] == self.index: NativeUI.begin(self)
            elif self.phase == "network-complete":
                value = read_json(self.root / "release.json")
                if value is not None:
                    require(value["run_id"] == self.run, "foreign pressed UI release")
                    NativeUI.finish(self)
            else: return NativeUI.tick(self, delta)
            return not self.finished
        except Exception: NativeUI.finish(self, traceback.format_exc()); return False


class Server:
    def __init__(self, result, run):
        self.path, self.root, self.run = Path(result), Path(result).parent, run
        self.started, self.finished, self.position, self.current, self.released = time.monotonic(), False, 0, None, False
        self.owners, self.originals = {}, {}
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        self.report = dict(status="running", error=None, peer="server", run_id=run, cases=[], player_ids={}, native_context_ready=False,
            original_authority_states_restored=False, server_waited_for_client_process_exit=False, full_acceptance=False, packaged_runtime=False,
            physical_input_tested=False, activation_handler_replayed=False, task_callbacks_replayed=False,
            packet_loss_tested=False, travel_rejoin_tested=False, gameplay_state_delivered_by_files=False, localonly_ui_replication_claimed=False)

    def state(self, peer):
        owner = self.owners[peer]
        return dict(abilities=[dict(path=value.get_path_name(), cls=value.get_class().get_path_name(), active=bool(value.get_property("bIsActive")),
            tasks=len(value.get_property("ActiveTasks")), net=int(value.get_property("NetExecutionPolicy")))
            for values in owner["abilities"].values() for value in values], role=int(owner["pawn"].call_function("GetLocalRole")),
            specs=sorted(value.get_path_name() for spec in owner["asc"].get_property("ActivatableAbilities").Items
                for value in list(spec.NonReplicatedInstances) + list(spec.ReplicatedInstances) if valid(value)))

    def setup(self):
        ready = {peer: read_json(self.root / (peer + "-ready.json")) for peer in PEERS}
        if not all(ready.values()): return
        require(all(row["run_id"] == self.run for row in ready.values()) and len({row["player_id"] for row in ready.values()}) == 2, "pressed UI owners are not distinct")
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5) or "L_InventoryTestMap" not in world.get_name(): continue
            controllers, = self.statics.call_function("GetAllActorsOfClass", world, ue.find_class("LyraPlayerController"))
            found = {}
            for controller in controllers:
                if not valid(controller.PlayerState): continue
                for peer, row in ready.items():
                    if int(controller.PlayerState.PlayerId) != row["player_id"]: continue
                    pawn = controller.get_controlled_pawn()
                    if not valid(pawn): continue
                    asc = ability_system(pawn)
                    if not valid(asc): continue
                    abilities = {target: instances(asc, ue.load_class(path)) for target, path in CLASSES.items()}
                    if not all(len(values) == 2 for values in abilities.values()): continue
                    found[peer] = dict(controller=controller, pawn=pawn, asc=asc, abilities=abilities)
            if set(found) == set(PEERS):
                self.world, self.owners = world, found
                self.originals = {peer: self.state(peer) for peer in PEERS}
                require(all(row["role"] == 3 and all(not value["active"] and value["tasks"] == 0 and value["net"] == 1 for value in row["abilities"])
                            for row in self.originals.values()), "native LocalOnly authority context differs")
                self.report.update(player_ids={peer: ready[peer]["player_id"] for peer in PEERS}, native_context_ready=True,
                    native_authority_initial_states=copy.deepcopy(self.originals))
                return

    def start_case(self):
        peer, index = PEERS[self.position // TRIALS], self.position % TRIALS
        value = read_json(self.root / (peer + "-request.json"))
        if value is None or value["index"] != index: return
        require(value["run_id"] == self.run, "foreign pressed UI request")
        self.case_started = time.monotonic()
        self.current = dict(target=peer, index=index, ui_target=TARGETS[index // (len(NETWORK_PLAN) * 2)],
            name=NETWORK_PLAN[(index // 2) % len(NETWORK_PLAN)], profile=("BlueprintFallback", "Python")[index % 2],
            authority_inactive_samples=0, native_authority_unchanged=True, foreign_local_owner_observed=False)
        atomic_write(self.root / "observe.json", dict(run_id=self.run, target=peer, index=index, stage="starting"))
        atomic_write(self.root / (peer + "-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        require(time.monotonic() - self.case_started < 24., "pressed UI owner/foreign/authority observation timeout")
        require(all(self.state(value) == self.originals[value] for value in PEERS), "LocalOnly UI changed native authority/spec state")
        row["authority_inactive_samples"] += 1
        held = read_json(self.root / (peer + "-held.json"))
        if held is not None:
            require(held["run_id"] == self.run, "foreign pressed UI held report")
            if held["index"] == row["index"]:
                require(held["native_widget_active"] and held["native_original_layer"], "native owner UI not actually active")
                atomic_write(self.root / "observe.json", dict(run_id=self.run, target=peer, index=row["index"], stage="held"))
                other = next(value for value in PEERS if value != peer)
                passive = read_json(self.root / (other + "-passive.json"))
                if passive is not None:
                    require(passive["run_id"] == self.run, "foreign pressed UI passive report")
                    if (passive["target"], passive["index"], passive["stage"]) == (peer, row["index"], "held"):
                        require(passive["native_owner_unchanged"] and passive["native_menu_empty"] and passive["native_all_inactive"] and
                                passive["native_profiles_preserved"] and passive["native_specs_preserved"] and passive["native_ability_count"] == 4, "foreign local owner changed")
                        row["foreign_local_owner_observed"], row["passive"] = True, passive
                        atomic_write(self.root / (peer + "-act.json"), dict(run_id=self.run, index=row["index"]))
        ack = read_json(self.root / (peer + "-" + str(row["index"]) + "-ack.json"))
        if ack is None: return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]) and row["foreign_local_owner_observed"], "foreign/incomplete pressed UI acknowledgement")
        row["client"] = ack; self.report["cases"].append(copy.deepcopy(row)); self.current = None; self.position += 1
        ue.log("UEP_WIDGET_PRESSED_NETWORK_CASE_OBSERVED " + peer + "/" + str(row["index"]))

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < 480., "pressed UI network total timeout")
            if not self.owners: self.setup()
            elif self.position == len(PEERS) * TRIALS:
                complete = [read_json(self.root / (peer + "-complete.json")) for peer in PEERS]
                if all(row is not None and row["run_id"] == self.run for row in complete):
                    if not self.released:
                        self.report["original_authority_states_restored"] = all(self.state(peer) == self.originals[peer] for peer in PEERS)
                        atomic_write(self.root / "release.json", dict(run_id=self.run)); self.released = True
                    exits = [read_json(self.root / (peer + "-exited.json")) for peer in PEERS]
                    if all(row is not None and row["run_id"] == self.run and row["exit_code"] == 0 for row in exits):
                        self.report["server_waited_for_client_process_exit"] = True; self.finish()
            elif self.current is None: self.start_case()
            else: self.observe()
            atomic_write(self.root / "server-status.json", dict(position=self.position, current=self.current,
                native_context_ready=bool(self.owners), elapsed_seconds=time.monotonic() - self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error: self.report["failed_native_observation"] = copy.deepcopy(self.current)
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_WIDGET_PRESSED_NETWORK_" + ("FAILED " + error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_WIDGET_PRESSED_NETWORK_" + self.report["status"].upper())


if any(value.startswith("-UEPWidgetPressedNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPWidgetPressedNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
