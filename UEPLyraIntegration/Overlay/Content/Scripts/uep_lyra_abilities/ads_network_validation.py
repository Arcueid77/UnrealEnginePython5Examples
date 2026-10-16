"""Two local ADS input/UI owners and native authority camera/speed/GAS."""
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
from . import ads_mixin as policy
from .ads_contract import NETWORK_PLAN as PLAN, require
from .ads_validation import Validation as NativeADS
from .jump_network_validation import Server as PlayingFixture, arg, PEERS


class Client(NativeADS):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root = peer, run, Path(result).parent
        self.plan = PLAN
        self.report.update(peer=peer, run_id=run, local_camera_speed_mapping_written_by_probe=False,
            ui_message_replication_tested=False, native_rpc_bypassed=False, packet_loss_tested=False,
            travel_rejoin_tested=False, paused_world_scope="standalone only; network pause not tested")

    def ready(self):
        value = read_json(self.root/"playing-ready.json")
        if value is None: return
        require(value["run_id"] == self.run and value["native_playing_phase"], "foreign/nonplaying ADS gate")
        NativeADS.ready(self)

    def begin(self):
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report["native_net_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_net_mode"] == "Client", "ADS owner is not a real client")
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def may_finish_hold(self):
        value = read_json(self.root/(self.peer+"-held.json"))
        if value is None: return False
        require(value["run_id"] == self.run, "foreign native ADS held gate")
        return value["index"] == self.index and value["actual_authority_held"]

    def settled(self):
        if time.monotonic()-self.phase_started < .25: return
        after = policy.snapshot(); self.row["no_late_callbacks"] = after == self.at_end
        self.row["counters"] = {key: value-self.before[key] for key, value in after.items() if type(value) is int and key != "active_count"}
        self.close_observer()
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run,
            peer=self.peer, index=self.index, row=copy.deepcopy(self.row)))
        self.enter("network-restored")

    def finish(self, error=None):
        if error: return NativeADS.finish(self, error)
        atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def tick(self, seconds):
        if not self.phase.startswith("network-"): return NativeADS.tick(self, seconds)
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native ADS owner barrier timeout")
            if self.phase == "network-permit":
                value = read_json(self.root/(self.peer+"-permit.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign native ADS permit")
                    if value["index"] == self.index: NativeADS.begin(self)
            elif self.phase == "network-restored":
                value = read_json(self.root/(self.peer+"-restored.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign native ADS restoration")
                    if value["index"] == self.index:
                        self.sides.append(copy.deepcopy(self.row))
                        if self.index % 2:
                            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
                            ue.log("UEP_ADS_CASE_OBSERVED "+self.name)
                        self.index += 1
                        if self.index == len(PLAN)*2: self.finish()
                        else: self.begin()
            else:
                value = read_json(self.root/"release.json")
                if value is not None:
                    require(value["run_id"] == self.run, "foreign native ADS release")
                    NativeADS.finish(self)
            return not self.finished
        except Exception: NativeADS.finish(self, traceback.format_exc()); return False


class Server(PlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.ability_class, self.prepared, self.originals = policy.CLASS, False, {}
        self.released = False
        self.report.update(native_rpc_bypassed=False, camera_or_speed_written_by_probe=False,
            mapping_context_written_by_probe=False, ui_message_replication_tested=False, original_player_states_restored=False)

    def state(self, peer):
        owner = self.owners[peer]; hero = owner["pawn"].get_component_by_type(ue.find_class("LyraHeroComponent"))
        camera = hero.get_property("AbilityCameraMode")
        return dict(model=capture(owner["controller"]), speed=float(owner["pawn"].CharacterMovement.MaxWalkSpeed),
            camera=camera.get_path_name() if camera else None, input_ignored=bool(owner["controller"].call_function("IsMoveInputIgnored")))

    def prepare(self):
        values = {peer: self.state(peer) for peer in PEERS}
        if not all(row["model"] is not None for row in values.values()): return
        require(all(not row["ability"].get_property("bIsActive") for row in self.owners.values()), "ADS already active before fixture")
        self.originals, self.prepared = values, True

    def start_case(self):
        peer, index = PEERS[self.position//(len(PLAN)*2)], self.position % (len(PLAN)*2)
        value = read_json(self.root/(peer+"-request.json"))
        if value is None or value["index"] != index: return
        require(value["run_id"] == self.run and self.state(peer) == self.originals[peer], "foreign/unrestored native ADS request")
        ue.set_mixin_profile(self.owners[peer]["ability"], ("ADSBlueprintFallback", "ADSPython")[index % 2])
        self.before, self.case_started = policy.snapshot(), time.monotonic()
        self.current = dict(target=peer, index=index, name=PLAN[index//2], authoritative_role=int(self.owners[peer]["pawn"].call_function("GetLocalRole")),
            native_active_observed=False, native_half_speed_observed=False, native_camera_mode_observed=False,
            native_wait_task_observed=False, foreign_owner_unchanged=True)
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        require(time.monotonic()-self.case_started < 20., "native authority ADS end/restore timeout")
        ability = self.owners[peer]["ability"]; state = self.state(peer)
        row["native_active_observed"] |= bool(ability.get_property("bIsActive"))
        row["native_half_speed_observed"] |= abs(state["speed"]-self.originals[peer]["speed"]*float(ability.ADSMultiplier)) < .01
        row["native_camera_mode_observed"] |= state["camera"] == policy.CAMERA
        row["native_wait_task_observed"] |= sum(valid(task) and task.is_a(ue.find_class("AbilityTask_WaitInputRelease")) for task in ability.get_property("ActiveTasks")) == 1
        for key in PEERS:
            if key != peer: row["foreign_owner_unchanged"] &= self.state(key) == self.originals[key]
        require(row["foreign_owner_unchanged"], "ADS changed foreign owner camera/speed/equipment/input")
        if all(row[key] for key in ("native_active_observed", "native_half_speed_observed", "native_camera_mode_observed", "native_wait_task_observed")):
            atomic_write(self.root/(peer+"-held.json"), dict(run_id=self.run, index=row["index"], actual_authority_held=True))
        ack = read_json(self.root/(peer+"-"+str(row["index"])+"-ack.json"))
        if ack is None or ability.get_property("bIsActive") or state != self.originals[peer]: return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]), "foreign ADS native ack")
        stats = policy.snapshot()
        row.update(client=ack, authority_original_restored=True, authority_tasks_after=len(ability.get_property("ActiveTasks")),
            authority_counters={key: value-self.before[key] for key, value in stats.items() if type(value) is int and key != "active_count"})
        self.report["cases"].append(copy.deepcopy(row))
        atomic_write(self.root/("authority-"+str(self.position)+".json"), dict(run_id=self.run, row=row))
        atomic_write(self.root/(peer+"-restored.json"), dict(run_id=self.run, index=row["index"]))
        ue.log("UEP_ADS_NETWORK_CASE_OBSERVED "+peer+"/"+str(row["index"]))
        self.current = None; self.position += 1

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native ADS authority timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS)*len(PLAN)*2:
                    complete = [read_json(self.root/(peer+"-complete.json")) for peer in PEERS]
                    if all(value is not None and value["run_id"] == self.run for value in complete):
                        if not self.released:
                            self.report["original_player_states_restored"] = all(self.state(peer) == self.originals[peer] for peer in PEERS)
                            atomic_write(self.root/"release.json", dict(run_id=self.run)); self.released = True
                        exits = [read_json(self.root/(peer+"-exited.json")) for peer in PEERS]
                        if all(value is not None and value["exit_code"] == 0 for value in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(position=self.position, current=self.current, elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error: self.report["failed_authority_observation"] = copy.deepcopy(self.current)
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_ADS_NETWORK_"+("FAILED "+error if error else "READY")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_ADS_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPADSNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPADSNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
