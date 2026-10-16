"""Native authority collision/GAS/cooldown, both replicated owner Health HUDs."""
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
from .grant_ge_pad_network_protocol import PLAN, PEERS, near, require, validate_ack, validate_cases
from . import grant_ge_pad_mixin as policy
from uep_lyra_hud.weapon_observer import valid

class GrantGENetwork(PadNetworkProbe):
    def __init__(self):
        super().__init__()
        self.timeout_seconds, self.saved_health = 600, {}
        self.pickup_seen, self.players_restored = -1, False
        self.visual_debug = {}

    def _status(self):
        result = super()._status()
        result["health_debug"] = copy.deepcopy(self.visual_debug)
        return result

    def visual(self):
        super().visual()
        paths = hud_state.snapshot()["active_widgets"]
        self.visual_debug = {"widgets": paths, "player_health": self.player["health"] if self.player else None}
        if len(paths) == 1:
            widget = ue.find_object(paths[0])
            if valid(widget):
                self.visual_debug.update(text=str(widget.HealthNumber.call_function("GetText")),
                    target=float(widget.HealthNumber.call_function("GetTargetValue")),
                    ratio=float(widget.BarFillMID.call_function("K2_GetScalarParameterValue", "Health_Updated")),
                    normalized=float(widget.NormalizedHealth), old=float(widget.HealthOldValue), new=float(widget.HealthNewValue),
                    presented=widget._uep_hud_presented_health, visual_active=widget._uep_hud_visual_active,
                    cached_material=widget.BarFillMID.get_path_name(),
                    animations={name: bool(widget.call_function("IsAnimationPlaying", getattr(widget, name)))
                        for name in ("OnSpawned", "OnDamaged", "OnHealed", "OnEliminated")})
                actual = widget.BarFill.Brush.ResourceObject
                if valid(actual):
                    self.visual_debug.update(actual_material=actual.get_path_name(),
                        actual_ratio=float(actual.call_function("K2_GetScalarParameterValue", "Health_Updated")))

    def set_health(self, peer, value, suffix):
        row = self.roster[peer]
        health = ue.find_object(row["health_component_path"])
        delta = value-float(health.call_function("GetHealth"))
        if abs(delta) < .001:
            return
        result = self.bridge.call_function("ApplyAuthorityHealthDeltaToPlayer", "grant-ge."+str(self.index)+"."+peer+"."+suffix,
                                           delta, row["player_token"])
        require(result.bApplied and near(float(result.HealthAfter), value), "native grant-GE setup rejected: "+str(result.Status))

    def prepare(self, roster):
        self.roster = copy.deepcopy(roster)
        if not self.owned_pawns:
            self.cls = ue.load_class(policy.CLASS)
            ue.register_declared_mixin(self.cls)
            for peer, row in roster.items():
                pawn = ue.find_object(row["pawn_path"])
                movement = pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
                self.owned_pawns[peer] = pawn, movement, pawn.get_actor_location(), int(movement.MovementMode)
                self.saved_health[peer] = float(row["health"])
                movement.call_function("StopMovementImmediately")
                movement.call_function("DisableMovement")
        for peer in PEERS:
            self.set_health(peer, 75.0, "baseline")
        self.stage = "baseline"
        self.phase_started = time.monotonic()

    def begin(self):
        self.phase_started = time.monotonic()
        target, profile = PLAN[self.index]
        pawn, movement, origin, mode = self.owned_pawns[target]
        self.center = ue.FVector(origin.x+6000.0+self.index*1200.0, origin.y, origin.z+500.0)
        transform = ue.FTransform()
        transform.translation = self.center
        self.stats_before, self.physical = policy.snapshot(), []
        self.pad = ue.find_class("GameplayStatics").get_cdo().call_function("BeginDeferredActorSpawnFromClass", self.world, self.cls, transform, 1, None)
        require(valid(self.pad), "native network grant-GE pad spawn failed")
        ue.set_mixin_profile(self.pad, profile)
        ue.find_class("GameplayStatics").get_cdo().call_function("FinishSpawningActor", self.pad, transform)
        require(float(self.pad.Duration) == 15.0 and self.pad.get_class() == self.cls and ue.get_mixin_profile(self.pad) == profile,
                "native grant-GE class/default/Profile differs")
        self.current = {"run_id": self.run_id, "case_index": self.index, "target": target, "profile": profile,
            "roster": copy.deepcopy(self.roster), "client_pawns": {peer: self._peer_status(peer)["player"]["pawn_path"] for peer in PEERS},
            "client_worlds": {peer: self._peer_status(peer)["player"]["world_token"] for peer in PEERS}, "acks": {}}
        self.scope = SubscriptionScope()
        self.scope.bind_event(self.pad.Volume, "OnComponentBeginOverlap", lambda component, actor, *rest:
                              self.physical.append("begin") if actor == pawn else None)
        self.scope.bind_event(self.pad.Volume, "OnComponentEndOverlap", lambda component, actor, *rest:
                              self.physical.append("end") if actor == pawn else None)
        require(pawn.set_actor_location(self.pad.Volume.call_function("K2_GetComponentLocation")), "native network enter rejected")
        self.stage, self.stage_started = "inside", time.monotonic()

    def publish(self, stage):
        atomic_write(self.root/"grant-ge-command.json", dict(self.current, stage=stage))

    def collect(self, stage):
        rows = {peer: read_json(self.root/"grant-ge-acks"/(str(self.index)+"-"+stage+"-"+peer+".json")) for peer in PEERS}
        if not all(rows.values()):
            return False
        for peer in PEERS:
            validate_ack(self.current, rows[peer], peer, stage)
        self.current["acks"][stage] = rows
        return True

    def server_tick(self):
        if self.stage == "release":
            release = read_json(self.root/"release.json")
            if release is not None:
                require(release["run_id"] == self.run_id, "foreign grant-GE release")
                self.finish()
            return
        if self.stage == "restore-ack":
            if all(read_json(self.root/("ready-"+peer+".json")) is not None for peer in PEERS):
                self.stage = "release"
                atomic_write(self.root/"ready-server.json", {"run_id": self.run_id})
            return
        if self.stage == "ready":
            roster = self._roster(PEERS)
            if roster is not None:
                self.prepare(roster)
            return
        if self.stage == "baseline":
            statuses = {peer: self._peer_status(peer) for peer in PEERS}
            if all(row is not None and near(row["player"]["health"], 75.0) for row in statuses.values()):
                self.begin()
        elif self.stage == "inside" and time.monotonic()-self.stage_started > .2:
            self.current["pickup_health"] = self.health_values(self.roster)
            expected = {peer: 100.0 if peer == self.current["target"] else 75.0 for peer in PEERS}
            require(self.current["pickup_health"] == expected and self.physical == ["begin"], "native heal/owner begin differs")
            self.publish("pickup")
            self.stage = "pickup-ack"
        elif self.stage == "pickup-ack" and self.collect("pickup"):
            target = self.current["target"]
            pawn = self.owned_pawns[target][0]
            require(pawn.set_actor_location(ue.FVector(self.center.x+500.0, self.center.y, self.center.z)), "native first leave rejected")
            require(not self.pad.bActive and not self.pad.call_function("IsActorTickEnabled"), "native first leave did not charge/pause")
            self.set_health(target, 75.0, "inactive-baseline")
            require(pawn.set_actor_location(self.pad.Volume.call_function("K2_GetComponentLocation")), "native inactive enter rejected")
            self.stage, self.stage_started = "inactive", time.monotonic()
        elif self.stage == "inactive" and time.monotonic()-self.stage_started > .2:
            self.current["inactive_health"] = self.health_values(self.roster)
            require(self.current["inactive_health"] == {peer: 75.0 for peer in PEERS}, "inactive grant-GE healed again")
            pawn = self.owned_pawns[self.current["target"]][0]
            require(pawn.set_actor_location(ue.FVector(self.center.x+500.0, self.center.y, self.center.z)), "native second leave rejected")
            require(self.physical == ["begin", "end", "begin", "end"], "native grant-GE collision sequence differs")
            self.charge_time = float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", self.world))
            self.stage = "cooldown"
        elif self.stage == "cooldown" and self.pad.bActive and not self.pad.TL_Charge.call_function("IsPlaying"):
            seconds = float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", self.world))-self.charge_time
            self.current.update(cooldown_seconds=seconds, physical_events=list(self.physical),
                finish={"active": bool(self.pad.bActive), "tick": bool(self.pad.call_function("IsActorTickEnabled")),
                    "light": bool(self.pad.PointLight.get_property("bVisible")), "mesh_hidden": bool(self.pad.ItemMesh.get_property("bHiddenInGame")),
                    "percent": float(self.pad.MID_TimerIndicator.call_function("K2_GetScalarParameterValue", "Percent"))},
                python_actives=policy.snapshot()["actives"]-self.stats_before["actives"],
                python_finishes=policy.snapshot()["finishes"]-self.stats_before["finishes"])
            self.scope.close()
            self.pad.actor_destroy()
            self.current.update(pad_destroyed=not valid(self.pad), fixture_scope_closed=self.scope.closed)
            self.pad = None
            self.publish("finished")
            self.stage = "finished-ack"
        elif self.stage == "finished-ack" and self.collect("finished"):
            self.history.append(copy.deepcopy(self.current))
            ue.log("UEP_GRANT_GE_NETWORK_CASE_PASSED "+str(self.index))
            self.index += 1
            self.phase_started = time.monotonic()
            if self.index == len(PLAN):
                validate_cases(self.history)
                self.restore()
                atomic_write(self.root/"grant-ge-command.json", {"run_id": self.run_id, "stage": "restored", "health": self.saved_health})
                self.stage = "restore-ack"
            else:
                self.stage = "ready"

    def client_tick(self):
        packet = read_json(self.root/"grant-ge-command.json")
        if packet is None or self.current_visual is None:
            return
        require(packet["run_id"] == self.run_id, "foreign grant-GE command")
        if packet["stage"] == "restored":
            value = packet["health"][self.peer]
            if near(self.player["health"], value) and near(self.current_visual["number"], value):
                require(len(self.history) == len(PLAN), "grant-GE restored before cases complete")
                self.players_restored = True
                atomic_write(self.root/("ready-"+self.peer+".json"), {"run_id": self.run_id})
            return
        index, stage = packet["case_index"], packet["stage"]
        if index <= self.last_ack:
            return
        expected = packet["pickup_health"][self.peer] if stage == "pickup" else 75.0
        if not near(self.player["health"], expected) or not near(self.current_visual["number"], expected):
            return
        ack = {"run_id": self.run_id, "case_index": index, "peer": self.peer, "stage": stage,
            "player": copy.deepcopy(self.player), "health_visual": copy.deepcopy(self.current_visual)}
        validate_ack(packet, ack, self.peer, stage)
        atomic_write(self.root/"grant-ge-acks"/(str(index)+"-"+stage+"-"+self.peer+".json"), ack)
        if stage == "pickup":
            self.pickup_seen = index
        else:
            require(self.pickup_seen == index, "grant-GE finish missing replicated pickup")
            self.history.append(ack)
            self.last_ack = index

    def restore(self):
        owned = list(self.owned_pawns.values())
        if self.peer == "server" and owned:
            for peer, value in self.saved_health.items():
                self.set_health(peer, value, "restore")
        super().restore()
        if owned:
            self.players_restored = True
            for pawn, movement, location, mode in owned:
                actual = pawn.get_actor_location()
                require(max(abs(getattr(actual, key)-getattr(location, key)) for key in ("x", "y", "z")) < .01 and
                        int(movement.MovementMode) == mode, "native grant-GE player restore differs")

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
            "fixture_scope_closed": self.scope.closed, "policy": policy.snapshot(), "hud": hud_state.snapshot(),
            "weapon_observer": weapon_observer.snapshot(), "gameplay_slice": {"enabled": False}, "shutdown": None,
            "fixture_server_spawn_and_teleport": True, "elapsed_seconds": self._wall_elapsed()}
        for flag in ("full_acceptance", "packaged_runtime", "client_effect_prediction_tested", "client_pad_profile_parity_tested",
                     "physical_client_input_tested", "pad_replication_forced", "handler_called_by_probe", "attributes_written_by_probe"):
            report[flag] = False
        if error is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        (ue.log_error if error else ue.log)("UEP_GRANT_GE_NETWORK_"+("FAILED "+error if error else "PASSED"))
        self.shutdown_binding()
        self._request_quit()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            now = time.monotonic()
            require(self._wall_elapsed() < self.timeout_seconds, "grant-GE total timeout")
            if now < self.next_tick:
                return True
            self.next_tick = now+.05
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
                limit = 300 if not self.owned_pawns and self.index == 0 else 120
                require(now-self.phase_started < limit, "grant-GE case timeout: "+str(self.index)+"/"+self.stage)
                self.server_tick()
            else:
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run_id and self.players_restored and len(self.history) == len(PLAN), "premature grant-GE release")
                    self.finish()
                else:
                    self.client_tick()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False


runtime = GrantGENetwork()
ticker = ue.add_ticker(runtime.tick)
