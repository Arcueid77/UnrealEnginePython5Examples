"""Existing server/replica identity protocol, with readiness ingress evidence."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities.jump_network_validation import arg
from .initial_inventory_network_validation import Client as LoadoutClient, Server as LoadoutServer
from .inventory_ready_observation import Trial
from .inventory_ready_network_contract import client_gate, server_gate
from . import inventory_ready_mixin as policy
from . import initial_inventory_mixin as loadout
from .initial_inventory_network_validation import token, fingerprint, PLAN, expected, state, require, atomic_write
from .outline_validation import gc
from uep_lyra_world.effect_pad_mixin import valid


def scope_fields(report):
    report.update(experience_callback_manually_called_by_typed_bp=False, native_experience_factory_signal_tested=True, experience_ready_factory_migrated=False,
        pending_inventory_wait_migrated=False, immediate_inventory_ready_branch_migrated=True)


class Client(LoadoutClient):
    trial_type = Trial
    marker = "UEP_CHARACTER_READY"
    validate_report = staticmethod(client_gate)

    def __init__(self, *args): super().__init__(*args); scope_fields(self.report); self.collection_started = None

    def begin(self):
        super().begin()
        if self.trial is not None: self.report["natural_startup_readiness"] = copy.deepcopy(policy.evidence(self.pawn))

    def observe(self):
        command = token(self.root, "trial.json", self.run)
        if command is None: return
        if command["peer"] != self.peer:
            self.report["foreign_turn_own_inventory_unchanged"] &= fingerprint(self.controller) == self.trial.original
            require(self.report["foreign_turn_own_inventory_unchanged"], "ready foreign turn changed own inventory"); return
        if command["index"] != self.index or self.replica() != expected(self.index): return
        _, profile, _, _ = PLAN[self.index]
        ue.set_mixin_profile(self.pawn, profile); self.remote_before = fingerprint(self.controller)
        self.trial.probe.call_function("Grant", self.pawn); self.enter("callback")

    def observe_callback(self):
        if not self.trial.probe.capture(self.pawn): return
        name, profile, definitions, _ = PLAN[self.index]
        after = loadout.evidence(self.pawn); before = self.trial.probe.before_loadout
        added = [value.ItemDef.get_path_name() for value in self.trial.inventory.call_function("GetAllItems") if value.get_path_name() not in self.trial.original["items"]]
        ue.set_mixin_profile(self.pawn, self.trial.profile)
        row = dict(index=self.index, name=name, profile=profile, replica_model=self.replica(), native_role=int(self.pawn.call_function("GetLocalRole")),
            native_authority=bool(self.pawn.call_function("HasAuthority")), bp_reference_call=True, real_experience_factory_signal=True,
            native_inventory_before_after_unchanged=fingerprint(self.controller) == self.remote_before,
            original_item_retained=all(value in self.trial.inventory.call_function("GetAllItems") for value in self.trial.original_items), added_definitions=sorted(added),
            profile_configuration_cdo_restored=self.fields_restored(), counters={key: after[key]-before[key] for key in after if key != "last_call"},
            readiness_counters=copy.deepcopy(self.trial.last_ready_delta))
        self.report["cases"].append(row); atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, row=copy.deepcopy(row))); self.enter("restore")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 400, "native ready owner timeout: "+self.phase)
            if self.phase == "callback":
                self.observe_callback(); atomic_write(self.root/(self.peer+"-status.json"), dict(run_id=self.run, phase=self.phase, index=self.index)); return True
            if self.phase == "complete" and self.collection_started is None: gc(); self.collection_started = time.monotonic()
            if self.phase == "complete" and "owned_experience_proxies_collected" not in self.report:
                if time.monotonic()-self.collection_started < .2: return True
                self.report.update(owned_experience_proxies_created=len(self.trial.probe.owned), owned_experience_proxies_collected=self.trial.probe.collected())
            return super().tick(seconds)
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        if self.trial is not None: self.report["caller_roots"] = self.trial.close_probe()
        super().finish(error)


class Server(LoadoutServer):
    trial_type = Trial
    marker = "UEP_CHARACTER_READY"
    validate_report = staticmethod(server_gate)

    def __init__(self, *args): super().__init__(*args); scope_fields(self.report); self.collection_started = None

    def setup(self):
        super().setup()
        self.report["natural_startup_readiness"] = {peer: copy.deepcopy(policy.evidence(value.pawn)) for peer, value in self.trials.items()}
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.fixture.world)
        self.report["native_net_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)

    def close_probes(self):
        rows = [value.close_probe() for value in self.trials.values()]
        self.report["caller_roots"] = {key: sum(row[key] for row in rows) for key in ("created", "released")}

    def observe(self):
        # Once restoration starts the measured grant is immutable evidence.
        # Never replace it with a new snapshot of the restored inventory.
        if self.phase == "grant" and not self.trials[self.current["peer"]].capture(): return
        super().observe()

    def release_clients(self):
        if not self.release_started:
            if self.collection_started is None: gc(); self.collection_started = time.monotonic(); return
            if time.monotonic()-self.collection_started < .2: return
            self.report.update(owned_experience_proxies_created=sum(len(value.probe.owned) for value in self.trials.values()),
                owned_experience_proxies_collected=all(value.probe.collected() for value in self.trials.values()))
            self.close_probes()
        super().release_clients()

    def finish(self, error=None):
        if self.finished: return
        if error and not self.release_started: self.close_probes()
        super().finish(error)


if any(value.startswith("-UEPCharacterReadyNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterReadyNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
