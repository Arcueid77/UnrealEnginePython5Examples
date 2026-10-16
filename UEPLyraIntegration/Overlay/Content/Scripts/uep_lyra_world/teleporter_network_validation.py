"""Server collision -> teleporter policy -> actual owner replication (2 clients)."""
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
from .teleporter_network_protocol import PLAN, PEERS, near, require, distance, validate_ack, validate_cases
from . import teleporter_mixin as policy
from .effect_pad_mixin import valid


def angles(value):
    return [float(getattr(value, k)) for k in ("pitch", "yaw", "roll")]


def angle_error(a, b):
    return max(abs((x-y+180.) % 360.-180.) for x, y in zip(a, b))


class TeleporterNetwork(PadNetworkProbe):
    def __init__(self):
        super().__init__()
        self.timeout_seconds, self.players_restored, self.observer = 600, False, None
        self.originals, self.server_restore_evidence, self.portals = {}, {}, []
        self.current = None
        self.actors_created = self.actors_destroyed = self.scopes_created = self.scopes_closed = 0

    @staticmethod
    def pawn_motion(pawn):
        movement = pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
        return dict(location=xyz(pawn.get_actor_location()), velocity=xyz(pawn.call_function("GetVelocity")),
                    movement_mode=int(movement.MovementMode))

    def motion(self):
        if self.player is None or not self._player_ready(self.player) or not self.player["pawn_path"]:
            return None
        pawn = ue.find_object(self.player["pawn_path"])
        return self.pawn_motion(pawn) if valid(pawn) else None

    def _status(self):
        result = super()._status()
        result.update(teleporter_stage=self.stage, teleporter_case=self.index, motion=self.motion())
        return result

    def publish(self, stage):
        packet = dict(self.current, stage=stage)
        if stage == "restored":
            packet["positions"] = self.current["restore_positions"]
        atomic_write(self.root/"teleporter-command.json", packet)

    def collect(self, stage):
        rows = {peer: read_json(self.root/"teleporter-acks"/(str(self.index)+"-"+stage+"-"+peer+".json")) for peer in PEERS}
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
            self.cls = ue.load_class(policy.CLASS)
            for peer, row in roster.items():
                pawn = ue.find_object(row["pawn_path"])
                movement = pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
                controller = pawn.call_function("GetController")
                self.originals[peer] = dict(pawn=pawn, movement=movement, controller=controller,
                    location=pawn.get_actor_location(), rotation=pawn.get_actor_rotation(), aim=controller.call_function("GetControlRotation"),
                    mode=int(movement.MovementMode), custom=int(movement.CustomMovementMode), health=float(row["health"]))
                movement.call_function("StopMovementImmediately"); movement.call_function("DisableMovement")
            self.observer = LaunchObservation([row["pawn"] for row in self.originals.values()])
        self.begin()

    @staticmethod
    def yaw(value):
        result = ue.FRotator(); result.yaw = value
        return result

    def spawn_portal(self, position, receiver, profile, scenario):
        statics = ue.find_class("GameplayStatics").get_cdo()
        transform = ue.FTransform(); transform.translation = position
        portal = statics.call_function("BeginDeferredActorSpawnFromClass", self.world, self.cls, transform, 1, None)
        require(valid(portal), "network portal spawn failed")
        self.portals.append(portal); self.actors_created += 1
        ue.set_mixin_profile(portal, profile)
        portal.set_property("ReceiverOnly", receiver)
        portal.set_property("LaunchOnTeleport", scenario != "no-launch")
        portal.set_property("KeepReleativeEntryUponExit", scenario == "relative-offset")
        statics.call_function("FinishSpawningActor", portal, transform)
        portal.set_actor_rotation(self.yaw(90. if receiver else 25.))
        require(portal.get_class() == self.cls and not portal.get_property("bReplicates"), "teleporter native type/replication changed")
        return portal

    def begin(self):
        self.phase_started = time.monotonic()
        target, scenario, profile = PLAN[self.index]
        original = self.originals[target]; pawn, origin = original["pawn"], original["location"]
        center = ue.FVector(origin.x+6000.+(self.index//2)*2000., origin.y, origin.z+2500.)
        self.stats_before, self.events_before, self.physical = policy.snapshot(), len(self.observer.events), []
        self.target_portal = self.spawn_portal(ue.FVector(center.x, center.y+1800., center.z), True, profile, scenario)
        self.source = self.spawn_portal(center, False, profile, scenario)
        self.source.set_property("TeleportingTarget", [self.target_portal])
        self.collision = int(self.source.Box.call_function("GetCollisionEnabled"))
        self.source.Box.call_function("SetCollisionEnabled", 0)
        self.scope = SubscriptionScope(); self.scopes_created += 1
        self.scope.bind_event(self.source.Box, "OnComponentBeginOverlap", lambda component, actor, *rest:
            self.physical.append("begin") if actor == pawn else None)
        self.scope.bind_event(self.source.Box, "OnComponentEndOverlap", lambda component, actor, *rest:
            self.physical.append("end") if actor == pawn else None)
        entry = self.source.Box.call_function("K2_GetComponentLocation")
        if scenario == "relative-offset":
            right = self.source.DefaultSceneRoot1.call_function("GetRightVector")
            entry = ue.FVector(entry.x+right.x*60., entry.y+right.y*60., entry.z+80.)
        pawn.set_actor_location(entry)
        statuses = {peer: self._peer_status(peer) for peer in PEERS}
        require(all(statuses.values()), "current teleporter peer status missing")
        self.current = dict(run_id=self.run_id, case_index=self.index, target=target, scenario=scenario, profile=profile,
            roster=copy.deepcopy(self.roster), acks={}, portal_replicates=False,
            client_pawns={peer: statuses[peer]["player"]["pawn_path"] for peer in PEERS},
            client_worlds={peer: statuses[peer]["player"]["world_token"] for peer in PEERS},
            positions={peer: xyz(row["pawn"].get_actor_location()) for peer, row in self.originals.items()})
        self.publish("armed"); self.stage = "arm-ack"

    def trigger(self):
        target, scenario = self.current["target"], self.current["scenario"]
        row = self.originals[target]; pawn = row["pawn"]
        exit_component = self.target_portal.get_property("Exit Direction")
        location, forward = exit_component.call_function("K2_GetComponentLocation"), exit_component.call_function("GetForwardVector")
        math = ue.find_class("KismetMathLibrary").get_cdo()
        expected_rotation = angles(math.call_function("Conv_VectorToRotator", forward))
        expected = xyz(location)
        if scenario == "relative-offset":
            base = self.source.DefaultSceneRoot1.call_function("K2_GetComponentLocation")
            normal = self.source.DefaultSceneRoot1.call_function("GetForwardVector")
            point = math.call_function("ProjectPointOnToPlane", pawn.Mesh.call_function("K2_GetComponentLocation"), base, normal)
            delta = [getattr(point, k)-getattr(base, k) for k in ("x", "y", "z")]
            delta[2] = math.call_function("FClamp", delta[2], 0., self.source.TeleporterHeight-100.)
            expected = [a+b for a, b in zip(expected, delta)]
        requested = [v*self.source.LaunchMultiplier for v in xyz(forward)] if scenario != "no-launch" else [0.]*3
        self.current.update(expected_location=expected, forward=xyz(forward), expected_requested=requested)
        row["movement"].call_function("SetMovementMode", 3, 0)
        self.source.Box.call_function("SetCollisionEnabled", self.collision)
        events = self.observer.events[self.events_before:]
        self.current.update(position_error=distance(xyz(pawn.get_actor_location()), expected),
            rotation_error=angle_error(angles(pawn.get_actor_rotation()), expected_rotation),
            control_error=angle_error(angles(row["controller"].call_function("GetControlRotation")), expected_rotation),
            destination_selected=self.source.TeleporterDestination == self.target_portal,
            receiving_pawn=self.target_portal.ReceivingPawn == pawn,
            receiver_box_destroyed=not valid(self.target_portal.get_component_by_type(ue.find_class("BoxComponent"))),
            launch_event_count=len(events), launch_event=copy.deepcopy(events[0]) if events else None,
            other_owner_launch_events=sum(event["pawn"] != pawn.get_path_name() for event in events))
        require(not policy.snapshot()["errors"], "network teleporter policy raised")
        require(self.current["position_error"] < .01 and self.physical == ["end", "begin"], "native teleporter entry/result differs")
        self.stage, self.stage_started = "physics", time.monotonic()

    def close_portals(self):
        if self.scope is not None and not self.scope.closed:
            self.scope.close(); self.scopes_closed += 1
        for portal in self.portals:
            if valid(portal):
                portal.actor_destroy(); self.actors_destroyed += int(not valid(portal))
        self.portals.clear()

    def restore_trial(self):
        self.close_portals()
        row = self.originals[self.current["target"]]
        row["movement"].call_function("StopMovementImmediately"); row["movement"].call_function("DisableMovement")
        row["pawn"].set_actor_location(row["location"]); row["pawn"].set_actor_rotation(row["rotation"])
        row["controller"].call_function("SetControlRotation", row["aim"])
        after = policy.snapshot()
        self.current.update(physical_events=list(self.physical), fixture_scope_closed=self.scope.closed, portals_destroyed=True,
            restore_positions={peer: xyz(value["location"]) for peer, value in self.originals.items()},
            python_counters={k: after[k]-self.stats_before[k] for k in after if k != "errors"})
        self.publish("restored"); self.stage = "trial-restore-ack"

    def restore(self):
        if self.peer != "server" or self.players_restored:
            return
        self.close_portals()
        try:
            for peer, row in self.originals.items():
                row["movement"].call_function("StopMovementImmediately")
                row["pawn"].set_actor_location(row["location"]); row["pawn"].set_actor_rotation(row["rotation"])
                row["controller"].call_function("SetControlRotation", row["aim"])
                row["movement"].call_function("SetMovementMode", row["mode"], row["custom"])
                health = row["pawn"].get_component_by_type(ue.find_class("LyraHealthComponent"))
                evidence = dict(position_error=distance(xyz(row["pawn"].get_actor_location()), xyz(row["location"])),
                    rotation_error=angle_error(angles(row["pawn"].get_actor_rotation()), angles(row["rotation"])),
                    aim_error=angle_error(angles(row["controller"].call_function("GetControlRotation")), angles(row["aim"])),
                    mode=int(row["movement"].MovementMode), expected_mode=row["mode"],
                    custom_mode=int(row["movement"].CustomMovementMode), expected_custom_mode=row["custom"],
                    health=float(health.call_function("GetHealth")), expected_health=row["health"])
                self.server_restore_evidence[peer] = evidence
                require(evidence["position_error"] < .01 and evidence["rotation_error"] < .01 and evidence["aim_error"] < .01 and
                    evidence["mode"] == row["mode"] and evidence["custom_mode"] == row["custom"] and near(evidence["health"], row["health"]),
                    "teleporter native player restore differs: "+repr(evidence))
        finally:
            if self.observer is not None:
                self.observer.close()
        self.players_restored = bool(self.originals)

    def server_tick(self):
        if self.stage == "release":
            release = read_json(self.root/"release.json")
            if release is not None:
                require(release["run_id"] == self.run_id, "foreign teleporter release"); self.finish()
        elif self.stage == "complete-ack":
            if all(read_json(self.root/("ready-"+peer+".json")) is not None for peer in PEERS):
                self.stage = "release"; atomic_write(self.root/"ready-server.json", dict(run_id=self.run_id))
        elif self.stage == "ready":
            roster = self._roster(PEERS)
            if roster is not None:
                self.prepare(roster)
        elif self.stage == "arm-ack" and self.collect("armed"):
            self.trigger()
        elif self.stage == "physics" and time.monotonic()-self.stage_started > .06:
            self.current["server_motion"] = self.pawn_motion(self.originals[self.current["target"]]["pawn"])
            self.publish("moving"); self.stage = "moving-ack"
        elif self.stage == "moving-ack" and self.collect("moving"):
            self.restore_trial()
        elif self.stage == "trial-restore-ack" and self.collect("restored"):
            self.history.append(copy.deepcopy(self.current)); ue.log("UEP_TELEPORTER_NETWORK_CASE_PASSED "+str(self.index))
            self.index += 1; self.phase_started = time.monotonic()
            if self.index == len(PLAN):
                validate_cases(self.history); self.restore()
                atomic_write(self.root/"teleporter-command.json", dict(run_id=self.run_id, stage="complete",
                    originals={peer: dict(position=xyz(row["location"]), mode=row["mode"], health=row["health"])
                               for peer, row in self.originals.items()}))
                self.stage = "complete-ack"
            else:
                self.stage = "ready"

    def client_tick(self):
        packet = read_json(self.root/"teleporter-command.json")
        if packet is None or self.current_visual is None:
            return
        require(packet["run_id"] == self.run_id, "foreign teleporter command")
        motion = self.motion()
        if packet["stage"] == "complete":
            if self.players_restored:
                return
            expected = packet["originals"][self.peer]
            if (motion is not None and distance(motion["location"], expected["position"]) < 10. and
                    motion["movement_mode"] == expected["mode"] and near(self.player["health"], expected["health"])):
                require(len(self.history) == len(PLAN), "teleporter completion before all owner observations")
                self.players_restored = True
                atomic_write(self.root/("ready-"+self.peer+".json"), dict(run_id=self.run_id))
            return
        index, stage = packet["case_index"], packet["stage"]
        if index <= self.last_ack or motion is None:
            return
        ack = dict(run_id=self.run_id, case_index=index, peer=self.peer, stage=stage,
            player=copy.deepcopy(self.player), motion=motion, health_visual=copy.deepcopy(self.current_visual))
        try:
            validate_ack(packet, ack, self.peer, stage)
        except RuntimeError:
            return
        atomic_write(self.root/"teleporter-acks"/(str(index)+"-"+stage+"-"+self.peer+".json"), ack)
        if stage == "restored":
            self.history.append(ack); self.last_ack = index

    def finish(self, failure=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.restore()
        except Exception:
            failure = (failure or "")+traceback.format_exc()
        report = dict(schema_version=1, status="failed" if failure else "passed", error=failure,
            run_id=self.run_id, peer=self.peer, cases=self.history, players_restored=self.players_restored,
            actors_created=self.actors_created, actors_destroyed=self.actors_destroyed,
            scopes_created=self.scopes_created, scopes_closed=self.scopes_closed,
            launch_observer_closed=self.observer is None or self.observer.closed, server_restore_evidence=self.server_restore_evidence,
            policy=policy.snapshot(), hud=hud_state.snapshot(), weapon_observer=weapon_observer.snapshot(),
            gameplay_slice=dict(enabled=False), shutdown=None, elapsed_seconds=self._wall_elapsed(),
            fixture_server_spawn_teleport_collision_arm=True, real_lyra_players_tested=True)
        for flag in ("full_acceptance", "packaged_runtime", "portal_replication_forced", "handler_called_by_probe",
                     "teleport_called_by_probe_after_entry", "launch_called_by_probe", "velocity_or_gravity_written",
                     "attributes_written_by_probe", "physical_client_input_tested", "client_portal_profile_parity_tested",
                     "audible_parity_tested", "production_placement_tested"):
            report[flag] = False
        if failure is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        (ue.log_error if failure else ue.log)("UEP_TELEPORTER_NETWORK_"+("FAILED "+failure if failure else "PASSED"))
        self.shutdown_binding(); self._request_quit()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            now = time.monotonic()
            require(self._wall_elapsed() < self.timeout_seconds, "teleporter total timeout")
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
                require(now-self.phase_started < (300 if not self.originals else 80), "teleporter case timeout: "+str(self.index)+"/"+self.stage)
                self.server_tick()
            else:
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run_id and self.players_restored and len(self.history) == len(PLAN), "premature teleporter release")
                    self.finish()
                else:
                    self.client_tick()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False


runtime = TeleporterNetwork()
ticker = ue.add_ticker(runtime.tick)
