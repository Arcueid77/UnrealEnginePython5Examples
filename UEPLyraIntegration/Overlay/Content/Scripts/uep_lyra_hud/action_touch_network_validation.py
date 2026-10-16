"""Real replicated owners, local typed producers, native UMG lifetime comparison."""
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage, Vector2D
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_network_validation import PadNetworkProbe
from . import action_touch_mixin as policy, state as hud_state, weapon_observer
from .shutdown_validation import defer_until_shutdown
from .weapon_observer import valid
from .action_touch_contract import equal
from .action_touch_network_protocol import PHASES, PEERS, require, validate_ack, validate_phases

CHANNEL = "Ability.Interaction.Duration.Message"


def model(widget):
    return [float(widget.Duration), float(widget.StartTime), bool(widget.Charging)]


def widget_state(widget):
    return dict(duration=float(widget.Duration), started=float(widget.StartTime), charging=bool(widget.Charging),
        disabled=bool(widget.get_property("isDisabled")), materials={image: {
            field: float(policy.material(widget, image).call_function("K2_GetScalarParameterValue", field))
            for field in ("Animate_Cooldown", "Animate_ActiveToInactive", "Animate_FromEmpty")}
            for image in ("WeaponCard", "ItemGlow")})


def inactive(proxy):
    return not valid(proxy) or not proxy.call_function("IsActive")


class Network(PadNetworkProbe):
    def __init__(self):
        super().__init__()
        self.timeout_seconds, self.widgets, self.pairs = 600, [], {}
        self.applied = -1
        self.local = None
        self.roster = None

    def _status(self):
        result = super()._status()
        result.update(action_touch_stage=self.stage, action_touch_phase=self.index)
        return result

    def publish(self):
        atomic_write(self.root/"action-touch-command.json", dict(run_id=self.run_id, phase_index=self.index,
            phase=PHASES[self.index], roster=copy.deepcopy(self.roster)))
        self.phase_started = time.monotonic(); self.stage = "phase-ack"

    def server_tick(self):
        if self.stage == "ready":
            roster = self._roster(PEERS)
            if roster is not None:
                self.roster = copy.deepcopy(roster); self.publish()
        elif self.stage == "phase-ack":
            acks = {peer: read_json(self.root/"action-touch-acks"/(str(self.index)+"-"+peer+".json")) for peer in PEERS}
            if not all(acks.values()):
                return
            packet = dict(run_id=self.run_id, phase_index=self.index, phase=PHASES[self.index], roster=copy.deepcopy(self.roster), acks=acks)
            for peer in PEERS:
                validate_ack(packet, acks[peer], peer)
            self.history.append(packet); ue.log("UEP_ACTION_TOUCH_NETWORK_PHASE_PASSED "+str(self.index))
            self.index += 1
            if self.index == len(PHASES):
                validate_phases(self.history); self.stage = "complete-ack"
                atomic_write(self.root/"action-touch-command.json", dict(run_id=self.run_id, phase="complete"))
            else:
                self.publish()
        elif self.stage == "complete-ack":
            if all(read_json(self.root/("ready-"+peer+".json")) is not None for peer in PEERS):
                atomic_write(self.root/"ready-server.json", dict(run_id=self.run_id)); self.stage = "release"
        elif self.stage == "release":
            release = read_json(self.root/"release.json")
            if release is not None:
                require(release["run_id"] == self.run_id, "foreign touch release"); self.finish()

    def setup(self):
        self.production_baseline = policy.snapshot()
        self.controller = ue.find_object(self.player["controller_path"])
        self.pawn = ue.find_object(self.player["pawn_path"])
        self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
            "GetGameInstanceSubsystem", self.world, ue.find_class("GameplayMessageSubsystem"))
        for kind, path in (("base", policy.CLASS), ("mobile", policy.MOBILE_CLASS)):
            cls = ue.load_class(path); pair = []
            for index, profile in enumerate(("Python", "BlueprintFallback")):
                widget = self.controller.create_widget(cls)
                widget.add_to_root(); self.widgets.append(widget); pair.append(widget)
                ue.set_mixin_profile(widget, profile)
                widget.set_property("DurationMessageTag", GameplayTag(TagName=CHANNEL))
                widget.AddToViewport(500)
                widget.SetPositionInViewport(Vector2D(X=20.+index*200., Y=20. if kind == "base" else 170.), False)
                widget.SetDesiredSizeInViewport(Vector2D(X=130., Y=130.))
                widget.call_function(policy.RESUME)
            self.pairs[kind] = pair

    def resolve_pawn(self, player_id):
        statics = ue.find_class("GameplayStatics").get_cdo()
        actors = ue.call_function_by_class(statics, ue.find_class("GameplayStatics"), "GetAllActorsOfClass",
            dict(WorldContextObject=self.world, ActorClass=ue.find_class("LyraCharacter")))["OutActors"]
        matches = []
        for actor in actors:
            player_state = actor.get_property("PlayerState")
            if valid(player_state) and int(player_state.call_function("GetPlayerId")) == player_id:
                matches.append(actor)
        return matches[0] if len(matches) == 1 else None

    def broadcast(self, instigator, duration):
        self.widgets[0].call_function("BroadcastActionDuration", self.router, GameplayTag(TagName=CHANNEL),
            LyraInteractionDurationMessage(Instigator=instigator, Duration=duration))

    def apply(self, packet):
        phase = packet["phase"]
        if phase == "baseline":
            self.setup()
        target_peer = phase[6:] if phase.startswith("owner-") else ("B0" if self.peer == "A" else "A")
        target_id = packet["roster"][target_peer]["player_id"]
        target_pawn = self.resolve_pawn(target_id)
        if not valid(target_pawn):
            return False
        self.local = dict(broadcast_player_id=target_id, broadcast_instigator=target_pawn.get_path_name(),
            before={kind: [model(w) for w in pair] for kind, pair in self.pairs.items()},
            counts={kind: pair[0]._uep_action_messages for kind, pair in self.pairs.items()}, old={})
        if phase.startswith("owner-"):
            self.broadcast(target_pawn, 2. if target_peer == "A" else 3.)
        elif phase == "foreign":
            self.broadcast(target_pawn, 9.)
        elif phase == "unmounted":
            for widget in self.widgets:
                widget.RemoveFromParent()
        elif phase == "reconstructed":
            for widget in self.widgets:
                widget.AddToViewport(500)
            self.broadcast(self.pawn, .7)
        elif phase == "profiles":
            for kind, pair in self.pairs.items():
                candidate = pair[0]; old_scope = candidate._uep_action_scope
                ue.set_mixin_profile(candidate, "BlueprintFallback"); candidate.call_function(policy.RESUME)
                old_proxy = candidate.get_property(policy.PROXY)
                ue.set_mixin_profile(candidate, "Python"); candidate.call_function(policy.RESUME)
                self.local["old"][kind] = dict(old_python_scope_closed=old_scope.closed, old_original_proxy_inactive=inactive(old_proxy))
                self.local["counts"][kind] = 0
            self.broadcast(self.pawn, 1.1)
        elif phase == "cleanup":
            self.cleanup_widgets()
        self.applied, self.applied_at = packet["phase_index"], time.monotonic()
        return True

    def cleanup_widgets(self):
        for widget in self.widgets:
            widget.RemoveFromParent(); ue.clear_mixin_profile(widget)
            if widget.is_rooted():
                widget.remove_from_root()

    def ack(self, packet):
        phase = packet["phase"]
        if phase == "unmounted":
            # Native Destruct has run; producer is intentionally later, not a
            # synchronous delivery while Slate still owns the widget.
            self.broadcast(self.pawn, 9.)
        row = dict(run_id=self.run_id, phase_index=packet["phase_index"], phase=phase, peer=self.peer,
            player=copy.deepcopy(self.player), synthetic_client_local_typed_message=True,
            message_network_replication_tested=False, pairs={},
            broadcast_player_id=self.local["broadcast_player_id"], broadcast_instigator=self.local["broadcast_instigator"])
        if phase == "cleanup":
            stats = policy.snapshot()
            row.update(roots_released=sum(not w.is_rooted() for w in self.widgets),
                owned_active_count=sum(w.get_path_name() in stats["active_widgets"] for w in self.widgets),
                scopes_balanced=stats["scopes_created"]-self.production_baseline["scopes_created"] ==
                    stats["scopes_closed"]-self.production_baseline["scopes_closed"],
                production_scopes_preserved=set(stats["active_widgets"]) == set(self.production_baseline["active_widgets"]),
                production_baseline=copy.deepcopy(self.production_baseline))
        else:
            for kind, (candidate, baseline) in self.pairs.items():
                proxy = baseline.get_property(policy.PROXY)
                result = dict(python=widget_state(candidate), blueprint=widget_state(baseline),
                    same_class=candidate.get_class() == baseline.get_class(),
                    owner_correct=candidate.call_function("GetOwningPlayer") == self.controller and baseline.call_function("GetOwningPlayer") == self.controller,
                    python_messages=candidate._uep_action_messages,
                    model_unchanged=self.local["before"][kind] == [model(candidate), model(baseline)],
                    message_delta=candidate._uep_action_messages-self.local["counts"][kind],
                    python_scope_closed=candidate._uep_action_scope is None, original_proxy_inactive=inactive(proxy))
                result.update(self.local["old"].get(kind, {})); row["pairs"][kind] = result
        validate_ack(packet, row, self.peer)
        self.history.append(row); self.last_ack = packet["phase_index"]
        atomic_write(self.root/"action-touch-acks"/(str(self.last_ack)+"-"+self.peer+".json"), row)

    def client_tick(self):
        packet = read_json(self.root/"action-touch-command.json")
        if packet is None or self.current_visual is None:
            return
        require(packet["run_id"] == self.run_id, "foreign touch command")
        if packet["phase"] == "complete":
            if self.stage != "release":
                require(len(self.history) == len(PHASES), "premature touch completion")
                atomic_write(self.root/("ready-"+self.peer+".json"), dict(run_id=self.run_id)); self.stage = "release"
            return
        if packet["phase_index"] <= self.last_ack:
            return
        if packet["phase_index"] != self.applied:
            if not self.apply(packet):
                return
        if time.monotonic()-self.applied_at > .2:
            self.ack(packet)

    def finish(self, failure=None):
        if self.finished:
            return
        self.finished = True
        try:
            if self.peer != "server":
                self.cleanup_widgets()
        except Exception:
            failure = (failure or "")+traceback.format_exc()
        report = dict(schema_version=1, status="failed" if failure else "passed", error=failure,
            run_id=self.run_id, peer=self.peer, phases=self.history, action_touch=policy.snapshot(),
            action_touch_observers=policy.snapshot(),
            hud=hud_state.snapshot(), weapon_observer=weapon_observer.snapshot(), gameplay_slice=dict(enabled=False),
            shutdown=None, elapsed_seconds=self._wall_elapsed(), synthetic_client_local_typed_message=True)
        for flag in ("full_acceptance", "packaged_runtime", "physical_touch_tested", "message_network_replication_tested",
                     "native_duration_ability_producer_tested", "player_movement_or_health_written", "production_placement_tested"):
            report[flag] = False
        if failure is None:
            defer_until_shutdown(report, self.result_path)
        atomic_write(Path(self.result_path), report)
        (ue.log_error if failure else ue.log)("UEP_ACTION_TOUCH_NETWORK_"+("FAILED "+failure if failure else "PASSED"))
        self.shutdown_binding(); self._request_quit()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            now = time.monotonic()
            require(self._wall_elapsed() < self.timeout_seconds, "action-touch network timeout")
            if now < self.next_tick:
                return True
            self.next_tick = now+.03
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
            require(now-self.phase_started < (300 if self.roster is None else 60), "action-touch network phase timeout")
            if self.peer == "server":
                self.server_tick()
            else:
                release = read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"] == self.run_id and len(self.history) == len(PHASES), "premature touch release")
                    self.finish()
                else:
                    self.client_tick()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False


runtime = Network()
ticker = ue.add_ticker(runtime.tick)
