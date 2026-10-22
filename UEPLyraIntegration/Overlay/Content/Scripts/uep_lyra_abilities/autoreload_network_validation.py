"""Two LocalOnly owners -> native reload GAS/RPC -> authority ammo replication.

Files coordinate pauses and read-only observations, never carry gameplay events.
Only authority sets native inventory tags for fixture setup and exact rollback.
"""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture, services
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from uep_lyra_hud.weapon_validation_helpers import set_stat
from uep_lyra_weapon_input import aim_snapshot
from . import autoreload_mixin as policy
from .autoreload_contract import PLAN, WEAPONS, require, validate
from .autoreload_validation import Validation as NativeAutoReload
from .jump_network_validation import Server as PlayingFixture, arg, PEERS
from . import reload_weapon_fixture as weapons
from . import reload_magazine_mixin as reload_policy


class Client(NativeAutoReload):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root, self.timeout = peer, run, Path(result).parent, 480.
        self.original_pistol = None
        self.report.update(peer=peer, run_id=run, local_inventory_written=False,
            gameplay_event_replication_tested=False, native_rpc_bypassed=False,
            packet_loss_tested=False, travel_rejoin_tested=False)

    def ready(self):
        gate = read_json(self.root/"playing-ready.json")
        if gate is None: return
        require(gate["run_id"] == self.run and gate["native_playing_phase"], "foreign/nonplaying AutoReload gate")
        NativeAutoReload.ready(self)

    def begin(self):
        require(str(self.bridge.call_function("CaptureSnapshot").NetMode) == "Client", "AutoReload owner is not a real client")
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, peer=self.peer,
            player_id=self.report["player_id"], original_ammo=self.original_ammo))
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index,
            native_ability_inactive=not self.ability.get_property("bIsActive")))
        self.enter("network-permit")

    def prepare_weapon(self, controller, model):
        if self.weapon == "pistol": return True
        if self.original_pistol is None:
            self.original_pistol = weapons.baseline(controller)
            self.report["native_weapon_fixture"] = copy.deepcopy(self.original_pistol)
            atomic_write(self.root/(self.peer+"-baseline-ready.json"), dict(run_id=self.run,
                player_id=int(controller.PlayerState.PlayerId)))
        gate = read_json(self.root/(self.peer+"-weapon-ready.json"))
        if gate is None: return False
        require((gate["run_id"], gate["weapon"]) == (self.run, self.weapon), "foreign AutoReload native equipment barrier")
        return True

    def set_ammo(self, values):
        # The standalone fixture is reused, but all its write hooks are forbidden.
        require(self.ammo() == tuple(values), "authority fixture ammo has not replicated")

    def complete_trial(self):
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run,
            peer=self.peer, index=self.index, row=copy.deepcopy(self.row)))
        self.enter("network-restored")

    def finish(self, error=None):
        if error: return self.exit_native(error)
        self.report["equipped_fixture_state_restored"] = capture(self.controller) == self.original_model
        atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def validate_report(self): validate(self.report, network=True)

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            self.close_observer()
            if hasattr(self, "original_aim"):
                self.inject(False); self.end_native()
                rotation = ue.FRotator()
                for field, value in self.original_aim.items(): setattr(rotation, field, value)
                self.controller.call_function("SetControlRotation", rotation)
                if self.weapon != "pistol":
                    self.report["temporary_weapon_removed"] = weapons.restored(self.controller, self.original_pistol)
                    self.report["original_player_restored"] = self.report["temporary_weapon_removed"] and aim_snapshot(self.controller) == self.original_aim
                    self.report["original_ability_active_restored"] = weapons.auto_active(self.controller) == self.original_pistol["original_auto_active"]
                else:
                    self.report["original_player_restored"] = capture(self.controller) == self.original_model and aim_snapshot(self.controller) == self.original_aim
                    ue.set_mixin_profile(self.ability, "Python")
                    require(self.asc.call_function("TryActivateAbilityByClass", self.cls, False), "native AutoReload default restore refused")
                    self.report["original_ability_active_restored"] = bool(self.ability.get_property("bIsActive")) and self.tasks() == 1
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_AUTORELOAD_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def tick(self, seconds):
        if not self.phase.startswith("network-"): return NativeAutoReload.tick(self, seconds)
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < self.timeout, "AutoReload network barrier timeout: "+self.phase)
            if self.phase == "network-permit":
                value = read_json(self.root/(self.peer+"-permit.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign AutoReload permit")
                    if value["index"] == self.index and self.ammo() == tuple(value["initial_ammo"]): NativeAutoReload.begin(self)
            elif self.phase == "network-restored":
                value = read_json(self.root/(self.peer+"-restored.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign AutoReload rollback")
                    if value["index"] == self.index and self.ammo() == self.original_ammo:
                        self.row["fixture_ammo_restored"] = True; self.append_side()
            else:
                value = read_json(self.root/"release.json")
                if value is not None:
                    require(value["run_id"] == self.run, "foreign AutoReload release")
                    if self.weapon != "pistol":
                        if weapons.auto_state(self.controller) is None or not weapons.restored(self.controller, self.original_pistol): return True
                        self.exit_native()
                    elif self.ammo() == self.original_ammo: self.exit_native()
            return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


class Server(PlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.ability_class, self.prepared, self.restored = policy.CLASS, False, False
        self.originals, self.items = {}, {}
        self.weapon = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoReloadWeapon=")), "pistol")
        require(self.weapon in WEAPONS, "weapon has no original authority AutoReload grant")
        self.weapon_fixtures, self.weapon_controllers, self.weapon_prepared = {}, {}, self.weapon == "pistol"
        self.report.update(schema_version=2, weapon=self.weapon, fixture_authority_inventory_setup=True, original_inventory_restored=False,
            inventory_properties_written=False, local_only_authority_activation_called=False,
            native_rpc_bypassed=False, gameplay_event_replication_tested=False)

    def ammo(self, peer):
        return tuple(int(self.items[peer].call_function("GetStatTagStackCount", GameplayTag(TagName=tag))) for tag in (policy.MAGAZINE, policy.SPARE))

    def set_ammo(self, peer, values):
        require(int(self.owners[peer]["pawn"].call_function("GetLocalRole")) == 3, "ammo fixture is not authority")
        if self.current is not None and self.current["name"] == "real-fire-auto-reload":
            self.current["authority_ammo_api_calls_after_permit"] += 1
        for tag, value in zip((policy.MAGAZINE, policy.SPARE), values): set_stat(self.items[peer], tag, value)

    def prepare_weapons(self):
        ready = {peer: read_json(self.root/(peer+"-baseline-ready.json")) for peer in PEERS}
        if not all(ready.values()): return
        require(all(row["run_id"] == self.run for row in ready.values()) and
            len({row["player_id"] for row in ready.values()}) == 2, "AutoReload equipment owners are not distinct/current")
        pawn = ue.find_object(self.report["native_playing_gate"]["stable_authority_pawns"][0][1])
        require(valid(pawn), "AutoReload stable authority pawn no longer valid")
        self.world = pawn.get_world()
        controllers, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraPlayerController"))
        for peer, row in ready.items():
            if peer in self.weapon_fixtures: continue
            matches = [controller for controller in controllers if valid(controller.PlayerState) and
                int(controller.PlayerState.PlayerId) == row["player_id"]]
            if len(matches) != 1: return
            self.weapon_controllers[peer] = matches[0]
            self.weapon_fixtures[peer] = weapons.install(matches[0], self.weapon)
        models = [capture(controller) for controller in self.weapon_controllers.values()]
        if not all(model is not None and weapons.WEAPONS[self.weapon][2] in model["definition"] for model in models): return
        self.report["native_weapon_fixtures"] = copy.deepcopy(self.weapon_fixtures)
        for peer in PEERS:
            atomic_write(self.root/(peer+"-weapon-ready.json"), dict(run_id=self.run, weapon=self.weapon))
        self.weapon_prepared = True

    def reload_active(self, peer):
        asc = ability_system(self.owners[peer]["pawn"])
        return any(valid(value) and value.get_property("bIsActive") for spec in asc.get_property("ActivatableAbilities").Items
            if valid(spec.Ability) and "GA_Weapon_Reload" in spec.Ability.get_class().get_name()
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances))

    def prepare(self):
        for peer, owner in self.owners.items():
            model = capture(owner["controller"])
            if model is None or weapons.WEAPONS[self.weapon][2] not in model["definition"]: return
            _, quickbar = services(owner["controller"])
            self.items[peer] = quickbar.call_function("GetActiveSlotItem")
            self.originals[peer] = model
            require(not owner["ability"].get_property("bIsActive"), "LocalOnly authority unexpectedly active")
            require(int(owner["ability"].NetExecutionPolicy) == 1, "original LocalOnly policy changed")
            ready = read_json(self.root/(peer+"-ready.json"))
            require(self.ammo(peer) == tuple(ready["original_ammo"]), "original owner/authority ammo differs")
        self.report["native_equipped_autoreload_grants"] = {peer: len(weapons.auto_instances(owner["controller"])) for peer, owner in self.owners.items()}
        self.prepared = True

    def start_case(self):
        peer, index = PEERS[self.position//(len(PLAN)*2)], self.position % (len(PLAN)*2)
        request = read_json(self.root/(peer+"-request.json"))
        if request is None or request["index"] != index: return
        require(request["run_id"] == self.run and request["native_ability_inactive"], "foreign/still-active AutoReload request")
        name = PLAN[index//2]
        capacity = int(self.items[peer].call_function("GetStatTagStackCount", GameplayTag(TagName="Lyra.ShooterGame.Weapon.MagazineSize")))
        initial = (0, capacity*2) if name == "empty-spare" else ((0, 0) if name == "empty-no-spare" else (capacity, capacity*2))
        before = {key: capture(owner["controller"]) for key, owner in self.owners.items()}
        self.set_ammo(peer, initial)
        self.current = dict(target=peer, index=index, name=name, profile=("BlueprintFallback", "Python")[index % 2],
            authoritative_role=3, initial_ammo=list(initial), before_models=before,
            other_inventory_unchanged=True, local_only_authority_stayed_inactive=True,
            native_reload_active_observed=False, minimum_magazine=initial[0], authority_ammo_api_calls_after_permit=0)
        require(not self.reload_active(peer), "previous authority Reload still active at AutoReload trial start")
        self.current["native_reload_observations"] = []
        self.current["reload_policy_before"] = reload_policy.snapshot()
        self.case_started = time.monotonic()
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index, initial_ammo=initial))

    def observe(self):
        row, peer = self.current, self.current["target"]
        require(time.monotonic()-self.case_started < 30., "native AutoReload authority observation timeout")
        row["local_only_authority_stayed_inactive"] &= not self.owners[peer]["ability"].get_property("bIsActive")
        row["native_reload_active_observed"] |= self.reload_active(peer)
        row["minimum_magazine"] = min(row["minimum_magazine"], self.ammo(peer)[0])
        observed = dict(ammo=list(self.ammo(peer)), active=self.reload_active(peer), reload_policy=reload_policy.snapshot())
        history = row["native_reload_observations"]
        if not history or any(history[-1][key] != value for key, value in observed.items()):
            if len(history) < 64: history.append(dict(observed, elapsed=time.monotonic()-self.case_started))
        for key, owner in self.owners.items():
            if key != peer: row["other_inventory_unchanged"] &= capture(owner["controller"]) == row["before_models"][key]
        require(row["other_inventory_unchanged"] and row["local_only_authority_stayed_inactive"], "AutoReload foreign owner/local-only authority changed")
        ack = read_json(self.root/(peer+"-"+str(row["index"])+"-ack.json"))
        if ack is None: return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]), "foreign AutoReload ack")
        native = self.ammo(peer)
        if self.reload_active(peer) or list(native) != [ack["row"]["final_magazine"], ack["row"]["final_spare"]]: return
        row.update(authority_final_ammo=list(native), client=ack)
        after = reload_policy.snapshot()
        row["authority_reload_counts"] = {key: after[key]-row["reload_policy_before"][key] for key in
            ("activations", "native_ends", "authority_reloads", "transferred_rounds", "reload_events", "tasks_created", "scopes_created", "scopes_closed")}
        require(row["authority_ammo_api_calls_after_permit"] == 0, "authority ammo fixture wrote during real firing")
        self.current = None
        original = self.originals[peer]
        self.set_ammo(peer, (original["magazine"], original["spare"]))
        row["authority_original_restored"] = capture(self.owners[peer]["controller"]) == original
        require(row["authority_original_restored"], "authority AutoReload fixture rollback failed")
        self.report["cases"].append(copy.deepcopy(row))
        atomic_write(self.root/(peer+"-restored.json"), dict(run_id=self.run, index=row["index"]))
        ue.log("UEP_AUTORELOAD_NETWORK_CASE_OBSERVED "+peer+"/"+str(row["index"]))
        self.current = None; self.position += 1

    def restore(self):
        self.current = None
        for peer, model in self.originals.items(): self.set_ammo(peer, (model["magazine"], model["spare"]))
        self.report["original_inventory_restored"] = all(capture(self.owners[peer]["controller"]) == model for peer, model in self.originals.items())
        if self.weapon_fixtures:
            self.report["equipped_fixture_states_restored"] = self.report["original_inventory_restored"]
            for peer, state in self.weapon_fixtures.items(): weapons.restore(self.weapon_controllers[peer], state)
            self.report["temporary_weapons_removed"] = all(weapons.restored(self.weapon_controllers[peer], state) for peer, state in self.weapon_fixtures.items())
            self.report["original_inventory_restored"] = self.report["temporary_weapons_removed"]

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 480., "native AutoReload server timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.weapon_prepared: self.prepare_weapons()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS)*len(PLAN)*2:
                    complete = [read_json(self.root/(peer+"-complete.json")) for peer in PEERS]
                    if all(value is not None and value["run_id"] == self.run for value in complete):
                        if not self.restored:
                            self.restore(); self.restored = True
                            atomic_write(self.root/"release.json", dict(run_id=self.run))
                        exits = [read_json(self.root/(peer+"-exited.json")) for peer in PEERS]
                        if all(value is not None and value["exit_code"] == 0 for value in exits):
                            self.report["server_waited_for_client_process_exit"] = True; self.finish()
                elif self.current is None: self.start_case()
                else: self.observe()
            atomic_write(self.root/"server-status.json", dict(position=self.position, prepared=self.prepared,
                current=self.current, elapsed_seconds=time.monotonic()-self.started))
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error and (self.prepared or self.weapon_fixtures):
            try: self.restore()
            except Exception: error += traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_AUTORELOAD_NETWORK_"+("FAILED "+error if error else "READY"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_AUTORELOAD_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPAutoReloadNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPAutoReloadNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
