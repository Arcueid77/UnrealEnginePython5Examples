"""Test-owned authoritative pads, real collision/GAS and two replicated HUDs.

Native server Pawn teleports, not physical client/manual input. Pads are not
forced to replicate and client-side effect/prediction behavior is not claimed.
"""

import copy
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue

from uep_runtime.subscriptions import SubscriptionScope
from uep_lyra_hud import state as hud_state, weapon_observer
from uep_lyra_hud.shutdown_validation import defer_until_shutdown
from uep_lyra_network import NetworkProbe
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_protocol import validate_hud
from uep_lyra_hud.weapon_observer import valid
from .effect_pad_mixin import ability_system
from .effect_pad_network_protocol import PEERS, PLAN, near, require, expected_health, validate_ack, validate_server_cases


class PadNetworkProbe(NetworkProbe):
    def __init__(self):
        super().__init__()
        require(self.peer in ("server",) + PEERS, "Invalid pad network peer")
        self.timeout_seconds = 420
        self.stage = "ready"
        self.elapsed = 0.0
        self.deadline = 0.0
        self.phase_started = time.monotonic()
        self.owned_pawns = {}
        self.pad = self.cls = None
        self.scope = SubscriptionScope()
        self.physical = []
        self.current_visual = None
        self.last_ack = -1

    def _status(self):
        result = super()._status()
        result["health_visual"] = copy.deepcopy(self.current_visual)
        if self.peer != "server":
            result["ready"] = result["ready"] and self.current_visual is not None
        return result

    def visual(self):
        self.current_visual = None
        if self.player is None or not self._player_ready(self.player):
            return
        paths = hud_state.snapshot()["active_widgets"]
        if len(paths) != 1:
            return
        widget = ue.find_object(paths[0])
        if not valid(widget):
            return
        text = str(widget.HealthNumber.call_function("GetText")).replace(",", "").strip()
        try:
            number = float(text)
        except ValueError:
            return
        target = float(widget.HealthNumber.call_function("GetTargetValue"))
        ratio = float(widget.BarFillMID.call_function("K2_GetScalarParameterValue", "Health_Updated"))
        if near(number, self.player["health"]) and near(target, self.player["health"]) and near(
                ratio, self.player["health"] / self.player["max_health"]):
            self.current_visual = {"number": number, "target": target, "ratio": ratio, "widget": paths[0]}

    def health_values(self, roster):
        return {peer: float(ue.find_object(row["health_component_path"]).call_function("GetHealth"))
                for peer, row in roster.items()}

    def prepare(self, roster):
        if not self.owned_pawns:
            self.cls = ue.load_class("/Game/Environments/Gameplay/BP_GameplayEffectPad.BP_GameplayEffectPad_C")
            ue.register_declared_mixin(self.cls)
            for peer, row in roster.items():
                pawn = ue.find_object(row["pawn_path"])
                movement = pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
                self.owned_pawns[peer] = (pawn, movement, pawn.get_actor_location(), int(movement.MovementMode))
                movement.call_function("StopMovementImmediately")
                movement.call_function("DisableMovement")
        for peer, row in roster.items():
            if near(row["health"], 75):
                # The native bridge rejects a zero/no-op delta. Do not weaken
                # its authority contract to make fixture setup pass.
                continue
            result = self.bridge.call_function("ApplyAuthorityHealthDeltaToPlayer", "pad." + str(self.index) + "." + peer,
                                              75.0 - row["health"], row["player_token"])
            require(result.bApplied and near(result.HealthAfter, 75), "Native pad baseline rejected")
        self.roster = copy.deepcopy(roster)
        self.stage = "baseline"
        self.phase_started = time.monotonic()

    def begin(self, roster):
        class_name, kind, target, profile = PLAN[self.index]
        cls = ue.load_class("/Game/Environments/Gameplay/" + class_name[:-2] + "." + class_name)
        cdo = cls.get_cdo()
        effect = cdo.GE_Damage if kind == "damage" else cdo.GE_Heal
        pawn = self.owned_pawns[target][0]
        self.asc = ability_system(pawn)
        require(self.asc.call_function("GetGameplayEffectCount", effect, None, False) == 0, "Preexisting pad effect")
        self.effect = effect
        origin = self.owned_pawns[target][2]
        self.center = ue.FVector(origin.x + 4000 + self.index * 800, origin.y, origin.z + 300)
        transform = ue.FTransform()
        transform.translation = self.center
        self.pad = self.gameplay_statics.call_function("BeginDeferredActorSpawnFromClass", self.world, cls, transform, 1, None)
        require(valid(self.pad), "Server pad spawn failed")
        ue.set_mixin_profile(self.pad, profile)
        self.pad.set_property("GameplayEffectToApply", effect)
        self.gameplay_statics.call_function("FinishSpawningActor", self.pad, transform)
        require(self.pad.get_class() == cls, "Pad class changed")
        self.physical = []

        def begin_overlap(component, actor, *unused):
            if actor == pawn:
                self.physical.append("begin")

        def end_overlap(component, actor, *unused):
            if actor == pawn:
                self.physical.append("end")

        self.scope = SubscriptionScope()
        self.scope.bind_event(self.pad.Volume, "OnComponentBeginOverlap", begin_overlap)
        self.scope.bind_event(self.pad.Volume, "OnComponentEndOverlap", end_overlap)
        require(pawn.set_actor_location(self.pad.Volume.call_function("K2_GetComponentLocation")), "Server enter rejected")
        self.current = {"run_id": self.run_id, "case_index": self.index, "class": class_name, "kind": kind,
                        "target": target, "profile": profile, "server_world_token": roster[target]["world_token"],
                        "roster": copy.deepcopy(roster), "expected_health": expected_health(kind, target),
                        "client_pawns": {peer: self._peer_status(peer)["player"]["pawn_path"] for peer in PEERS},
                        "client_worlds": {peer: self._peer_status(peer)["player"]["world_token"] for peer in PEERS}}
        self.stage, self.deadline = "inside", self.elapsed + 1.1

    def server_tick(self):
        validate_hud(hud_state.snapshot())
        if self.stage == "release":
            release = read_json(self.root / "release.json")
            if release is not None:
                require(release.get("run_id") == self.run_id, "Foreign pad release")
                self.finish()
            return
        # While an effect is running, never wait for animated client UI before
        # moving the server Pawn out. The effect would keep ticking meanwhile.
        roster = self.roster if self.stage in ("inside", "outside", "ack") else self._roster(PEERS)
        if roster is None:
            return
        if self.stage == "ready":
            self.prepare(roster)
        elif self.stage == "baseline":
            if all(near(row["health"], 75) and near(self._peer_status(peer)["player"]["health"], 75)
                   for peer, row in roster.items()):
                self.begin(roster)
        elif self.stage == "inside" and self.elapsed >= self.deadline:
            self.current["inside_count"] = int(self.asc.call_function("GetGameplayEffectCount", self.effect, None, False))
            require(self.current["inside_count"] >= 1, "Server physical begin did not apply GAS")
            require(self.health_values(roster) == self.current["expected_health"], "Wrong native pad Health/owner")
            pawn = self.owned_pawns[self.current["target"]][0]
            require(pawn.set_actor_location(ue.FVector(self.center.x + 500, self.center.y, self.center.z)), "Server leave rejected")
            self.stage, self.deadline = "outside", self.elapsed + 1.1
        elif self.stage == "outside" and self.elapsed >= self.deadline:
            self.current["after_count"] = int(self.asc.call_function("GetGameplayEffectCount", self.effect, None, False))
            require(self.current["after_count"] == 0, "Server physical end left active effect")
            self.current["health_after"] = self.health_values(roster)
            require(self.current["health_after"] == self.current["expected_health"], "Pad health changed after leave")
            require(self.physical == ["begin", "end"], "Server collision entry replayed/missing")
            self.current["physical_events"] = list(self.physical)
            if self.current["profile"] == "Python":
                self.current.update(python_constructions=self.pad._uep_effect_pad_constructions,
                                    python_begin_intents=self.pad._uep_effect_pad_begin_intents,
                                    python_end_intents=self.pad._uep_effect_pad_end_intents)
            self.scope.close()
            self.pad.actor_destroy()
            self.pad = None
            atomic_write(self.root / "pad-command.json", self.current)
            self.stage = "ack"
        elif self.stage == "ack":
            acks = {peer: read_json(self.root / "pad-acks" / (str(self.index) + "-" + peer + ".json")) for peer in PEERS}
            if not all(acks.values()):
                return
            for peer, ack in acks.items():
                validate_ack(self.current, ack, peer)
                validate_hud(ack["hud"], ack["player"])
            self.current["acks"] = acks
            self.history.append(copy.deepcopy(self.current))
            self.index += 1
            if self.index == len(PLAN):
                validate_server_cases(self.history)
                self.restore()
                self.stage = "release"
                atomic_write(self.root / "ready-server.json", {"run_id": self.run_id})
            else:
                self.stage = "ready"
                self.phase_started = time.monotonic()

    def client_tick(self):
        packet = read_json(self.root / "pad-command.json")
        if packet is None or packet["case_index"] <= self.last_ack or self.current_visual is None:
            return
        require(packet["run_id"] == self.run_id, "Foreign pad command")
        if not near(self.player["health"], packet["expected_health"][self.peer]):
            return
        ack = {"run_id": self.run_id, "case_index": packet["case_index"], "peer": self.peer,
               "server_world_token": packet["server_world_token"], "player": copy.deepcopy(self.player),
               "health_visual": copy.deepcopy(self.current_visual), "hud": hud_state.snapshot()}
        validate_ack(packet, ack, self.peer)
        validate_hud(ack["hud"], ack["player"])
        self.history.append(ack)
        self.last_ack = packet["case_index"]
        atomic_write(self.root / "pad-acks" / (str(self.last_ack) + "-" + self.peer + ".json"), ack)
        if self.last_ack == len(PLAN) - 1:
            atomic_write(self.root / ("ready-" + self.peer + ".json"), {"run_id": self.run_id})

    def restore(self):
        self.scope.close()
        if valid(self.pad):
            self.pad.actor_destroy()
            self.pad = None
        for pawn, movement, location, mode in self.owned_pawns.values():
            if valid(pawn):
                pawn.set_actor_location(location)
                movement.call_function("SetMovementMode", mode, 0)
        self.owned_pawns.clear()
        if self.cls is not None:
            require(ue.unregister_mixin(self.cls), "Pad router restore failed")
            self.cls = None

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.restore()
        except Exception:
            error = (error or "") + traceback.format_exc()
        report = {"schema_version": 1, "status": "failed" if error else "passed", "run_id": self.run_id,
                  "peer": self.peer, "cases": self.history, "error": error, "full_acceptance": False,
                  "native_health_replication": not bool(error), "client_effect_prediction_verified": False,
                  "physical_client_input_tested": False, "pad_replication_forced": False,
                  "overlap_handlers_called_by_probe": False, "attributes_written_by_probe": False,
                  "fixture_delegates_closed": self.scope.closed, "hud": hud_state.snapshot(),
                  "weapon_observer": weapon_observer.snapshot(), "gameplay_slice": {"enabled": False},
                  "shutdown": None, "elapsed_seconds": self._wall_elapsed()}
        if error is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        (ue.log_error if error else ue.log)("UEP_EFFECT_PAD_NETWORK_" + ("FAILED " + error if error else "PASSED"))
        self.shutdown_binding()
        self._request_quit()

    def tick(self, delta):
        try:
            self.elapsed += delta
            if self.finished:
                return False
            require(self._wall_elapsed() < self.timeout_seconds, "Pad total timeout")
            now = time.monotonic()
            if now < self.next_tick:
                return True
            self.next_tick = now + 0.05
            world = self._game_world()
            if not valid(world) or not self._attach(world):
                return True
            self.rows = [self._snapshot_report(s) for s in self.bridge.call_function("CapturePlayerSnapshots")]
            if self.peer == "server":
                self._isolate_bot_combat()
            self.player = self.rows[0] if self.peer != "server" and len(self.rows) == 1 else None
            if self.peer != "server":
                self.visual()
            atomic_write(self.root / "status" / (self.peer + ".json"), self._status())
            if self.peer == "server":
                require(now - self.phase_started < 180, "Pad case timeout: " + str(self.index) + "/" + self.stage)
                self.server_tick()
            else:
                release = read_json(self.root / "release.json")
                if release is not None:
                    require(release.get("run_id") == self.run_id and len(self.history) == len(PLAN), "Premature pad release")
                    self.finish()
                else:
                    self.client_tick()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False


if not any(flag in sys.argv for flag in ("-UEPGrantGENetwork", "-UEPLauncherNetwork", "-UEPSpawnerNetwork", "-UEPTeleporterNetwork", "-UEPActionTouchNetwork", "-UEPHealAbilityNetwork")):
    runtime = PadNetworkProbe()
    ticker = ue.add_ticker(runtime.tick)
