"""Two native predicted owners; authority effects/health/input, no event replay."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayEffectQuery
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from . import hero_heal_mixin as policy
from .hero_heal_contract import NETWORK_PLAN, require
from .hero_heal_validation import Validation as NativeHeal, INPUT_ID
from .jump_network_validation import Server as PlayingFixture, arg, PEERS

def instances(asc, cls):
    return [value for spec in asc.get_property("ActivatableAbilities").Items
        if valid(spec.Ability) and spec.Ability.get_class() == cls
        for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]


def specs(asc):
    return sorted(value.get_path_name() for spec in asc.get_property("ActivatableAbilities").Items
        for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value))


class Client(NativeHeal):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root = peer, run, Path(result).parent
        self.plan, self.timeout = NETWORK_PLAN, 480.
        self.network_fixture = True
        self.report.update(peer=peer, run_id=run, local_health_written=False, local_ability_granted=False,
            native_rpc_bypassed=False, gameplay_event_replication_tested=False,
            packet_loss_tested=False, travel_rejoin_tested=False)

    def ready(self):
        value = read_json(self.root/"playing-ready.json")
        if value is None: return
        require(value["run_id"] == self.run and value["native_playing_phase"], "foreign/nonplaying Hero Heal gate")
        NativeHeal.ready(self)

    def grant_ability(self):
        require(str(self.bridge.call_function("CaptureSnapshot").NetMode) == "Client", "Hero Heal owner is not native client")
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"], original_health=self.original_health))
        value = read_json(self.root/"granted.json")
        if value is not None:
            require(value["run_id"] == self.run, "foreign Hero Heal grant")
            if len(instances(self.asc, self.cls)) == 1: self.attach_ability()

    def set_health(self, value):
        require(abs(self.health()-value) < .01, "authority Health fixture has not replicated")

    def begin(self):
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def complete_trial(self):
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, peer=self.peer,
            index=self.index, row=copy.deepcopy(self.row)))
        self.enter("network-confirm")

    def may_perform_action(self):
        value = read_json(self.root/(self.peer+"-action-ready.json"))
        if value is None: return False
        require(value["run_id"] == self.run, "foreign Hero Heal authority action gate")
        return value["index"] == self.index and value["actual_authority_first_heal"]

    def finish(self, error=None):
        if error: return self.exit_native(error)
        atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_HERO_HEAL_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def tick(self, seconds):
        if not self.phase.startswith("network-"): return NativeHeal.tick(self, seconds)
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < self.timeout, "native Hero Heal owner barrier timeout: "+self.phase)
            suffix = {"network-permit": "permit", "network-confirm": "confirm", "network-restored": "restored"}.get(self.phase)
            value = read_json(self.root/(self.peer+"-"+suffix+".json")) if suffix else read_json(self.root/"release.json")
            if value is None: return True
            require(value["run_id"] == self.run, "foreign Hero Heal owner barrier")
            if suffix and value["index"] != self.index: return True
            if self.phase == "network-permit":
                if abs(self.health()-75.) < .01: NativeHeal.begin(self)
            elif self.phase == "network-confirm":
                if abs(self.health()-value["authority_health"]) < .01 and self.effects() == self.original_effects and self.tasks() == 0:
                    self.row.update(health_after=self.health(), authority_health_confirmed=True,
                        native_heal_effects_restored=True, tasks_after_end=0)
                    atomic_write(self.root/(self.peer+"-"+str(self.index)+"-final-ack.json"), dict(run_id=self.run,
                        peer=self.peer, index=self.index, row=copy.deepcopy(self.row)))
                    self.enter("network-restored")
            elif self.phase == "network-restored":
                if abs(self.health()-self.original_health) < .01:
                    self.row["fixture_health_restored"] = True; self.append_side()
            elif self.specs() == self.original_specs and abs(self.health()-self.original_health) < .01:
                self.report["original_player_restored"] = capture(self.controller) == self.original_model and not self.ignored()
                self.report["original_ability_specs_restored"] = True
                self.exit_native()
            return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


class Server(PlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.cls, self.grants, self.originals, self.commands = None, {}, {}, 0
        self.report.update(fixture_authority_grant_and_health=True, original_player_states_restored=False,
            original_ability_specs_restored=False, health_properties_written=False, native_rpc_bypassed=False,
            activation_handler_replayed=False, task_callbacks_replayed=False, animation_assets_modified=False,
            original_montage_or_effect_written=False, gameplay_event_replication_tested=False)
        self.report.update(authority_input_baseline_fixture=True, native_input_locks_suspended={}, native_input_locks_restored={})
        self.restored = False

    def health(self, peer): return float(self.owners[peer]["health"].call_function("GetHealth"))
    def effects(self, peer):
        owner = self.owners[peer]
        return len(owner["asc"].call_function("GetActiveEffects", GameplayEffectQuery(EffectDefinition=owner["ability"].GE_Heal)))
    def tasks(self, peer): return sum(valid(task) for task in self.owners[peer]["ability"].get_property("ActiveTasks"))

    def set_health(self, peer, value):
        delta = value-self.health(peer)
        if abs(delta) < .01: return
        self.commands += 1
        result = self.bridge.call_function("ApplyAuthorityHealthDeltaToPlayer", "hero-heal-net."+str(self.commands), delta,
            self.owners[peer]["player_token"])
        require(result.bApplied and abs(result.HealthAfter-value) < .01 and str(result.TargetActor) == self.owners[peer]["pawn"].get_path_name(),
            "bounded authority Hero Heal Health/target refused: "+str(result.Status))

    def setup(self):
        ready = {peer: read_json(self.root/(peer+"-ready.json")) for peer in PEERS}
        if not all(ready.values()): return
        require(all(value["run_id"] == self.run for value in ready.values()) and len({value["player_id"] for value in ready.values()}) == 2,
            "Hero Heal owners are not distinct")
        if self.cls is None: self.cls = ue.load_class(policy.CLASS)
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5) or "L_Expanse" not in world.get_name(): continue
            self.world = world
            self.bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            snapshots = {int(value.PlayerId): value for value in self.bridge.call_function("CapturePlayerSnapshots")}
            controllers, = self.statics.call_function("GetAllActorsOfClass", world, ue.find_class("LyraPlayerController"))
            for peer in PEERS:
                if peer in self.owners: continue
                matches = [value for value in controllers if valid(value.PlayerState) and int(value.PlayerState.PlayerId) == ready[peer]["player_id"]]
                if len(matches) != 1: continue
                controller = matches[0]; pawn = controller.get_controlled_pawn(); asc = ability_system(pawn)
                model = capture(controller)
                if model is None: continue
                require(not any(spec.InputID == INPUT_ID for spec in asc.get_property("ActivatableAbilities").Items) and not instances(asc, self.cls),
                    "do not replace original ability/input bindings")
                health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
                self.originals[peer] = dict(model=model, health=float(health.call_function("GetHealth")), specs=specs(asc),
                    input_ignored=bool(controller.call_function("IsMoveInputIgnored")))
                # The retained BP releases twice on native End (end + state).
                # Isolate that known baseline defect from routine comparison.
                # Count native pops, never reset or read/write the raw counter;
                # restore exactly the same number after the fixture finishes.
                suspended = 0
                while controller.call_function("IsMoveInputIgnored"):
                    require(suspended < 16, "authority input baseline fixture exceeded bounded native stack")
                    controller.call_function("SetIgnoreMoveInput", False); suspended += 1
                self.report["native_input_locks_suspended"][peer] = suspended
                require(abs(self.originals[peer]["health"]-ready[peer]["original_health"]) < .01, "original owner/authority Health differs")
                self.grants[peer] = asc.call_function("K2_GiveAbility", self.cls, 1, INPUT_ID)
                values = instances(asc, self.cls)
                require(len(values) == 1, "authority native Hero Heal grant failed")
                self.owners[peer] = dict(controller=controller, pawn=pawn, asc=asc, health=health, ability=values[0],
                    player_id=ready[peer]["player_id"], player_token=str(snapshots[ready[peer]["player_id"]].PlayerToken))
            if set(self.owners) == set(PEERS):
                self.report["player_ids"] = {peer: value["player_id"] for peer, value in self.owners.items()}
                atomic_write(self.root/"granted.json", dict(run_id=self.run)); return

    def start_case(self):
        peer, index = PEERS[self.position//(len(NETWORK_PLAN)*2)], self.position % (len(NETWORK_PLAN)*2)
        value = read_json(self.root/(peer+"-request.json"))
        if value is None or value["index"] != index: return
        require(value["run_id"] == self.run, "foreign Hero Heal native request")
        owner = self.owners[peer]
        require(not owner["ability"].get_property("bIsActive") and self.effects(peer) == 0, "previous authority Hero Heal not clean")
        profile = ("BlueprintFallback", "Python")[index % 2]
        ue.set_mixin_profile(owner["ability"], profile)
        self.before = policy.snapshot(); self.set_health(peer, 75.)
        self.current = dict(target=peer, index=index, name=NETWORK_PLAN[index//2], profile=profile, authoritative_role=int(owner["pawn"].call_function("GetLocalRole")),
            native_active_observed=False, native_effect_observed=False, native_movement_lock_observed=False,
            native_task_triple_observed=False, native_first_heal_observed=False, foreign_owner_unchanged=True)
        self.case_started = time.monotonic()
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        require(time.monotonic()-self.case_started < 20., "native Hero Heal authority confirmation timeout")
        owner = self.owners[peer]; ability = owner["ability"]
        row["native_active_observed"] |= bool(ability.get_property("bIsActive"))
        row["native_effect_observed"] |= self.effects(peer) > 0
        row["native_movement_lock_observed"] |= bool(owner["controller"].call_function("IsMoveInputIgnored"))
        row["native_task_triple_observed"] |= self.tasks(peer) == 3
        row["native_first_heal_observed"] |= self.health(peer) > 75.
        if row["native_active_observed"] and row["native_effect_observed"] and row["native_task_triple_observed"] and row["native_first_heal_observed"]:
            atomic_write(self.root/(peer+"-action-ready.json"), dict(run_id=self.run, index=row["index"], actual_authority_first_heal=True))
        for key, foreign in self.owners.items():
            if key != peer:
                actual = dict(model=capture(foreign["controller"]), health=self.health(key),
                    input_ignored=bool(foreign["controller"].call_function("IsMoveInputIgnored")))
                row["foreign_observation"] = dict(peer=key, original=self.originals[key], current=actual)
                row["foreign_owner_unchanged"] &= (actual["model"] == self.originals[key]["model"] and
                    actual["health"] == self.originals[key]["health"] and actual["input_ignored"] is False)
        require(row["foreign_owner_unchanged"], "Hero Heal altered foreign owner health/equipment/input")
        ack = read_json(self.root/(peer+"-"+str(row["index"])+"-ack.json"))
        if ack is None or ability.get_property("bIsActive"): return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]), "foreign Hero Heal ack")
        row.update(authority_health=self.health(peer), authority_effects_after=self.effects(peer), authority_tasks_after=self.tasks(peer),
            authority_movement_baseline_restored=not owner["controller"].call_function("IsMoveInputIgnored"))
        atomic_write(self.root/(peer+"-confirm.json"), dict(run_id=self.run, index=row["index"], authority_health=row["authority_health"]))
        final = read_json(self.root/(peer+"-"+str(row["index"])+"-final-ack.json"))
        if final is None: return
        require((final["run_id"], final["peer"], final["index"]) == (self.run, peer, row["index"]), "foreign Hero Heal final ack")
        row["client"] = final
        stats = policy.snapshot(); row["authority_counters"] = {key: value-self.before[key] for key, value in stats.items() if type(value) is int and key != "active_count"}
        self.set_health(peer, self.originals[peer]["health"])
        row["authority_original_restored"] = self.health(peer) == self.originals[peer]["health"] and capture(owner["controller"]) == self.originals[peer]["model"]
        self.report["cases"].append(copy.deepcopy(row))
        atomic_write(self.root/("authority-"+str(self.position)+".json"), dict(run_id=self.run, row=copy.deepcopy(row)))
        atomic_write(self.root/(peer+"-restored.json"), dict(run_id=self.run, index=row["index"]))
        ue.log("UEP_HERO_HEAL_NETWORK_CASE_OBSERVED "+peer+"/"+str(row["index"]))
        self.current = None; self.position += 1

    def restore(self):
        for peer, owner in self.owners.items():
            if valid(owner["ability"]) and owner["ability"].get_property("bIsActive"): owner["ability"].call_function("K2_EndAbility")
            if peer in self.grants: owner["asc"].call_function("ClearAbility", self.grants.pop(peer))
            self.set_health(peer, self.originals[peer]["health"])
            if peer not in self.report["native_input_locks_restored"]:
                count = self.report["native_input_locks_suspended"][peer]
                for unused in range(count): owner["controller"].call_function("SetIgnoreMoveInput", True)
                self.report["native_input_locks_restored"][peer] = count
        self.report["original_player_states_restored"] = all(self.health(peer) == self.originals[peer]["health"] and
            capture(owner["controller"]) == self.originals[peer]["model"] and
            bool(owner["controller"].call_function("IsMoveInputIgnored")) == self.originals[peer]["input_ignored"] for peer, owner in self.owners.items())
        self.report["original_ability_specs_restored"] = all(specs(owner["asc"]) == self.originals[peer]["specs"] for peer, owner in self.owners.items())

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native Hero Heal authority timeout")
            if not self.playing_gate: self.wait_playing()
            elif set(self.owners) != set(PEERS): self.setup()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(NETWORK_PLAN)*len(PEERS)*2:
                    complete = [read_json(self.root/(peer+"-complete.json")) for peer in PEERS]
                    if all(value is not None and value["run_id"] == self.run for value in complete):
                        if not self.restored:
                            self.restore(); self.restored = True; atomic_write(self.root/"release.json", dict(run_id=self.run))
                        exits = [read_json(self.root/(peer+"-exited.json")) for peer in PEERS]
                        if all(value is not None and value["exit_code"] == 0 for value in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(position=self.position, owners=list(self.owners),
                current=self.current, elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error:
            self.report["failed_authority_observation"] = copy.deepcopy(self.current)
            self.report["originals"] = copy.deepcopy(self.originals)
        if error and self.owners and not self.restored:
            try: self.restore()
            except Exception: error += traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_HERO_HEAL_NETWORK_"+("FAILED "+error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_HERO_HEAL_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPHeroHealNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPHeroHealNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
