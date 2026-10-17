"""Native authority grants replicate; client BP calls are true remote no-ops."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, arg
from uep_lyra_abilities.auto_respawn_helpers_mixin import CLASS as ABILITY
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from .quickbar_input_network_validation import token
from .quickbar_input_validation import fingerprint
from .initial_inventory_validation import Trial, state
from .initial_inventory_contract import PLAN, require, expected
from .initial_inventory_network_contract import server_gate, client_gate
from . import initial_inventory_mixin as policy

PEERS = ("A", "B0")


class Client(Ready):
    trial_type = Trial
    marker = "UEP_CHARACTER_LOADOUT"
    validate_report = staticmethod(client_gate)
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.root, self.peer, self.run, self.trial = Path(result).parent, peer, run, None
        self.require_auto_active = self.require_local_playing_phase = False
        self.scope, self.closed = None, False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, local_inventory_written=False, gameplay_state_delivered_by_files=False,
            whole_character_migrated=False, signal_payload_owner_claimed=False, native_inventory_signals=[],
            inventory_observers=dict(created=0, closed=0, active=0), foreign_turn_own_inventory_unchanged=True,
            original_inventory_identities_restored=False, profile_configuration_cdo_restored=False)

    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is None: return
        require(gate["native_playing_phase"], "loadout owner bypassed actual native Playing")
        self.report["authority_phase_gate_observed"] = True; super().ready()

    def replica(self):
        try: return state(self.controller)
        except Exception:
            self.report["last_replica_readiness_error"] = traceback.format_exc(); return None

    def begin(self):
        if self.replica() is None: return
        self.trial = self.trial_type(self.controller)
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report.update(player_id=int(self.controller.PlayerState.PlayerId), native_role=int(self.pawn.call_function("GetLocalRole")),
            native_net_mode=str(bridge.call_function("CaptureSnapshot").NetMode), natural_remote_startup=copy.deepcopy(policy.evidence(self.pawn)))
        self.scope = SubscriptionScope(); self.report["inventory_observers"].update(created=1, active=1)
        for channel in ("Lyra.QuickBar.Message.SlotsChanged", "Lyra.Inventory.Message.StackChanged"):
            self.scope.listen_gameplay_signal(self.pawn, channel, lambda tag: self.report["native_inventory_signals"].append(str(tag.TagName)))
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        self.enter("trial")

    def observe(self):
        command = token(self.root, "trial.json", self.run)
        if command is None: return
        if command["peer"] != self.peer:
            self.report["foreign_turn_own_inventory_unchanged"] &= fingerprint(self.controller) == self.trial.original
            require(self.report["foreign_turn_own_inventory_unchanged"], "foreign authority loadout changed this owner's inventory")
            return
        if command["index"] != self.index or self.replica() != expected(self.index): return
        name, profile, definitions, occupied = PLAN[self.index]
        ue.set_mixin_profile(self.pawn, profile)
        before = copy.deepcopy(policy.evidence(self.pawn)); native_before = fingerprint(self.controller)
        self.trial.probe.call_function("Grant", self.pawn)
        after = policy.evidence(self.pawn)
        added = [value.ItemDef.get_path_name() for value in self.trial.inventory.call_function("GetAllItems") if value.get_path_name() not in self.trial.original["items"]]
        ue.set_mixin_profile(self.pawn, self.trial.profile)
        row = dict(index=self.index, name=name, profile=profile, replica_model=self.replica(),
            native_role=int(self.pawn.call_function("GetLocalRole")), native_authority=bool(self.pawn.call_function("HasAuthority")), bp_reference_call=True,
            native_inventory_before_after_unchanged=fingerprint(self.controller) == native_before,
            original_item_retained=all(value in self.trial.inventory.call_function("GetAllItems") for value in self.trial.original_items),
            added_definitions=sorted(added), profile_configuration_cdo_restored=self.fields_restored(),
            counters={key: after[key]-before[key] for key in after if key != "last_call"})
        self.augment_row(row)
        self.report["cases"].append(row)
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, row=copy.deepcopy(row)))
        self.enter("restore")

    def augment_row(self, row): pass

    def fields_restored(self):
        return str(ue.get_mixin_profile(self.pawn)) == self.trial.profile and list(self.pawn.get_property("InitialInventoryItems")) == self.trial.configuration and self.trial.cdo_state() == self.trial.cdo_before

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 400, "loadout client timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "trial": self.observe()
            elif self.phase == "restore":
                restored = token(self.root, "restored.json", self.run)
                if restored is not None and (restored["peer"], restored["index"]) == (self.peer, self.index) and (
                        fingerprint(self.controller) == self.trial.original and self.replica() == self.trial.original_model):
                    atomic_write(self.root/(self.peer+"-"+str(self.index)+"-restored.json"), dict(run_id=self.run))
                    self.index += 1; self.enter("complete" if self.index == len(PLAN) else "trial")
            else:
                self.report["foreign_turn_own_inventory_unchanged"] &= fingerprint(self.controller) == self.trial.original
                require(self.report["foreign_turn_own_inventory_unchanged"], "other owner's loadout changed completed client's inventory")
                if token(self.root, "release.json", self.run) is not None:
                    self.report["original_inventory_identities_restored"] = fingerprint(self.controller) == self.trial.original and self.replica() == self.trial.original_model
                    self.report["profile_configuration_cdo_restored"] = self.fields_restored(); self.finish()
            atomic_write(self.root/(self.peer+"-status.json"), dict(run_id=self.run, phase=self.phase, index=self.index,
                elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if self.scope is not None:
            try: self.scope.close(); self.report["inventory_observers"].update(closed=1, active=0)
            except Exception: error = (error or "")+traceback.format_exc()
            self.scope = None
        if self.trial is not None: ue.set_mixin_profile(self.pawn, self.trial.profile)
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)(self.marker+"_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; self.validate_report(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)(self.marker+"_SHUTDOWN_"+self.report["status"].upper())


class Server:
    trial_type = Trial
    marker = "UEP_CHARACTER_LOADOUT"
    validate_report = staticmethod(server_gate)
    def __init__(self, result, run):
        self.path, self.root, self.run = Path(result), Path(result).parent, run
        self.fixture = PlayingFixture(result, run); self.fixture.ability_class = ABILITY
        self.started, self.finished, self.position, self.current = time.monotonic(), False, 0, None
        self.trials = {}; self.phase = "grant"
        self.release_started = False
        self.report = dict(status="running", error=None, run_id=run, cases=[], natural_startup_grants={},
            server_waited_for_client_process_exit=False, all_original_inventory_identities_restored=False,
            gameplay_state_delivered_by_files=False, inventory_properties_written=False, whole_character_migrated=False,
            full_acceptance=False, restore_frozen_before_release=False)

    def setup(self):
        self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"])
        for peer, owner in self.fixture.owners.items():
            self.report["natural_startup_grants"][peer] = copy.deepcopy(policy.evidence(owner["pawn"]))
            self.trials[peer] = self.trial_type(owner["controller"])

    def start_trial(self):
        peer, index = PEERS[self.position//len(PLAN)], self.position % len(PLAN)
        self.current = self.trials[peer].execute(index)
        self.current.update(peer=peer, index=index, authority_role=int(self.trials[peer].pawn.call_function("GetLocalRole")), other_authority_owner_unchanged=True)
        self.foreign = {name: fingerprint(value.controller) for name, value in self.trials.items() if name != peer}
        self.case_started = time.monotonic(); self.phase = "grant"
        atomic_write(self.root/"trial.json", dict(run_id=self.run, peer=peer, index=index))

    def observe(self):
        row = self.current; peer, index = row["peer"], row["index"]
        for name, original in self.foreign.items(): row["other_authority_owner_unchanged"] &= fingerprint(self.trials[name].controller) == original
        require(row["other_authority_owner_unchanged"], "authority loadout changed foreign owner's native inventory")
        require(time.monotonic()-self.case_started < 20, "loadout owner replica/undo acknowledgement timeout: "+self.phase)
        if self.phase == "grant":
            ack = token(self.root, peer+"-"+str(index)+"-ack.json", self.run)
            if ack is None: return
            require(state(self.trials[peer].controller) == row["native_model"], "native authority loadout changed before acknowledgement")
            row["owner_observation"] = ack["row"]; row.update(self.trials[peer].restore()); self.phase = "restore"
            atomic_write(self.root/"restored.json", dict(run_id=self.run, peer=peer, index=index))
        elif token(self.root, peer+"-"+str(index)+"-restored.json", self.run) is not None:
            self.report["cases"].append(copy.deepcopy(row)); self.current = None; self.position += 1
            ue.log(self.marker+"_NETWORK_CASE_PASSED "+peer+"/"+str(index))

    def release_clients(self):
        if not self.release_started:
            # Verify while native owners still exist, then publish one-way
            # release. Disconnect destroys these objects; never reread them.
            restored = all(fingerprint(value.controller) == value.original and state(value.controller) == value.original_model for value in self.trials.values())
            require(restored, "loadout native originals differ before client release")
            self.report.update(all_original_inventory_identities_restored=True, restore_frozen_before_release=True)
            self.release_started = True
            atomic_write(self.root/"release.json", dict(run_id=self.run))
        exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
        if all(value is not None and value["exit_code"] == 0 for value in exits):
            self.report["server_waited_for_client_process_exit"] = True; self.finish()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 400, "loadout authority timeout")
            if not self.fixture.playing_gate: self.fixture.wait_playing()
            elif not self.fixture.owners: self.fixture.setup()
            elif not self.trials: self.setup()
            else:
                isolate_bots(self.fixture.statics, self.fixture.world, ue.find_class("LyraPlayerBotController"))
                if self.position == 2*len(PLAN):
                    self.release_clients()
                elif self.current is None: self.start_trial()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(run_id=self.run, position=self.position, phase=self.phase,
                native_playing_gate=self.fixture.playing_gate, current=self.current, elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and not self.release_started:
            for value in self.trials.values():
                try: value.restore()
                except Exception: error += traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)(self.marker+"_NETWORK_READY" if not error else error); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; self.validate_report(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        atomic_write(self.path, self.report); (ue.log if self.report["status"] == "passed" else ue.log_error)(self.marker+"_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPCharacterLoadoutNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterLoadoutNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
