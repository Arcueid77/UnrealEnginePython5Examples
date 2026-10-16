"""Real Lyra owners: native collision/OnLaunched/physics and received movement."""
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_hud import state as hud_state, weapon_observer
from uep_lyra_hud.shutdown_validation import defer_until_shutdown
from uep_lyra_network_io import atomic_write, read_json
from .effect_pad_network_validation import PadNetworkProbe
from .launcher_observation import LaunchObservation, xyz
from .launcher_network_protocol import PLAN, PEERS, near, require, distance, validate_ack, validate_cases
from . import launcher_mixin as policy
from .effect_pad_mixin import valid

class LauncherNetwork(PadNetworkProbe):
    def __init__(self):
        super().__init__()
        self.timeout_seconds, self.players_restored, self.observer = 600, False, None
        self.current = None
        self.originals = {}
        self.server_restore_evidence = {}
        self.actors_created = self.actors_destroyed = self.scopes_created = self.scopes_closed = 0

    def motion(self):
        if self.player is None or not self._player_ready(self.player) or not self.player["pawn_path"]:
            return None
        pawn = ue.find_object(self.player["pawn_path"])
        return self.pawn_motion(pawn) if valid(pawn) else None

    @staticmethod
    def pawn_motion(pawn):
        movement = pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
        return {"location": xyz(pawn.get_actor_location()), "velocity": xyz(pawn.call_function("GetVelocity")),
            "movement_mode": int(movement.MovementMode)}

    def _status(self):
        result = super()._status()
        result.update(launcher_stage=self.stage, launcher_case=self.index, motion=self.motion())
        return result

    def publish(self, stage):
        packet = dict(self.current, stage=stage)
        if stage == "restored":
            packet["positions"] = self.current["restore_positions"]
        atomic_write(self.root/"launcher-command.json", packet)

    def collect(self, stage):
        rows = {peer: read_json(self.root/"launcher-acks"/(str(self.index)+"-"+stage+"-"+peer+".json")) for peer in PEERS}
        if not all(rows.values()):
            return False
        packet = dict(self.current, positions=self.current["restore_positions"] if stage == "restored" else self.current["positions"])
        for peer in PEERS:
            validate_ack(packet, rows[peer], peer, stage)
        self.current["acks"][stage] = rows
        return True

    def prepare(self, roster):
        self.roster = copy.deepcopy(roster)
        if not self.originals:
            self.classes = [ue.load_class(path) for path in policy.CLASSES]
            for peer, row in roster.items():
                pawn = ue.find_object(row["pawn_path"])
                movement = pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
                self.originals[peer] = {"pawn": pawn, "movement": movement, "location": pawn.get_actor_location(),
                    "mode": int(movement.MovementMode), "custom": int(movement.CustomMovementMode), "health": float(row["health"])}
                movement.call_function("StopMovementImmediately")
                movement.call_function("DisableMovement")
            self.observer = LaunchObservation([row["pawn"] for row in self.originals.values()])
        self.begin()

    def begin(self):
        self.phase_started = time.monotonic()
        target, scenario, profile = PLAN[self.index]
        original = self.originals[target]
        origin, pawn = original["location"], original["pawn"]
        center = ue.FVector(origin.x+6000.0+self.index*1200.0, origin.y, origin.z+1500.0)
        transform = ue.FTransform();transform.translation = center
        cls = self.classes[2 if scenario == "up-vertical" else 1]
        self.stats_before, self.events_before, self.physical = policy.snapshot(), len(self.observer.events), []
        self.pad = ue.find_class("GameplayStatics").get_cdo().call_function("BeginDeferredActorSpawnFromClass", self.world, cls, transform, 1, None)
        require(valid(self.pad), "network launcher spawn failed")
        self.actors_created += 1
        ue.set_mixin_profile(self.pad, profile)
        if scenario.startswith("push"):
            self.pad.set_property("Use Target", scenario == "push-target")
            self.pad.set_property("Target", ue.FVector(150.0, 200.0, -30.0))
        ue.find_class("GameplayStatics").get_cdo().call_function("FinishSpawningActor", self.pad, transform)
        require(self.pad.get_class() == cls and not self.pad.get_property("bReplicates"), "network launcher type/replication changed")
        self.collision = int(self.pad.Sphere.call_function("GetCollisionEnabled"))
        self.pad.Sphere.call_function("SetCollisionEnabled", 0)
        self.scope = SubscriptionScope();self.scopes_created += 1
        self.scope.bind_event(self.pad.Sphere, "OnComponentBeginOverlap", lambda component, actor, *rest:
            self.physical.append("begin") if actor == pawn else None)
        self.scope.bind_event(self.pad.Sphere, "OnComponentEndOverlap", lambda component, actor, *rest:
            self.physical.append("end") if actor == pawn else None)
        require(pawn.set_actor_location(self.pad.Sphere.call_function("K2_GetComponentLocation")), "network launcher baseline teleport failed")
        statuses = {peer: self._peer_status(peer) for peer in PEERS}
        require(all(statuses.values()), "network launcher current peer status missing")
        self.current = {"run_id": self.run_id, "case_index": self.index, "target": target, "scenario": scenario, "profile": profile,
            "roster": copy.deepcopy(self.roster), "acks": {}, "pad_replicates": False,
            "client_pawns": {peer: statuses[peer]["player"]["pawn_path"] for peer in PEERS},
            "client_worlds": {peer: statuses[peer]["player"]["world_token"] for peer in PEERS},
            "positions": {peer: xyz(row["pawn"].get_actor_location()) for peer,row in self.originals.items()}}
        self.launch_position = self.current["positions"][target]
        self.current["launch_position"] = self.launch_position
        self.publish("armed")
        self.stage = "arm-ack"

    def trigger(self):
        target, scenario = self.current["target"], self.current["scenario"]
        pawn = self.originals[target]["pawn"]
        forward = xyz(pawn.call_function("GetActorForwardVector"))
        if scenario == "up-vertical":
            requested = [forward[0], forward[1], float(self.pad.UpOverride)]
        elif scenario == "push-target":
            target_vector = xyz(self.pad.Target);speed = (target_vector[0]**2+target_vector[1]**2)**.5*2.1
            requested = [forward[0]*speed, forward[1]*speed, max(250.0, min(850.0, target_vector[2]*2.0))]
        else:
            requested = [forward[0]*self.pad.Multiplier, forward[1]*self.pad.Multiplier, self.pad.UpOverride*self.pad.Multiplier]
        self.current["expected_requested"] = requested
        self.originals[target]["movement"].call_function("SetMovementMode", 3, 0)
        # Restore the original collision mode. Native overlap generation calls
        # BP/Python business; neither a handler nor LaunchCharacter is replayed.
        self.pad.Sphere.call_function("SetCollisionEnabled", self.collision)
        require(self.physical == ["begin"], "network launcher native begin missing/duplicated")
        events = self.observer.events[self.events_before:]
        require(len(events) == 1 and events[0]["pawn"] == pawn.get_path_name(), "network launcher native OnLaunched missing/cross-owner")
        self.current.update(launch_event=copy.deepcopy(events[0]), launch_event_count=len(events),
            other_owner_launch_events=sum(event["pawn"] != pawn.get_path_name() for event in events))
        require(not policy.snapshot()["errors"], "network launcher Python error: "+repr(policy.snapshot()["errors"]))
        self.stage, self.stage_started = "physics", time.monotonic()

    def restore_trial(self):
        target = self.current["target"]
        row = self.originals[target]
        row["movement"].call_function("StopMovementImmediately")
        row["movement"].call_function("DisableMovement")
        require(row["pawn"].set_actor_location(row["location"]), "network launcher trial restore failed")
        require(self.physical == ["begin", "end"], "network launcher physical lifecycle differs")
        self.scope.close();self.scopes_closed += 1
        self.pad.actor_destroy();self.actors_destroyed += int(not valid(self.pad))
        self.current.update(physical_events=list(self.physical), fixture_scope_closed=self.scope.closed,
            pad_destroyed=not valid(self.pad), restore_positions={peer: xyz(value["location"]) for peer,value in self.originals.items()},
            python_launches=policy.snapshot()["launches"]-self.stats_before["launches"],
            python_cues=policy.snapshot()["cues"]-self.stats_before["cues"])
        self.pad = None
        self.publish("restored");self.stage = "trial-restore-ack"

    def restore(self):
        # Readiness is published only after verified restoration. Clients may
        # disconnect before the server handles release; never touch their now-
        # destroyed Pawns again during the idempotent final finish path.
        if self.peer != "server" or self.players_restored:
            return
        if self.scope is not None and not self.scope.closed:
            self.scope.close();self.scopes_closed += 1
        if valid(self.pad):
            self.pad.actor_destroy();self.actors_destroyed += int(not valid(self.pad));self.pad = None
        try:
            for peer, row in self.originals.items():
                row["movement"].call_function("StopMovementImmediately")
                moved = row["pawn"].set_actor_location(row["location"])
                # Native MoveComponent may return false for an already-equal
                # location. Require the actual postcondition, not movement.
                actual = xyz(row["pawn"].get_actor_location())
                row["movement"].call_function("SetMovementMode", row["mode"], row["custom"])
                health = row["pawn"].get_component_by_type(ue.find_class("LyraHealthComponent"))
                evidence = {"teleport_returned_movement": bool(moved), "location": actual,
                    "expected_location": xyz(row["location"]), "position_error": distance(actual, xyz(row["location"])),
                    "mode": int(row["movement"].MovementMode), "expected_mode": row["mode"],
                    "custom_mode": int(row["movement"].CustomMovementMode), "expected_custom_mode": row["custom"],
                    "health": float(health.call_function("GetHealth")), "expected_health": row["health"]}
                self.server_restore_evidence[peer] = evidence
                require(evidence["position_error"] < .01 and evidence["mode"] == evidence["expected_mode"] and
                        evidence["custom_mode"] == evidence["expected_custom_mode"] and near(evidence["health"], evidence["expected_health"]),
                        "network launcher native player restore postcondition differs: "+repr(evidence))
        finally:
            if self.observer is not None:
                self.observer.close()
        self.players_restored = bool(self.originals)

    def server_tick(self):
        if self.stage == "release":
            release = read_json(self.root/"release.json")
            if release is not None:
                require(release["run_id"] == self.run_id, "foreign launcher release")
                self.finish()
            return
        if self.stage == "complete-ack":
            if all(read_json(self.root/("ready-"+peer+".json")) is not None for peer in PEERS):
                self.stage = "release";atomic_write(self.root/"ready-server.json", {"run_id": self.run_id})
            return
        if self.stage == "ready":
            roster = self._roster(PEERS)
            if roster is not None:
                self.prepare(roster)
            return
        if self.stage == "arm-ack" and self.collect("armed"):
            self.trigger()
        elif self.stage == "physics" and time.monotonic()-self.stage_started > .05:
            motion = self.pawn_motion(self.originals[self.current["target"]]["pawn"])
            if motion["location"][2] <= self.launch_position[2]+.5:
                return
            self.current["server_motion"] = motion
            self.publish("moving");self.stage = "moving-ack"
        elif self.stage == "moving-ack" and self.collect("moving"):
            self.restore_trial()
        elif self.stage == "trial-restore-ack" and self.collect("restored"):
            self.history.append(copy.deepcopy(self.current))
            ue.log("UEP_LAUNCHER_NETWORK_CASE_PASSED "+str(self.index))
            self.index += 1;self.phase_started = time.monotonic()
            if self.index == len(PLAN):
                validate_cases(self.history)
                self.restore()
                atomic_write(self.root/"launcher-command.json", {"run_id": self.run_id, "stage": "complete",
                    "originals": {peer: {"position": xyz(row["location"]), "mode": row["mode"], "health": row["health"]}
                                  for peer,row in self.originals.items()}})
                self.stage = "complete-ack"
            else:
                self.stage = "ready"

    def client_tick(self):
        packet = read_json(self.root/"launcher-command.json")
        if packet is None or self.current_visual is None:
            return
        require(packet["run_id"] == self.run_id, "foreign launcher command")
        motion = self.motion()
        if packet["stage"] == "complete":
            if self.players_restored:
                return  # Readiness is immutable, not a per-frame status file.
            expected = packet["originals"][self.peer]
            if (motion is not None and distance(motion["location"], expected["position"]) < 10.0 and
                    motion["movement_mode"] == expected["mode"] and near(self.player["health"], expected["health"])):
                require(len(self.history) == len(PLAN), "launcher completion before all owner observations")
                self.players_restored = True
                atomic_write(self.root/("ready-"+self.peer+".json"), {"run_id": self.run_id})
            return
        index, stage = packet["case_index"], packet["stage"]
        if index <= self.last_ack or motion is None:
            return
        ack = {"run_id": self.run_id, "case_index": index, "peer": self.peer, "stage": stage,
            "player": copy.deepcopy(self.player), "motion": motion, "health_visual": copy.deepcopy(self.current_visual)}
        try:
            validate_ack(packet, ack, self.peer, stage)
        except RuntimeError:
            return  # Wait for actual native replication, never substitute server data.
        atomic_write(self.root/"launcher-acks"/(str(index)+"-"+stage+"-"+self.peer+".json"), ack)
        if stage == "restored":
            self.history.append(ack);self.last_ack = index

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.restore()
        except Exception:
            error = (error or "")+traceback.format_exc()
        report = {"schema_version": 1, "status": "failed" if error else "passed", "error": error,
            "run_id": self.run_id, "peer": self.peer, "cases": self.history, "players_restored": self.players_restored,
            "actors_created": self.actors_created, "actors_destroyed": self.actors_destroyed,
            "scopes_created": self.scopes_created, "scopes_closed": self.scopes_closed,
            "launch_observer_closed": self.observer is None or self.observer.closed,
            "server_restore_evidence": self.server_restore_evidence,
            "policy": policy.snapshot(), "hud": hud_state.snapshot(), "weapon_observer": weapon_observer.snapshot(),
            "gameplay_slice": {"enabled": False}, "shutdown": None, "elapsed_seconds": self._wall_elapsed(),
            "fixture_server_spawn_teleport_collision_arm": True, "real_lyra_players_tested": True}
        for flag in ("full_acceptance", "packaged_runtime", "pad_replication_forced", "handler_called_by_probe",
                     "launch_called_by_probe", "velocity_or_gravity_written", "attributes_written_by_probe",
                     "physical_client_input_tested", "client_pad_profile_parity_tested", "cue_visual_parity_tested"):
            report[flag] = False
        if error is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        (ue.log_error if error else ue.log)("UEP_LAUNCHER_NETWORK_"+("FAILED "+error if error else "PASSED"))
        self.shutdown_binding();self._request_quit()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            now = time.monotonic()
            require(self._wall_elapsed() < self.timeout_seconds, "launcher network total timeout")
            if now < self.next_tick:
                return True
            self.next_tick = now+.02
            world = self._game_world()
            if not valid(world) or not self._attach(world):
                return True
            self.peer_frame_snapshots.clear()
            self.rows = [self._snapshot_report(row) for row in self.bridge.call_function("CapturePlayerSnapshots")]
            self.player = self.rows[0] if self.peer != "server" and len(self.rows) == 1 else None
            if self.peer == "server":
                self._isolate_bot_combat()
            else:
                self.visual()
            atomic_write(self.root/"status"/(self.peer+".json"), self._status())
            if self.peer == "server":
                limit = 300 if not self.originals else 80
                require(now-self.phase_started < limit, "launcher network case timeout: "+str(self.index)+"/"+self.stage)
                self.server_tick()
            else:
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run_id and self.players_restored and len(self.history) == len(PLAN), "premature launcher release")
                    self.finish()
                else:
                    self.client_tick()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc());return False

runtime = LauncherNetwork()
ticker = ue.add_ticker(runtime.tick)
