"""Real native GAS request/SendInfo. Files coordinate and compare; no receiver replay."""
import atexit
import copy
import math
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from .jump_network_validation import Server as PlayingFixture, arg
from .auto_respawn_helpers_validation import Validation as Ready, instances, specs
from .auto_respawn_helpers_network_validation import token
from .dash_selector_mixin import CLASS, FIELDS, evidence as selector_evidence
from .dash_rpc_input_mixin import evidence, vector, path
from .dash_rpc_input_contract import TRIALS, PEERS, require, client as validate_client


def delta(after, before): return {name: after[name]-before[name] for name in ("python_calls", "fallback_calls")}
def payload(ability): return dict(direction=vector(ability.get_property("Direction")), montage=path(ability.get_property("Montage")))
def configuration(ability):
    return dict(montages={name: path(ability.get_property(name)) for name in FIELDS},
        native=[int(ability.InstancingPolicy), int(ability.NetExecutionPolicy), float(ability.Strength), float(ability.RootMotionDuration), float(ability.AbilityDuration)])
def task_state(ability):
    tasks = [value for value in ability.get_property("ActiveTasks") if valid(value)]
    return dict(count=len(tasks), root=any(value.is_a(ue.find_class("AbilityTask_ApplyRootMotionConstantForce")) for value in tasks),
        montage=any(value.is_a(ue.find_class("AbilityTask_PlayMontageAndWait")) for value in tasks))
def distance(a, b): return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


class Client(Ready):
    def __init__(self, result, peer, run):
        super().__init__(result); self.require_auto_active = self.require_local_playing_phase = False
        self.peer, self.run, self.root = peer, run, self.path.parent; self.cleaned = False
        self.report = dict(schema_version=1, status="running", error=None, peer=peer, run_id=run, cases=[],
            rpc_receiver_replayed=False, activation_event_replayed=False, ability_granted_by_fixture=False,
            ability_direction_montage_written_by_fixture=False, health_written_by_fixture=False, raw_velocity_written_by_fixture=False,
            gameplay_state_delivered_by_files=False, physical_input_tested=False, enhanced_input_tested=False,
            whole_dash_activation_migrated=False, dash_task_business_migrated=False, movement_parity_certified=False,
            full_acceptance=False, packaged_runtime=False, request_entry="ASC.TryActivateAbilityByClass", movement_intent_entry="Pawn.AddMovementInput")
    def ready(self):
        if token(self.root, "playing-ready.json", self.run) is not None: Ready.ready(self)
    def begin(self):
        self.cls = ue.load_class(CLASS); values = instances(self.asc, self.cls)
        require(len(values) == 1 and not values[0].get_property("bIsActive"), "one actual granted inactive native Dash required")
        self.dash = values[0]; self.original = dict(profile=str(ue.get_mixin_profile(self.dash)), specs=specs(self.asc), config=configuration(self.dash))
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        net_mode = str(bridge.call_function("CaptureSnapshot").NetMode)
        require(net_mode == "Client", "Dash owner must be an actual native client")
        self.report.update(native_role=int(self.pawn.call_function("GetLocalRole")), native_net_mode=net_mode, player_id=int(self.controller.PlayerState.PlayerId),
            actual_ability_class=path(self.dash.get_class()), actual_granted_primary_instance=True)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        self.request()
    def request(self):
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index)); self.enter("permit")
    def trial_begin_evidence(self): pass
    def trial_end_evidence(self): pass
    def start(self):
        if self.dash.get_property("bIsActive") or self.dash.call_function("GetCooldownTimeRemaining") > 0 or int(self.pawn.CharacterMovement.MovementMode) != 1: return
        name, self.profile = TRIALS[self.index]; ue.set_mixin_profile(self.dash, self.profile)
        self.before, self.selector_before = copy.deepcopy(evidence(self.dash)), copy.deepcopy(selector_evidence(self.dash))
        self.row = dict(index=self.index, name=name, profile=self.profile, native_request_accepted=False,
            native_active_observed=False, native_root_motion_task_observed=False, native_montage_task_observed=False,
            cooldown_repeat_rejected=False, max_motion_distance=0., max_native_speed=0.)
        self.trial_begin_evidence()
        self.enter("intent")
    def intent(self):
        direction = self.pawn.call_function("GetActorForwardVector" if self.row["name"] == "forward" else "GetActorRightVector")
        scale = 1. if self.row["name"] == "forward" else -1.
        self.pawn.call_function("AddMovementInput", direction, scale, False)
        if time.monotonic()-self.phase_started < .2: return
        self.motion_start = vector(self.pawn.get_actor_location())
        self.row["native_request_accepted"] = bool(self.asc.call_function("TryActivateAbilityByClass", self.cls, False))
        require(self.row["native_request_accepted"], "native owner Dash request rejected")
        self.row["chosen"] = payload(self.dash)
        self.row["cooldown_repeat_rejected"] = self.asc.call_function("TryActivateAbilityByClass", self.cls, False) is False
        self.enter("observe")
    def observe(self):
        require(time.monotonic()-self.phase_started < 12., "native owner Dash/task/cooldown end timeout")
        active = bool(self.dash.get_property("bIsActive")); tasks = task_state(self.dash)
        self.row["native_active_observed"] |= active
        self.row["native_root_motion_task_observed"] |= tasks["root"]; self.row["native_montage_task_observed"] |= tasks["montage"]
        self.row["max_motion_distance"] = max(self.row["max_motion_distance"], distance(vector(self.pawn.get_actor_location()), self.motion_start))
        self.row["max_native_speed"] = max(self.row["max_native_speed"], distance(vector(self.pawn.call_function("GetVelocity")), [0., 0., 0.]))
        if active or self.dash.call_function("GetCooldownTimeRemaining") > 0: return
        self.quiet_before, self.selector_quiet = copy.deepcopy(evidence(self.dash)), copy.deepcopy(selector_evidence(self.dash))
        self.quiet_ticks = 0; self.enter("quiet")
    def quiet(self):
        require(evidence(self.dash) == self.quiet_before and selector_evidence(self.dash) == self.selector_quiet, "late native Dash Python dispatch")
        self.quiet_ticks += 1
        if self.quiet_ticks < 20: return
        self.row.update(native_ability_ended=not bool(self.dash.get_property("bIsActive")), native_tasks_after=task_state(self.dash)["count"],
            quiet_after_end=True, native_configuration_unchanged=configuration(self.dash) == self.original["config"],
            specs_unchanged=specs(self.asc) == self.original["specs"], rpc_counters=delta(evidence(self.dash), self.before),
            selector_counters=delta(selector_evidence(self.dash), self.selector_before))
        self.trial_end_evidence()
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, peer=self.peer, index=self.index, row=self.row))
        self.enter("authority")
    def tick(self, delta_seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360., "native Dash RPC owner timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "permit":
                permission = token(self.root, self.peer+"-permit.json", self.run)
                if permission is not None and permission["index"] == self.index: self.start()
            elif self.phase == "intent": self.intent()
            elif self.phase == "observe": self.observe()
            elif self.phase == "quiet": self.quiet()
            elif self.phase == "authority":
                row = token(self.root, self.peer+"-restored.json", self.run)
                if row is not None and row["index"] == self.index:
                    self.report["cases"].append(copy.deepcopy(self.row)); self.index += 1
                    if self.index == len(TRIALS):
                        self.cleanup(); atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run)); self.enter("release")
                    else: self.request()
            elif self.phase == "release" and token(self.root, "release.json", self.run) is not None: self.finish()
            self.write(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def cleanup(self):
        if self.cleaned: return
        if hasattr(self, "dash") and valid(self.dash):
            ue.set_mixin_profile(self.dash, self.original["profile"])
            self.report.update(profile_restored=str(ue.get_mixin_profile(self.dash)) == self.original["profile"],
                specs_unchanged=specs(self.asc) == self.original["specs"], native_configuration_unchanged=configuration(self.dash) == self.original["config"])
        self.cleaned = True
    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_DASH_RPC_INPUT_OWNER_"+("FAILED "+error if error else "READY")); ue.request_exit()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate_client(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_RPC_INPUT_SHUTDOWN_"+self.report["status"].upper())


class Server(PlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run); self.ability_class = CLASS; self.prepared = self.released = False
        self.report.update(rpc_receiver_replayed=False, activation_event_replayed=False, native_rpc_bypassed=False,
            gameplay_state_delivered_by_files=False, whole_dash_activation_migrated=False, native_pose_resets=[],
            original_profiles_restored=False, specs_and_configuration_preserved=False)
    def trial_begin_evidence(self): pass
    def trial_end_evidence(self): pass
    def state(self, peer):
        owner = self.owners[peer]; pawn, ability = owner["pawn"], owner["ability"]
        return dict(pawn=path(pawn), health=float(pawn.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth")),
            location=vector(pawn.get_actor_location()), velocity=vector(pawn.call_function("GetVelocity")),
            specs=specs(ability_system(pawn)), config=configuration(ability), active=bool(ability.get_property("bIsActive")),
            data=payload(ability), rpc=copy.deepcopy(evidence(ability)), selector=copy.deepcopy(selector_evidence(ability)),
            profile=str(ue.get_mixin_profile(ability)))
    def prepare(self):
        if any(owner["ability"].get_property("bIsActive") for owner in self.owners.values()): return
        self.originals = {peer: dict(profile=str(ue.get_mixin_profile(owner["ability"])), config=configuration(owner["ability"]),
            specs=specs(ability_system(owner["pawn"])), location=owner["pawn"].get_actor_location(), rotation=owner["pawn"].get_actor_rotation())
            for peer, owner in self.owners.items()}
        self.prepared = True
    def start_case(self):
        peer, index = PEERS[self.position//len(TRIALS)], self.position%len(TRIALS)
        request = token(self.root, peer+"-request.json", self.run)
        if request is None or request["index"] != index: return
        owner = self.owners[peer]; ability, pawn = owner["ability"], owner["pawn"]
        if ability.get_property("bIsActive") or ability.call_function("GetCooldownTimeRemaining") > 0 or int(pawn.CharacterMovement.MovementMode) != 1: return
        original = self.originals[peer]
        moved = bool(pawn.call_function("K2_TeleportTo", original["location"], original["rotation"]))
        require(moved, "native collision-checked Dash fixture pose reset refused"); pawn.call_function("ForceNetUpdate")
        self.report["native_pose_resets"].append(dict(peer=peer, index=index, native_api="K2_TeleportTo", succeeded=moved))
        name, profile = TRIALS[index]; ue.set_mixin_profile(ability, profile)
        self.before = copy.deepcopy(evidence(ability)); self.foreign = {key: self.state(key) for key in PEERS if key != peer}
        self.current = dict(target=peer, index=index, name=name, profile=profile, native_role=int(pawn.call_function("GetLocalRole")),
            actual_ability_class=path(ability.get_class()),
            stores_before_rpc=payload(ability),
            native_active_observed=False, native_root_motion_task_observed=False, native_montage_task_observed=False, foreign_owner_unchanged=True)
        self.trial_begin_evidence()
        self.case_started, self.quiet_count, self.quiet_snapshot = time.monotonic(), 0, None
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))
    def observe(self):
        row, peer = self.current, self.current["target"]; owner = self.owners[peer]; ability = owner["ability"]
        require(time.monotonic()-self.case_started < 20., "native Dash server RPC/task/ack timeout")
        tasks = task_state(ability); row["native_active_observed"] |= bool(ability.get_property("bIsActive"))
        row["native_root_motion_task_observed"] |= tasks["root"]; row["native_montage_task_observed"] |= tasks["montage"]
        require(all(self.state(key) == before for key, before in self.foreign.items()), "native Dash changed foreign authority owner")
        after = copy.deepcopy(evidence(ability)); diff = delta(after, self.before)
        if sum(diff.values()):
            row.update(received=copy.deepcopy(after["last"]), stored=payload(ability), actual_receiver_authority=after["last"]["ability_authority"])
        ack = token(self.root, peer+"-"+str(row["index"])+"-ack.json", self.run)
        if ack is None or ability.get_property("bIsActive") or ability.call_function("GetCooldownTimeRemaining") > 0: return
        if self.quiet_snapshot is None: self.quiet_snapshot = after
        require(after == self.quiet_snapshot, "native server Dash receiver dispatched late work"); self.quiet_count += 1
        if self.quiet_count < 20: return
        require((ack["peer"], ack["index"]) == (peer, row["index"]), "foreign Dash owner acknowledgement")
        row.update(rpc_counters=diff, client=ack, quiet_after_end=True, native_ability_ended=True, native_tasks_after=tasks["count"],
            native_configuration_unchanged=configuration(ability) == self.originals[peer]["config"], specs_unchanged=specs(ability_system(owner["pawn"])) == self.originals[peer]["specs"])
        self.trial_end_evidence()
        self.report["cases"].append(copy.deepcopy(row)); atomic_write(self.root/("authority-"+str(self.position)+".json"), dict(run_id=self.run, row=row))
        atomic_write(self.root/(peer+"-restored.json"), dict(run_id=self.run, index=row["index"]))
        ue.log("UEP_DASH_RPC_INPUT_NETWORK_CASE_OBSERVED "+peer+"/"+str(row["index"])); self.position += 1; self.current = None
    def restore(self):
        for peer, owner in self.owners.items(): ue.set_mixin_profile(owner["ability"], self.originals[peer]["profile"])
        self.report.update(original_profiles_restored=all(str(ue.get_mixin_profile(owner["ability"])) == self.originals[peer]["profile"] for peer, owner in self.owners.items()),
            specs_and_configuration_preserved=all(configuration(owner["ability"]) == self.originals[peer]["config"] and
                specs(ability_system(owner["pawn"])) == self.originals[peer]["specs"] for peer, owner in self.owners.items()))
    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360., "native Dash RPC server timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS)*len(TRIALS):
                    if all(token(self.root, peer+"-complete.json", self.run) is not None for peer in PEERS):
                        if not self.released: self.restore(); atomic_write(self.root/"release.json", dict(run_id=self.run)); self.released = True
                        exits = [token(self.root, peer+"-exited.json", self.run) for peer in PEERS]
                        if all(value is not None and value["exit_code"] == 0 for value in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(run_id=self.run, position=self.position, current=self.current, elapsed=time.monotonic()-self.started))
            atomic_write(self.path, self.report); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error: self.report["failed_authority_observation"] = copy.deepcopy(self.current)
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_DASH_RPC_INPUT_NETWORK_"+("FAILED "+error if error else "READY")); ue.request_exit()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_RPC_INPUT_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPDashRPCInputNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPDashRPCInputNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
