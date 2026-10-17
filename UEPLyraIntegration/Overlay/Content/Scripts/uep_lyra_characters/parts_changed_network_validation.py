"""Server native FastArray operations -> two clients' actual part delegates."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import LyraCharacterPart
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.jump_network_validation import Server as PlayingFixture, arg
from uep_lyra_abilities.auto_respawn_helpers_mixin import CLASS as ABILITY
from uep_lyra_world.effect_pad_mixin import valid
from .quickbar_input_network_validation import token
from .inventory_clear_mixin import inventory_state
from .team_cosmetics_validation import DeviceObserver, ActorState, visual
from .outline_validation import path
from .parts_changed_observation import component, parts, part_actors, query, delta, DelegateObserver
from . import parts_changed_mixin as policy, team_cosmetics_mixin as team_policy
from .parts_changed_network_contract import PLAN, require
from .parts_changed_contract import CLASS, TEMP_CLASS

PEERS = ("A", "B0")


def native_actors(world, ids):
    actors, = ue.find_class("GameplayStatics").get_cdo().call_function("GetAllActorsOfClass", world, ue.load_class(CLASS))
    result = {}
    for actor in actors:
        state = actor.get_property("PlayerState")
        if state is not None:
            for peer, player_id in ids.items():
                if int(state.PlayerId) == player_id: result[peer] = actor
    return result


class Context:
    def __init__(self, actors, controllers, server):
        self.actors, self.controllers, self.server = actors, controllers, server
        world = next(iter(actors.values())).get_world()
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
        self.net_mode = str(bridge.call_function("CaptureSnapshot").NetMode)
        self.states = {peer: ActorState(actor) for peer, actor in actors.items()}
        self.original_parts = {peer: parts(actor) for peer, actor in actors.items()}
        self.original_actors = {peer: [path(value) for value in part_actors(actor)] for peer, actor in actors.items()}
        self.inventory = {peer: inventory_state(controller) for peer, controller in controllers.items()}
        cls = next(iter(actors.values())).get_class(); self.cdo, self.cdo_profile = cls.get_cdo(), str(ue.get_mixin_profile(cls.get_cdo()))
        self.startup = {peer: copy.deepcopy(policy.evidence(actor)) for peer, actor in actors.items()}
        self.devices, self.tracking, self.closed = DeviceObserver(), False, False
        self.names = {path(actor): peer for peer, actor in actors.items()}; self.handles, self.spawned = {}, []
        self.delegates = DelegateObserver(actors.values(), self.delivered)

    def delivered(self, key):
        if not self.tracking: return
        # Capture the actual scheduler object in the producer's own multicast,
        # before its one-shot lifetime can end on a later engine tick.
        self.properties[self.names[key]].extend(self.devices.collect(self.marker))
        self.marker = self.devices.markers[-1] if self.devices.markers else None

    def arm(self, profiles):
        self.properties, self.before, self.raw_before, self.team_before = {}, {}, {}, {}
        for peer, actor in self.actors.items():
            ue.set_mixin_profile(actor, profiles[peer])
            self.properties[peer] = []; self.before[peer] = copy.deepcopy(policy.evidence(actor))
            self.raw_before[peer] = self.delegates.count(actor); self.team_before[peer] = copy.deepcopy(team_policy.evidence(actor))
        self.marker = self.devices.marker(); self.tracking = True

    def produce(self, operation):
        for peer, actor in self.actors.items():
            if operation == "add":
                self.handles[peer] = component(actor).call_function("AddCharacterPart", LyraCharacterPart(PartClass=ue.find_class("Actor"))).clone()
            else: component(actor).call_function("RemoveCharacterPart", self.handles[peer])

    def seen(self, operation):
        require(not self.delegates.errors, "independent native delegate observer failed: "+str(self.delegates.errors))
        for peer, actor in self.actors.items():
            expected = 0 if self.server or operation == "remove-again" else 1
            count = self.delegates.count(actor)-self.raw_before[peer]
            require(count <= expected, "native part replication produced duplicate/unexpected delegates")
            temporary = [value for value in part_actors(actor) if value.get_class().get_path_name() == TEMP_CLASS and path(value) not in self.original_actors[peer]]
            if count != expected or len(parts(actor)) != len(self.original_parts[peer])+int(operation == "add") or len(temporary) != int(not self.server and operation == "add"): return False
        return True

    def seal(self):
        self.tracking = False
        require(not self.devices.collect(self.marker), "native device property was not captured in its actual part multicast")

    def devices_done(self):
        return self.devices.markers_removed() and all(self.devices.observed(values) for values in self.properties.values())

    def rows(self, operation, profiles):
        result = {}
        for peer, actor in self.actors.items():
            counters = delta(policy.evidence(actor), self.before[peer], "last_query")
            deliveries = self.delegates.since(actor, self.raw_before[peer]); current = part_actors(actor)
            temporary = [value for value in current if value.get_class().get_path_name() == TEMP_CLASS and path(value) not in self.original_actors[peer]]
            self.spawned.extend(temporary)
            user = actor.call_function("GetPlatformUserId")
            result[peer] = dict(profile=str(ue.get_mixin_profile(actor)), native_operation_called=True, native_callback_count=len(deliveries),
                native_delegate_payload_matches=all(value["component_matches"] and value["owner_matches"] for value in deliveries),
                counters=counters, team_counters=delta(team_policy.evidence(actor), self.team_before[peer], "last_call"),
                last_query=copy.deepcopy(policy.evidence(actor)["last_query"]), native_team_query=query(actor),
                platform_user_valid=bool(ue.find_class("InputDeviceLibrary").get_cdo().call_function("IsValidPlatformId", user)),
                native_role=int(actor.call_function("GetLocalRole")), locally_controlled=bool(actor.call_function("IsLocallyControlled")),
                retained_class=actor.get_class().get_path_name(), part_entries=len(parts(actor)), original_part_entries=len(self.original_parts[peer]),
                temporary_actors=len(temporary), visual=visual(actor), native_device_properties_created=len(self.properties[peer]),
                native_device_properties=self.devices.rows(self.properties[peer]), native_scheduler_removed_owned_properties=True)
        return result

    def cleanup(self):
        if self.closed: return self.cleanup_report
        errors = []
        if self.server:
            for peer, handle in self.handles.items():
                try:
                    if any(row["handle"] == int(handle.PartHandle) for row in parts(self.actors[peer])):
                        component(self.actors[peer]).call_function("RemoveCharacterPart", handle)
                except Exception: errors.append(traceback.format_exc())
        restored = {}
        for peer, actor in self.actors.items():
            try:
                self.states[peer].restore()
                restored[peer] = parts(actor) == self.original_parts[peer] and [path(value) for value in part_actors(actor)] == self.original_actors[peer]
            except Exception: errors.append(traceback.format_exc())
        try: self.delegates.close()
        except Exception: errors.append(traceback.format_exc())
        markers_removed = self.devices.markers_removed()
        try: self.devices.close()
        except Exception: errors.append(traceback.format_exc())
        self.cleanup_report = dict(original_parts_and_visual_profiles_restored=restored,
            original_inventory_restored=all(inventory_state(controller) == self.inventory[peer] for peer, controller in self.controllers.items()),
            cdo_profile_restored=str(ue.get_mixin_profile(self.cdo)) == self.cdo_profile,
            owned_temporary_actors_destroyed=all(not valid(value) for value in self.spawned), delegate_fixture_shutdown=self.delegates.snapshot(),
            native_observation_markers=len(self.devices.markers), native_observation_markers_removed=markers_removed,
            device_roots_created=self.devices.roots_created, device_roots_released=self.devices.roots_released)
        self.closed = True
        if errors: raise RuntimeError("native replicated parts cleanup failed: "+"\n".join(errors))
        return self.cleanup_report


class Peer(Ready):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.root, self.peer, self.run, self.context, self.position, self.complete = Path(result).parent, peer, run, None, 0, False
        self.require_auto_active = self.require_local_playing_phase = False
        self.report.update(peer=peer, run_id=run, network_acceptance=True, native_world_net_mode_observed=True,
            native_part_fastarray_replication=True, gameplay_state_delivered_by_files=False,
            local_part_producer_called=peer == "server", component_delegate_broadcast_by_fixture=False, callback_replayed=False,
            parts_properties_written=False, all_parts_removed_by_fixture=False, pixels_verified=False, hardware_output_tested=False,
            whole_character_migrated=False, full_acceptance=False)

    def status(self):
        atomic_write(self.root/(self.peer+"-status.json"), dict(run_id=self.run, phase=self.phase, position=self.position,
            complete=self.complete, elapsed_seconds=time.monotonic()-self.started))

    def clean(self):
        if self.context is not None: self.report["cleanup"] = self.context.cleanup()
        self.complete = True

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        if not self.complete:
            try: self.clean()
            except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_PARTS_"+("FAILED "+error if error else "NETWORK_READY")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        self.write(); marker = "UEP_CHARACTER_PARTS_"+("NETWORK_" if self.peer == "server" else "SHUTDOWN_")
        (ue.log if self.report["status"] == "passed" else ue.log_error)(marker+self.report["status"].upper())


class Client(Peer):
    def ready(self):
        gate = token(self.root, "playing-ready.json", self.run)
        if gate is not None:
            require(gate["native_playing_phase"], "native parts client bypassed Playing"); Ready.ready(self)

    def begin(self):
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        self.enter("context")

    def setup_context(self):
        plan = token(self.root, "parts-plan.json", self.run)
        if plan is None: return
        actors = native_actors(self.world, plan["player_ids"])
        if set(actors) != set(PEERS) or not all(part_actors(actor) and query(actor)["part_of_team"] for actor in actors.values()): return
        self.context = Context(actors, {self.peer: self.controller}, False)
        self.report.update(player_ids=plan["player_ids"], native_net_mode=self.context.net_mode, natural_startup_python_dispatch=self.context.startup)
        atomic_write(self.root/(self.peer+"-context-ready.json"), dict(run_id=self.run)); self.enter("idle")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360, "native replicated parts client timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "context": self.setup_context()
            elif self.phase == "idle":
                command = token(self.root, "parts-command.json", self.run)
                if command is not None and command["position"] == self.position:
                    self.command = command; self.context.arm(command["profiles"])
                    atomic_write(self.root/(self.peer+"-"+str(self.position)+"-armed.json"), dict(run_id=self.run)); self.enter("replication")
                elif self.position == len(PLAN) and token(self.root, "parts-clean.json", self.run) is not None:
                    self.clean(); self.write(); atomic_write(self.root/(self.peer+"-parts-done.json"), dict(run_id=self.run)); self.enter("release")
            elif self.phase == "replication":
                require(time.monotonic()-self.phase_started < 12, "native part FastArray replication/callback timeout")
                issued = token(self.root, "parts-issued-"+str(self.position)+".json", self.run)
                if issued is not None and time.monotonic()-self.phase_started >= .2 and self.context.seen(self.command["operation"]):
                    self.context.seal(); self.enter("device")
            elif self.phase == "device":
                require(time.monotonic()-self.phase_started < 8, "replicated part callback device scheduler timeout")
                if self.context.devices_done():
                    row = dict(position=self.position, actors=self.context.rows(self.command["operation"], self.command["profiles"]))
                    self.report["cases"].append(row)
                    atomic_write(self.root/(self.peer+"-"+str(self.position)+"-ack.json"), dict(run_id=self.run, row=row))
                    self.position += 1; self.enter("idle")
            elif self.phase == "release" and token(self.root, "parts-release.json", self.run) is not None: self.exit_native()
            self.status(); return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


class Server(Peer):
    def __init__(self, result, run):
        super().__init__(result, "server", run)
        self.fixture = PlayingFixture(result, run); self.fixture.ability_class = ABILITY
        self.report.update(server_waited_for_client_process_exit=False, all_cleanup_frozen_before_release=False)
        self.enter("setup")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360, "native parts authority timeout: "+self.phase)
            if self.phase == "setup":
                if not self.fixture.playing_gate: self.fixture.wait_playing()
                elif not self.fixture.owners: self.fixture.setup()
                elif self.context is None:
                    self.context = Context({peer: value["controller"].get_controlled_pawn() for peer, value in self.fixture.owners.items()},
                        {peer: value["controller"] for peer, value in self.fixture.owners.items()}, True)
                    self.report.update(player_ids=self.fixture.report["player_ids"], native_playing_gate=self.fixture.report["native_playing_gate"],
                        native_net_mode=self.context.net_mode, natural_startup_python_dispatch=self.context.startup)
                    atomic_write(self.root/"parts-plan.json", dict(run_id=self.run, player_ids=self.report["player_ids"]))
                elif all(token(self.root, peer+"-context-ready.json", self.run) is not None for peer in PEERS): self.enter("next")
            elif self.phase == "next":
                if self.position == len(PLAN):
                    self.clean(); atomic_write(self.root/"parts-clean.json", dict(run_id=self.run)); self.enter("cleanup")
                else:
                    name, operation, profiles = PLAN[self.position]
                    self.command = dict(run_id=self.run, position=self.position, name=name, operation=operation, profiles=profiles)
                    self.context.arm(profiles); atomic_write(self.root/"parts-command.json", self.command); self.enter("armed")
            elif self.phase == "armed":
                require(time.monotonic()-self.phase_started < 15, "native parts peer-arm timeout")
                if all(token(self.root, peer+"-"+str(self.position)+"-armed.json", self.run) is not None for peer in PEERS):
                    self.context.produce(self.command["operation"]); require(self.context.seen(self.command["operation"]), "authority part list did not change through native producer")
                    self.context.seal(); self.report["cases"].append(dict(position=self.position, actors=self.context.rows(self.command["operation"], self.command["profiles"])))
                    atomic_write(self.root/("parts-issued-"+str(self.position)+".json"), dict(run_id=self.run)); self.enter("ack")
            elif self.phase == "ack":
                require(time.monotonic()-self.phase_started < 18, "native replicated parts peer-ack timeout")
                if all(token(self.root, peer+"-"+str(self.position)+"-ack.json", self.run) is not None for peer in PEERS):
                    self.position += 1; ue.log("UEP_CHARACTER_PARTS_NETWORK_OPERATION_PASSED "+str(self.position)); self.enter("next")
            elif self.phase == "cleanup":
                if all(token(self.root, peer+"-parts-done.json", self.run) is not None for peer in PEERS):
                    self.report["all_cleanup_frozen_before_release"] = True
                    atomic_write(self.root/"parts-release.json", dict(run_id=self.run)); self.enter("exits")
            elif self.phase == "exits":
                # Controllers may already be destroyed. Only POD exit records.
                exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                if all(value is not None and value["exit_code"] == 0 for value in exits):
                    self.report["server_waited_for_client_process_exit"] = True; self.exit_native()
            self.status(); return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


if any(value.startswith("-UEPCharacterPartsNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterPartsNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
