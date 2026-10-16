"""Native server parts -> retained FastArray -> two real child-actor viewers."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, arg, PEERS
from . import cosmetics_mixin as policy
from .cosmetic_validation import Validation as NativeParts
from .cosmetic_state import capture
from .cosmetic_contract import require


def base_report(peer, run):
    return dict(schema_version=1, status="running", error=None, peer=peer, run_id=run, cases=[],
        full_acceptance=False, packaged_runtime=False, animation_assets_modified=False,
        part_arrays_written=False, part_actors_spawned_by_python=False, native_replication_bypassed=False,
        beginplay_handler_replayed=False, rng_seed_or_result_written=False, packet_loss_tested=False,
        travel_rejoin_tested=False)


class Server(NativeParts):
    def __init__(self, result, run):
        super().__init__(result)
        self.root, self.run, self.position, self.owner_index = Path(result).parent, run, 0, 0
        self.fixture, self.phase, self.require_actors = PlayingFixture(result, run), "setup", False
        self.network = base_report("server", run)
        self.network.update(owners={}, server_waited_for_client_process_exit=False)

    def setup_owner(self):
        self.peer = PEERS[self.owner_index]
        self.world = self.fixture.world; self.controller = self.fixture.owners[self.peer]["controller"]
        self.pawn = self.controller.get_controlled_pawn()
        self.original, self.index, self.sides = capture(self.pawn), 0, []
        self.report = dict(cases=[], random_trials=[], original_player_restored=False)
        self.begin()

    def begin(self):
        self.other = self.fixture.owners[PEERS[1] if self.peer == PEERS[0] else PEERS[0]]["controller"].get_controlled_pawn()
        self.other_before = capture(self.other)
        atomic_write(self.root/"arm.json", dict(run_id=self.run, position=self.position, target=self.peer,
            index=self.index, player_id=self.fixture.owners[self.peer]["player_id"]))
        self.enter("armed")

    def part_presented(self):
        self.row.update(position=self.position, target=self.peer, index=self.index)
        atomic_write(self.root/"present.json", dict(run_id=self.run, position=self.position, chosen_class=self.row["chosen_class"]))
        self.enter("present")

    def record_trial(self, row):
        self.network["cases"].append(copy.deepcopy(row)); self.position += 1

    def finish(self, error=None):
        if error: return self.exit_native(error)
        self.network["owners"][self.peer] = copy.deepcopy(self.report)
        if self.owner_index == 0:
            self.owner_index = 1; self.setup_owner()
        else: self.enter("release")

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if valid(self.component): self.component.call_function("K2_DestroyComponent", self.controller)
        except Exception: error = (error or "")+traceback.format_exc()
        self.network.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.network)
        (ue.log_error if error else ue.log)("UEP_COSMETIC_NETWORK_AUTHORITY_"+("FAILED "+error if error else "READY"))
        ue.request_exit()

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native cosmetic server timeout: "+self.phase)
            if self.phase == "setup":
                if not self.fixture.playing_gate: self.fixture.wait_playing()
                elif not self.fixture.owners: self.fixture.setup()
                else:
                    self.network.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"])
                    self.setup_owner()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.phase in ("armed", "present", "removed"):
                    require(time.monotonic()-self.phase_started < 20., "native cosmetic peer barrier timeout: "+self.phase)
                    suffix = {"armed": "armed", "present": "presented", "removed": "removed"}[self.phase]
                    rows = [read_json(self.root/(peer+"-"+suffix+".json")) for peer in PEERS]
                    acknowledged = all(row is not None and (row["run_id"], row["position"]) == (self.run, self.position) for row in rows)
                    if acknowledged:
                        if self.phase == "armed": NativeParts.begin(self)
                        elif self.phase == "present":
                            self.component.call_function("K2_DestroyComponent", self.controller); self.component = None
                            atomic_write(self.root/"remove.json", dict(run_id=self.run, position=self.position))
                            self.enter("removed")
                        else:
                            self.row["other_owner_unchanged"] = capture(self.other) == self.other_before
                            require(self.row["other_owner_unchanged"], "native cosmetic change leaked to other owner")
                            NativeParts.removed(self)
                elif self.phase == "added": NativeParts.added(self)
                elif self.phase == "release":
                    atomic_write(self.root/"release.json", dict(run_id=self.run, trials=self.position))
                    rows = [read_json(self.root/(peer+"-exited.json")) for peer in PEERS]
                    if all(row is not None and row["exit_code"] == 0 for row in rows):
                        self.network["server_waited_for_client_process_exit"] = True; self.exit_native()
            atomic_write(self.root/"server-status.json", dict(position=self.position, phase=self.phase,
                owner=PEERS[self.owner_index], elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False

    def finalize(self):
        self.network["policy_shutdown"] = policy.snapshot()
        if self.network["status"] == "awaiting_shutdown": self.network["status"] = "passed"
        atomic_write(self.path, self.network)
        (ue.log if self.network["status"] == "passed" else ue.log_error)("UEP_COSMETIC_NETWORK_"+self.network["status"].upper())


class Client:
    def __init__(self, result, peer, run):
        self.path, self.root, self.peer, self.run = Path(result), Path(result).parent, peer, run
        self.started, self.finished, self.phase, self.position = time.monotonic(), False, "ready", -1
        self.scope, self.created, self.closed = None, 0, 0
        self.report = base_report(peer, run)
        self.statics = ue.find_class("GameplayStatics").get_cdo()

    def find_pawn(self, player_id):
        pawns, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraCharacter"))
        values = [pawn for pawn in pawns if valid(pawn) and valid(pawn.PlayerState) and int(pawn.PlayerState.PlayerId) == player_id]
        return values[0] if len(values) == 1 else None

    def ready(self):
        gate = read_json(self.root/"playing-ready.json")
        if gate is None: return
        require(gate["run_id"] == self.run, "foreign cosmetic native Playing gate")
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bHealthReady and snap.Health > 0 and not snap.bDamageImmune): continue
            require(str(snap.NetMode) == "Client", "cosmetic viewer is not a native network client")
            self.world = world
            controller = self.statics.call_function("GetPlayerController", world, 0)
            self.report["player_id"] = int(controller.PlayerState.PlayerId)
            atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
            self.phase = "idle"; return

    def arm(self, command):
        require(command["run_id"] == self.run and command["position"] == self.position+1, "foreign/out-of-order cosmetic trial")
        pawn = self.find_pawn(command["player_id"])
        if not valid(pawn): return
        baseline = capture(pawn)
        if not baseline or any(row["actor"] is None for row in baseline): return
        self.position, self.command, self.pawn, self.baseline = command["position"], command, pawn, baseline
        self.native_events = 0
        customizer = pawn.get_component_by_type(ue.find_class("LyraPawnComponent_CharacterParts"))
        self.scope = SubscriptionScope(); self.created += 1
        def changed(component):
            require(component == customizer, "native cosmetic delegate delivered wrong owner")
            self.native_events += 1
        self.scope.bind_event(customizer, "OnCharacterPartsChanged", changed)
        self.phase, self.trial_started = "present", time.monotonic()
        atomic_write(self.root/(self.peer+"-armed.json"), dict(run_id=self.run, position=self.position))

    def present(self):
        value = read_json(self.root/"present.json")
        if value is None or value["position"] != self.position: return
        require(value["run_id"] == self.run, "foreign native cosmetic presentation gate")
        native = capture(self.pawn)
        original = {row["actor"] for row in self.baseline}
        added = [row for row in native if row["actor"] and row["actor"] not in original]
        if len(added) != 1 or len(native) != len(self.baseline)+1 or self.native_events < 1: return
        require(added[0]["cls"] == value["chosen_class"], "native FastArray delivered wrong cosmetic class")
        self.row = dict(position=self.position, target=self.command["target"], index=self.command["index"],
            pawn=self.pawn.get_path_name(), native_part=added[0], native_add_delegate_seen=True,
            native_cleanup_restored_original_ids=False)
        atomic_write(self.root/(self.peer+"-presented.json"), dict(run_id=self.run, position=self.position))
        self.phase = "removed"

    def removed(self):
        value = read_json(self.root/"remove.json")
        if value is None or value["position"] != self.position: return
        require(value["run_id"] == self.run, "foreign native cosmetic removal gate")
        if capture(self.pawn) != self.baseline or self.native_events < 2: return
        self.row.update(native_cleanup_restored_original_ids=True, native_delegate_deliveries=self.native_events)
        self.scope.close(); self.scope = None; self.closed += 1
        self.report["cases"].append(copy.deepcopy(self.row))
        atomic_write(self.root/(self.peer+"-removed.json"), dict(run_id=self.run, position=self.position))
        self.phase = "idle"

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native cosmetic viewer timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase in ("present", "removed"):
                require(time.monotonic()-self.trial_started < 25., "native FastArray/body/delegate rollback timeout: "+self.phase)
                (self.present if self.phase == "present" else self.removed)()
            else:
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run and release["trials"] == len(self.report["cases"]), "native cosmetic release incomplete")
                    self.finish(); return False
                command = read_json(self.root/"arm.json")
                if command is not None and command["position"] > self.position: self.arm(command)
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if self.scope is not None: self.scope.close(); self.scope = None; self.closed += 1
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
            observer_scopes_created=self.created, observer_scopes_closed=self.closed)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_COSMETIC_NETWORK_VIEWER_"+("FAILED "+error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_COSMETIC_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPCosmeticNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCosmeticNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
