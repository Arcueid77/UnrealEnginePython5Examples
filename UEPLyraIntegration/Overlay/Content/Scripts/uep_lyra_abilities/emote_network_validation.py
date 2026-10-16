"""Two real Emote input owners and native predicted authority; no RPC replay."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_world.effect_pad_mixin import valid
from . import emote_mixin as policy
from .emote_validation import Validation as NativeEmote
from .emote_network_contract import PLAN, PEERS, require
from .jump_network_validation import Server as PlayingFixture, arg


class Client(NativeEmote):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root, self.plan, self.timeout = peer, run, Path(result).parent, PLAN, 480.
        self.report.update(peer=peer, run_id=run, native_external_movement_fixture=False,
            native_movement_producer="not exercised in this network batch", packet_loss_tested=False,
            travel_rejoin_tested=False, network_movement_interruption_tested=False,
            network_crouch_interruption_tested=False, network_pause_tested=False, gameplay_state_delivered_by_files=False)

    def ready(self):
        gate = read_json(self.root / "playing-ready.json")
        if gate is None: return
        require(gate["run_id"] == self.run and gate["native_playing_phase"], "foreign/nonplaying Emote readiness")
        NativeEmote.ready(self)

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report.update(native_net_mode=str(bridge.call_function("CaptureSnapshot").NetMode),
            native_owner_role=int(self.pawn.call_function("GetLocalRole")), player_id=int(self.controller.PlayerState.PlayerId))
        require(self.report["native_net_mode"] == "Client" and self.report["native_owner_role"] == 2, "Emote owner is not an actual autonomous client")
        atomic_write(self.root / (self.peer + "-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        atomic_write(self.root / (self.peer + "-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def may_perform_action(self):
        value = read_json(self.root / (self.peer + "-held.json"))
        if value is None: return False
        require(value["run_id"] == self.run, "foreign Emote authority-held token")
        return value["index"] == self.index and value["actual_authority_held"]

    def complete_trial(self):
        atomic_write(self.root / (self.peer + "-" + str(self.index) + "-ack.json"),
            dict(run_id=self.run, peer=self.peer, index=self.index, row=copy.deepcopy(self.row)))
        self.enter("network-restored")

    def finish(self, error=None):
        if error: return NativeEmote.finish(self, error)
        atomic_write(self.root / (self.peer + "-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def tick(self, delta):
        if not self.phase.startswith("network-"): return NativeEmote.tick(self, delta)
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < self.timeout, "native Emote owner barrier timeout")
            if self.phase == "network-permit":
                value = read_json(self.root / (self.peer + "-permit.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign Emote permit")
                    if value["index"] == self.index: NativeEmote.begin(self)
            elif self.phase == "network-restored":
                value = read_json(self.root / (self.peer + "-restored.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign Emote restoration")
                    if value["index"] == self.index: NativeEmote.complete_trial(self)
            else:
                value = read_json(self.root / "release.json")
                if value is not None:
                    require(value["run_id"] == self.run, "foreign Emote release")
                    NativeEmote.finish(self)
            return not self.finished
        except Exception:
            NativeEmote.finish(self, traceback.format_exc()); return False


class Server(PlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.ability_class, self.prepared, self.originals, self.original_profiles, self.released = policy.CLASS, False, {}, {}, False
        self.report.update(original_player_states_restored=False, original_profiles_restored=False, native_rpc_bypassed=False,
            network_movement_interruption_tested=False, network_crouch_interruption_tested=False,
            network_pause_tested=False, gameplay_state_delivered_by_files=False)

    def state(self, peer):
        owner = self.owners[peer]; pawn, ability = owner["pawn"], owner["ability"]
        montage = ability.get_property("Montage to Play")
        anim = pawn.Mesh.call_function("GetAnimInstance")
        return dict(model=capture(owner["controller"]), active=bool(ability.get_property("bIsActive")),
            montage_playing=bool(anim.call_function("Montage_IsPlaying", montage)), crouched=bool(pawn.get_property("bIsCrouched")),
            input_ignored=bool(owner["controller"].call_function("IsMoveInputIgnored")),
            health=float(pawn.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth")))

    def prepare(self):
        values = {peer: self.state(peer) for peer in PEERS}
        if not all(row["model"] is not None for row in values.values()): return
        require(all(not row["active"] and not row["montage_playing"] for row in values.values()), "Emote was already active")
        self.originals, self.prepared = values, True
        self.original_profiles = {peer: str(ue.get_mixin_profile(owner["ability"])) for peer, owner in self.owners.items()}

    def start_case(self):
        peer, index = PEERS[self.position // (len(PLAN) * 2)], self.position % (len(PLAN) * 2)
        value = read_json(self.root / (peer + "-request.json"))
        if value is None or value["index"] != index: return
        require(value["run_id"] == self.run and self.state(peer) == self.originals[peer], "foreign/unrestored Emote request")
        owner = self.owners[peer]; ability = owner["ability"]
        profile = ("EmoteBlueprintFallback", "EmotePython")[index % 2]
        ue.set_mixin_profile(ability, profile)
        require(str(ue.get_mixin_profile(ability)) == profile, "authority Emote Profile selection failed")
        self.before, self.case_started = policy.instance_snapshot(ability), time.monotonic()
        self.current = dict(target=peer, index=index, name=PLAN[index // 2], profile=profile,
            authoritative_role=int(owner["pawn"].call_function("GetLocalRole")), native_active_observed=False,
            native_montage_observed=False, native_task_observed=False, foreign_owner_unchanged=True,
            native_type_source_preserved=ability.get_class().get_path_name() == policy.CLASS and
                ability.call_function("GetAvatarActorFromActorInfo") == owner["pawn"], actual_authority_held=False)
        atomic_write(self.root / (peer + "-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        require(time.monotonic() - self.case_started < 20., "native authority Emote end/restore timeout")
        ability = self.owners[peer]["ability"]; state = self.state(peer)
        row["native_active_observed"] |= state["active"]
        row["native_montage_observed"] |= state["montage_playing"]
        row["native_task_observed"] |= len(ability.get_property("ActiveTasks")) == 1
        row["actual_authority_held"] |= state["active"] and state["montage_playing"] and len(ability.get_property("ActiveTasks")) == 1
        for other in PEERS:
            if other != peer: row["foreign_owner_unchanged"] &= self.state(other) == self.originals[other]
        require(row["foreign_owner_unchanged"], "Emote affected foreign native owner")
        if row["actual_authority_held"]:
            atomic_write(self.root / (peer + "-held.json"), dict(run_id=self.run, index=row["index"], actual_authority_held=True))
        ack = read_json(self.root / (peer + "-" + str(row["index"]) + "-ack.json"))
        if ack is None or state != self.originals[peer]: return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]), "foreign Emote acknowledgement")
        after = policy.instance_snapshot(ability)
        row.update(client=ack, authority_original_restored=True, authority_tasks_after=len(ability.get_property("ActiveTasks")),
                   authority_counters={key: value - self.before[key] for key, value in after.items()})
        self.report["cases"].append(copy.deepcopy(row))
        atomic_write(self.root / (peer + "-restored.json"), dict(run_id=self.run, index=row["index"]))
        ue.log("UEP_EMOTE_NETWORK_CASE_OBSERVED " + peer + "/" + str(row["index"]))
        self.current = None; self.position += 1

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic() - self.started < 480., "native Emote authority timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS) * len(PLAN) * 2:
                    complete = [read_json(self.root / (peer + "-complete.json")) for peer in PEERS]
                    if all(value is not None and value["run_id"] == self.run for value in complete):
                        if not self.released:
                            self.report["original_player_states_restored"] = all(self.state(peer) == self.originals[peer] for peer in PEERS)
                            for peer, owner in self.owners.items(): ue.set_mixin_profile(owner["ability"], self.original_profiles[peer])
                            self.report["original_profiles_restored"] = all(str(ue.get_mixin_profile(owner["ability"])) == self.original_profiles[peer] for peer, owner in self.owners.items())
                            atomic_write(self.root / "release.json", dict(run_id=self.run)); self.released = True
                        exits = [read_json(self.root / (peer + "-exited.json")) for peer in PEERS]
                        if all(value is not None and value["run_id"] == self.run and value["exit_code"] == 0 for value in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root / "server-status.json", dict(position=self.position, current=self.current,
                native_playing_gate=self.playing_gate, elapsed_seconds=time.monotonic() - self.started))
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error: self.report["failed_authority_observation"] = copy.deepcopy(self.current)
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_EMOTE_NETWORK_" + ("FAILED " + error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_EMOTE_NETWORK_" + self.report["status"].upper())


if any(value.startswith("-UEPEmoteNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPEmoteNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
