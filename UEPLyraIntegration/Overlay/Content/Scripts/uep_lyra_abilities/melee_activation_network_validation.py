"""Native predicted Melee requests, authority montage barrier, no damage fixture writes."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from .jump_network_validation import Server as Playing, arg
from .auto_respawn_helpers_validation import Validation as Ready, specs
from .auto_respawn_helpers_network_validation import token
from .melee_activation_validation import Validation as Single, config, path, vector
from .melee_hit_montage_mixin import CLASS
from . import melee_activation_mixin as policy
from .melee_activation_network_contract import TRIALS, require, client


def counters(ability, before):
    after = policy.instance_snapshot(ability)
    return {key: after.get(key, 0)-before.get(key, 0) for key in set(after)|set(before)}
def tasks(ability):
    values = [task for task in ability.get_property("ActiveTasks") if valid(task)]
    return dict(count=len(values), montage=any(task.is_a(ue.find_class("AbilityTask_PlayMontageAndWait")) for task in values),
        root=any(task.is_a(ue.find_class("AbilityTask_ApplyRootMotionConstantForce")) for task in values))
def equipment(pawn):
    manager = pawn.call_function("GetComponentByClass", ue.find_class("LyraEquipmentManagerComponent"))
    values = manager.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance"))
    require(values and values[0].is_a(ue.load_class(policy.WEAPON)), "actual equipped first native Melee weapon required")
    return dict(weapon=path(values[0]), montage=path(values[0].get_property("MeleeAttackMontage")))


class Client(Single):
    def __init__(self, result, peer, run):
        super().__init__(result); self.peer, self.run, self.root = peer, run, self.path.parent
        self.require_local_playing_phase = False; self.report.update(peer=peer, run_id=run, native_network_activation_tested=True)
    def ready(self):
        if token(self.root, "playing-ready.json", self.run) is not None: Ready.ready(self)
    def begin(self):
        super().begin(); self.report.update(player_id=int(self.controller.PlayerState.PlayerId),
            native_net_mode=str(ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world).call_function("CaptureSnapshot").NetMode))
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
    def start(self):
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index)); self.enter("permit")
    def prepare(self):
        permission = token(self.root, self.peer+"-permit.json", self.run)
        if permission is None or permission["index"] != self.index: return
        if self.melee.get_property("bIsActive") or self.melee.call_function("GetCooldownTimeRemaining") > 0: return
        name, profile = TRIALS[self.index]; ue.set_mixin_profile(self.melee, profile)
        self.before = policy.instance_snapshot(self.melee); self.health_before = self.healths(); self.intervened = False
        self.row = dict(index=self.index, name=name, profile=profile, equipment=equipment(self.pawn),
            native_active_observed=False, native_montage_task_observed=False, native_root_task_observed=False, intervention=None)
        self.enter("settle")
    def observe(self):
        require(time.monotonic()-self.phase_started < 14., "native Melee owner montage/end timeout")
        self.sample(); elapsed = self.game_time()-self.game_started
        if self.row["name"] != "natural" and not self.intervened:
            confirmation = token(self.root, self.peer+"-"+str(self.index)+"-active.json", self.run)
            if confirmation is not None and elapsed >= .07:
                require(self.melee.get_property("bIsActive") and self.tasks()["montage"] and confirmation["native_activation_and_montage"] is True,
                    "owner intervention missed confirmed actual native montage")
                self.intervened = True; action = dict(active_before=True, authority_confirmed=True, time=elapsed)
                if self.row["name"] == "cancel":
                    action["native_entry"] = "GameplayAbility.K2_CancelAbility"; self.melee.call_function("K2_CancelAbility")
                else:
                    action["native_entry"] = "ue.set_mixin_profile"
                    ue.set_mixin_profile(self.melee, "Python" if self.row["profile"] == "BlueprintFallback" else "BlueprintFallback")
                    action["new_profile"] = str(ue.get_mixin_profile(self.melee))
                action["active_after"] = bool(self.melee.get_property("bIsActive")); self.row["intervention"] = action
            require(self.intervened or elapsed < .4, "authority montage confirmation too late for actual intervention")
        if self.melee.get_property("bIsActive") or self.melee.call_function("GetCooldownTimeRemaining") > 0: return
        self.quiet_before = policy.instance_snapshot(self.melee); self.quiet_ticks = 0; self.enter("quiet")
    def quiet(self):
        require(policy.instance_snapshot(self.melee) == self.quiet_before and self.healths() == self.health_before, "late owner callback/damage")
        self.quiet_ticks += 1
        if self.quiet_ticks < 20: return
        self.row.update(stats=counters(self.melee, self.before), native_ended=not bool(self.melee.get_property("bIsActive")),
            native_tasks_after=self.tasks()["count"], quiet_ticks=self.quiet_ticks,
            actual_scope_closed=getattr(self.melee, "_uep_melee_montage_scope", None) is None, all_pawn_health_unchanged=True,
            specs_unchanged=specs(self.asc) == self.original["specs"], config_unchanged=config(self.melee) == self.original["config"])
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, peer=self.peer, index=self.index, row=self.row)); self.enter("authority")
    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360., "native Melee owner total timeout")
            if self.phase == "permit": self.prepare(); self.write(); return True
            if self.phase == "authority":
                ack = token(self.root, self.peer+"-accepted.json", self.run)
                if ack is not None and ack["index"] == self.index:
                    self.report["cases"].append(copy.deepcopy(self.row)); self.index += 1
                    if self.index == len(TRIALS):
                        self.cleanup(); atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run)); self.enter("release")
                    else: self.enter("start")
                self.write(); return True
            if self.phase == "release":
                if token(self.root, "release.json", self.run) is not None: self.finish()
                return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
        return super().tick(delta)
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; client(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_MELEE_ACTIVATION_SHUTDOWN_"+self.report["status"].upper())


class Server(Playing):
    def __init__(self, result, run):
        super().__init__(result, run); self.ability_class = CLASS; self.position = 0; self.current = None; self.prepared = self.released = False
        self.report.update(actual_ability_class=CLASS, native_network_activation_tested=True, activation_event_replayed=False,
            task_callbacks_replayed=False, ability_granted_by_fixture=False, health_or_raw_velocity_written=False,
            trace_damage_business_migrated=False, request_entry="actual remote native GAS activation", cases=[])
    def healths(self): return Single.healths(self)
    def state(self, peer):
        owner = self.owners[peer]; pawn, ability = owner["pawn"], owner["ability"]
        return dict(pawn=path(pawn), location=vector(pawn.get_actor_location()), velocity=vector(pawn.call_function("GetVelocity")),
            active=bool(ability.get_property("bIsActive")), specs=specs(ability_system(pawn)), config=config(ability),
            profile=str(ue.get_mixin_profile(ability)), equipment=equipment(pawn))
    def prepare(self):
        if any(value["ability"].get_property("bIsActive") for value in self.owners.values()): return
        self.originals = {peer: dict(profile=str(ue.get_mixin_profile(value["ability"])), specs=specs(ability_system(value["pawn"])),
            config=config(value["ability"]), location=value["pawn"].get_actor_location(), rotation=value["pawn"].get_actor_rotation()) for peer, value in self.owners.items()}
        self.report.update(actual_granted_primary_instances=True,
            native_net_mode=str(ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world).call_function("CaptureSnapshot").NetMode))
        self.prepared = True
    def start_case(self):
        peer, index = ("A", "B0")[self.position//len(TRIALS)], self.position%len(TRIALS)
        request = token(self.root, peer+"-request.json", self.run)
        if request is None or request["index"] != index: return
        owner = self.owners[peer]; pawn, ability = owner["pawn"], owner["ability"]
        if ability.get_property("bIsActive") or ability.call_function("GetCooldownTimeRemaining") > 0: return
        require(pawn.call_function("K2_TeleportTo", self.originals[peer]["location"], self.originals[peer]["rotation"]), "authority native fixture reset refused")
        pawn.call_function("ForceNetUpdate"); name, profile = TRIALS[index]; ue.set_mixin_profile(ability, profile)
        self.before = policy.instance_snapshot(ability); self.health_before = self.healths()
        self.other = {key: self.state(key) for key in self.owners if key != peer}; self.case_started = time.monotonic(); self.quiet_ticks = 0; self.quiet_before = None
        self.current = dict(target=peer, index=index, name=name, profile=profile, native_role=int(pawn.call_function("GetLocalRole")),
            equipment=equipment(pawn), native_active_observed=False, native_montage_task_observed=False, native_root_task_observed=False, authority_ready_sent=False)
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))
    def observe(self):
        value = self.current; peer = value["target"]; owner = self.owners[peer]; ability = owner["ability"]; state = tasks(ability)
        require(time.monotonic()-self.case_started < 20., "native Melee authority/owner case timeout")
        require(self.healths() == self.health_before and all(self.state(key) == before for key, before in self.other.items()), "native Melee changed foreign owner or Health")
        value["native_active_observed"] |= bool(ability.get_property("bIsActive")); value["native_montage_task_observed"] |= state["montage"]; value["native_root_task_observed"] |= state["root"]
        if ability.get_property("bIsActive") and state["montage"] and not value["authority_ready_sent"]:
            value["authority_ready_sent"] = True
            atomic_write(self.root/(peer+"-"+str(value["index"])+"-active.json"), dict(run_id=self.run, index=value["index"], native_activation_and_montage=True))
        ack = token(self.root, peer+"-"+str(value["index"])+"-ack.json", self.run)
        if ack is None or ability.get_property("bIsActive") or ability.call_function("GetCooldownTimeRemaining") > 0: return
        after = policy.instance_snapshot(ability)
        if self.quiet_before is None: self.quiet_before = copy.deepcopy(after)
        require(after == self.quiet_before, "late authority Melee callback"); self.quiet_ticks += 1
        if self.quiet_ticks < 20: return
        value.update(client=ack, stats=counters(ability, self.before), native_ended=True, native_tasks_after=state["count"],
            quiet_ticks=self.quiet_ticks, actual_scope_closed=getattr(ability, "_uep_melee_montage_scope", None) is None,
            all_pawn_health_unchanged=True, foreign_owner_unchanged=True, specs_unchanged=specs(ability_system(owner["pawn"])) == self.originals[peer]["specs"],
            config_unchanged=config(ability) == self.originals[peer]["config"])
        self.report["cases"].append(copy.deepcopy(value)); atomic_write(self.root/(peer+"-accepted.json"), dict(run_id=self.run, index=value["index"]))
        self.position += 1; self.current = None
    def restore(self):
        for peer, value in self.owners.items(): ue.set_mixin_profile(value["ability"], self.originals[peer]["profile"])
        self.report.update(profiles_restored=all(str(ue.get_mixin_profile(value["ability"])) == self.originals[peer]["profile"] for peer, value in self.owners.items()),
            specs_config_unchanged=all(specs(ability_system(value["pawn"])) == self.originals[peer]["specs"] and config(value["ability"]) == self.originals[peer]["config"] for peer, value in self.owners.items()), shutdown=policy.snapshot())
    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360., "native Melee authority total timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == 2*len(TRIALS):
                    if all(token(self.root, peer+"-complete.json", self.run) is not None for peer in ("A", "B0")):
                        if not self.released: self.restore(); atomic_write(self.root/"release.json", dict(run_id=self.run)); self.released = True
                        exits = [token(self.root, peer+"-exited.json", self.run) for peer in ("A", "B0")]
                        if all(value is not None and value["exit_code"] == 0 for value in exits): self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.path, self.report); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_MELEE_ACTIVATION_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPMeleeActivationNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPMeleeActivationNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
