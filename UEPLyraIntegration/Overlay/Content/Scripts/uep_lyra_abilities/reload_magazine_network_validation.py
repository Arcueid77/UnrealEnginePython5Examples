"""Predicted owner reload -> native GAS RPC -> authority ammo and owner replica."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture, services
from uep_lyra_world.effect_pad_mixin import valid
from . import reload_magazine_mixin as policy
from . import reload_weapon_fixture as weapons
from .reload_magazine_validation import Validation as NativeReload, PISTOL, AUTO
from .reload_magazine_contract import NETWORK_PLAN as PLAN, REFUSED, EARLY, require
from .jump_network_validation import Server as PlayingFixture, arg, PEERS

class Client(NativeReload):
    def __init__(self, result, peer, run):
        super().__init__(result)
        self.peer, self.run, self.root, self.network_fixture, self.plan = peer, run, Path(result).parent, True, PLAN
        self.original_pistol = None
        self.equipment_observer = None
        self.observe_equipment = "-UEPWeaponInstanceIntegration" in sys.argv
        self.report.update(peer=peer, run_id=run, local_inventory_written=False, native_rpc_bypassed=False,
            gameplay_event_replication_tested=False, packet_loss_tested=False, travel_rejoin_tested=False, network_pause_tested=False)

    def ready(self):
        gate = read_json(self.root/"playing-ready.json")
        if gate is None: return
        require(gate["run_id"] == self.run and gate["native_playing_phase"], "foreign/nonplaying reload gate")
        NativeReload.ready(self)

    def begin(self):
        if self.equipment_observer is not None: self.equipment_observer.note_initial(self.controller)
        self.report["native_net_mode"] = str(self.bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_net_mode"] == "Client", "reload owner is not a native client")
        self.report["player_id"] = int(self.controller.PlayerState.PlayerId)
        atomic_write(self.root/(self.peer+"-ready.json"), dict(run_id=self.run, player_id=self.report["player_id"]))
        atomic_write(self.root/(self.peer+"-request.json"), dict(run_id=self.run, index=self.index))
        self.enter("network-permit")

    def prepare_weapon(self, controller, model):
        if self.observe_equipment and self.equipment_observer is None:
            from uep_lyra_weapons.weapon_instance_network_observer import Observer
            self.equipment_observer = Observer(self.peer)
        if self.weapon == "pistol": return True
        if self.original_pistol is None:
            self.original_pistol = weapons.baseline(controller)
            self.report["native_weapon_fixture"] = dict(copy.deepcopy(self.original_pistol), weapon=self.weapon)
            atomic_write(self.root/(self.peer+"-baseline-ready.json"), dict(run_id=self.run, player_id=int(controller.PlayerState.PlayerId)))
        gate = read_json(self.root/(self.peer+"-weapon-ready.json"))
        if gate is None: return False
        require((gate["run_id"], gate["weapon"]) == (self.run, self.weapon), "foreign native weapon grant barrier")
        return True

    def set_ammo(self, values): require(self.ammo() == tuple(values), "authority reload fixture ammo not yet replicated")

    def may_perform_action(self):
        gate = read_json(self.root/(self.peer+"-"+str(self.index)+"-held.json"))
        if gate is None: return False
        require((gate["run_id"], gate["index"]) == (self.run, self.index), "foreign native reload active barrier")
        return True

    def complete_trial(self):
        atomic_write(self.root/(self.peer+"-"+str(self.index)+"-ack.json"), dict(run_id=self.run, peer=self.peer,
            index=self.index, row=copy.deepcopy(self.row)))
        self.enter("network-restored")

    def may_capture_end(self):
        # Ability End and inventory FastArray replication are different native
        # transports. Do not freeze a predicted pre-replication ammo snapshot.
        expected = self.row["initial_ammo"] if self.name in REFUSED or self.name in EARLY else self.row["expected_ammo"]
        return self.ammo() == tuple(expected)

    def finish(self, error=None):
        if error: return self.exit_native(error)
        if self.weapon != "pistol":
            self.report["equipped_fixture_state_restored"] = self.ammo() == self.original_ammo and capture(self.controller) == self.original_model
        atomic_write(self.root/(self.peer+"-complete.json"), dict(run_id=self.run, peer=self.peer))
        self.enter("network-complete")

    def exit_native(self, error=None):
        if self.finished: return
        self.finished = True
        if error and hasattr(self, "row"): self.report["failed_trial_observation"] = copy.deepcopy(self.row)
        try:
            if hasattr(self, "action"): self.controller.inject_enhanced_input_for_action(self.action, False)
            self.close_observer()
            if self.weapon != "pistol" and self.original_pistol is not None:
                self.report["temporary_weapon_removed"] = weapons.restored(self.controller, self.original_pistol)
                self.report["original_player_restored"] = self.report["temporary_weapon_removed"] and not self.no_firing()
                self.report["original_autoreload_active_restored"] = weapons.auto_active(self.controller) == self.original_pistol["original_auto_active"]
            elif hasattr(self, "ability"):
                if self.ability.get_property("bIsActive"): self.ability.call_function("K2_EndAbility")
                ue.set_mixin_profile(self.ability, "Python")
                self.report["original_player_restored"] = self.ammo() == self.original_ammo and capture(self.controller) == self.original_model and not self.no_firing()
                if self.original_auto_active and not self.auto.get_property("bIsActive"):
                    require(self.asc.call_function("TryActivateAbilityByClass", ue.load_class(AUTO), False), "native owner AutoReload restore refused")
                self.report["original_autoreload_active_restored"] = bool(self.auto.get_property("bIsActive")) == self.original_auto_active
        except Exception: error = (error or "")+traceback.format_exc()
        if self.equipment_observer is not None: self.report["equipment_integration"] = self.equipment_observer.close()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_RELOAD_MAGAZINE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def tick(self, seconds):
        if not self.phase.startswith("network-"): return NativeReload.tick(self, seconds)
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 600., "native owner reload barrier timeout")
            if self.phase == "network-permit":
                value = read_json(self.root/(self.peer+"-permit.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign native reload permit")
                    self.name = self.plan[self.index//2]
                    if value["index"] == self.index and self.ammo() == self.initial_ammo(): NativeReload.begin(self)
            elif self.phase == "network-restored":
                value = read_json(self.root/(self.peer+"-restored.json"))
                if value is not None:
                    require(value["run_id"] == self.run, "foreign native reload restoration")
                    if value["index"] == self.index and self.ammo() == self.original_ammo and capture(self.controller) == self.original_model:
                        self.row["fixture_ammo_restored"] = True; self.sides.append(copy.deepcopy(self.row))
                        if self.index % 2:
                            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
                            ue.log("UEP_RELOAD_MAGAZINE_CASE_OBSERVED "+self.name)
                        self.index += 1
                        if self.index == len(self.plan)*2: self.finish()
                        else: self.begin()
            elif self.phase == "network-complete":
                value = read_json(self.root/"release.json")
                if value is not None:
                    require(value["run_id"] == self.run, "foreign native reload release")
                    if self.equipment_observer is not None and not self.equipment_observer.ready_to_close(): return True
                    if self.weapon != "pistol":
                        state = weapons.auto_state(self.controller)
                        if state is None or not weapons.restored(self.controller, self.original_pistol): return True
                    self.exit_native()
            return not self.finished
        except Exception: self.exit_native(traceback.format_exc()); return False


class Server(PlayingFixture):
    def __init__(self, result, run):
        super().__init__(result, run)
        self.weapon = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPReloadWeapon=")), "pistol")
        require(self.weapon in weapons.WEAPONS, "unknown authority reload weapon")
        self.ability_class, self.prepared, self.released = weapons.WEAPONS[self.weapon][0], False, False
        self.originals, self.original_models = {}, {}
        self.weapon_fixtures, self.weapon_controllers, self.weapon_prepared = {}, {}, self.weapon == "pistol"
        self.equipment_observer = None
        self.observe_equipment = "-UEPWeaponInstanceIntegration" in sys.argv
        self.report.update(fixture_authority_inventory_setup=True, original_player_states_restored=False,
            native_rpc_bypassed=False, inventory_properties_written=False, gameplay_event_replication_tested=False, network_pause_tested=False, weapon=self.weapon)

    def prepare_weapons(self):
        ready = {peer: read_json(self.root/(peer+"-baseline-ready.json")) for peer in PEERS}
        if not all(ready.values()): return
        if self.observe_equipment and self.equipment_observer is None:
            from uep_lyra_weapons.weapon_instance_network_observer import Observer
            self.equipment_observer = Observer("server")
        require(all(value["run_id"] == self.run for value in ready.values()) and len({value["player_id"] for value in ready.values()}) == 2,
            "native weapon fixture owners are not distinct/current")
        # World Partition can expose several matching subworlds. Use the actual
        # stable authority Pawn already verified by the native Playing gate.
        pawn = ue.find_object(self.report["native_playing_gate"]["stable_authority_pawns"][0][1])
        require(valid(pawn), "native Playing authority Pawn no longer valid")
        self.world = pawn.get_world()
        controllers, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraPlayerController"))
        for peer, row in ready.items():
            if peer in self.weapon_fixtures: continue
            matches = [controller for controller in controllers if valid(controller.PlayerState) and int(controller.PlayerState.PlayerId) == row["player_id"]]
            if len(matches) != 1: return
            self.weapon_controllers[peer] = matches[0]
            self.weapon_fixtures[peer] = weapons.install(matches[0], self.weapon)
        models = [capture(controller) for controller in self.weapon_controllers.values()]
        if not all(model is not None and weapons.WEAPONS[self.weapon][2] in model["definition"] for model in models): return
        self.report["native_weapon_fixtures"] = copy.deepcopy(self.weapon_fixtures)
        for peer in PEERS:
            atomic_write(self.root/(peer+"-weapon-ready.json"), dict(run_id=self.run, weapon=self.weapon))
        self.weapon_prepared = True

    def select(self, peer):
        self.controller = self.owners[peer]["controller"]; self.ability = self.owners[peer]["ability"]
        _, quickbar = services(self.controller)
        self.item = quickbar.call_function("GetActiveSlotItem")
        self.pawn, self.capacity = self.owners[peer]["pawn"], self.originals[peer][1]
        self.anim = self.pawn.Mesh.call_function("GetAnimInstance")

    def prepare(self):
        values = {peer: capture(owner["controller"]) for peer, owner in self.owners.items()}
        if not all(values.values()): return
        self.original_models = values
        if self.equipment_observer is not None:
            for owner in self.owners.values(): self.equipment_observer.note_initial(owner["controller"])
        self.report["native_equipped_autoreload_grants"] = {peer: len(weapons.auto_instances(owner["controller"])) for peer, owner in self.owners.items()}
        for peer, owner in self.owners.items():
            _, quickbar = services(owner["controller"])
            self.originals[peer] = policy.ammo(quickbar.call_function("GetActiveSlotItem"))
            self.select(peer)
            require(not NativeReload.no_firing(self), "do not overwrite authority foreign NoFiring")
        self.prepared = True

    def start_case(self):
        peer, index = PEERS[self.position//(len(PLAN)*2)], self.position % (len(PLAN)*2)
        value = read_json(self.root/(peer+"-request.json"))
        if value is None or value["index"] != index: return
        require(value["run_id"] == self.run, "foreign native reload request")
        self.select(peer)
        require(capture(self.controller) == self.original_models[peer] and not self.ability.get_property("bIsActive") and
            not NativeReload.no_firing(self), "authority reload original state not restored")
        self.name = PLAN[index//2]; ue.set_mixin_profile(self.ability, ("BlueprintFallback", "Python")[index % 2])
        initial = NativeReload.initial_ammo(self); NativeReload.set_ammo(self, initial)
        self.before, self.case_started = policy.snapshot(), time.monotonic()
        self.current = dict(target=peer, index=index, name=self.name, authoritative_role=int(self.pawn.call_function("GetLocalRole")), initial_ammo=initial,
            authority_active_observed=False, authority_tasks_observed=0, authority_montage_playing_observed=False,
            authority_expected_no_firing_observed=False, foreign_owner_unchanged=True)
        atomic_write(self.root/(peer+"-permit.json"), dict(run_id=self.run, index=index))

    def observe(self):
        row, peer = self.current, self.current["target"]
        require(time.monotonic()-self.case_started < 20., "native authority reload/replication timeout")
        self.select(peer)
        active, tasks = bool(self.ability.get_property("bIsActive")), NativeReload.tasks(self)
        row["authority_active_observed"] |= active
        row["authority_tasks_observed"] = max(row["authority_tasks_observed"], tasks)
        row["authority_montage_playing_observed"] |= bool(self.anim.call_function("Montage_IsPlaying", self.ability.ReloadMontage))
        if active: row["authority_expected_no_firing_observed"] |= NativeReload.no_firing(self) == (row["initial_ammo"][0] == 0)
        if all(row[key] for key in ("authority_active_observed", "authority_montage_playing_observed", "authority_expected_no_firing_observed")) and row["authority_tasks_observed"] == 2:
            if not row.get("held_barrier_published"):
                row["held_barrier_published"] = True
                atomic_write(self.root/(peer+"-"+str(row["index"])+"-held.json"), dict(run_id=self.run, index=row["index"]))
        for foreign, owner in self.owners.items():
            if foreign != peer:
                old_pawn = self.pawn; self.pawn = owner["pawn"]
                row["foreign_owner_unchanged"] &= capture(owner["controller"]) == self.original_models[foreign] and not NativeReload.no_firing(self)
                self.pawn = old_pawn
        require(row["foreign_owner_unchanged"], "reload mutated another owner inventory/NoFiring")
        ack = read_json(self.root/(peer+"-"+str(row["index"])+"-ack.json"))
        if ack is None: return
        require((ack["run_id"], ack["peer"], ack["index"]) == (self.run, peer, row["index"]), "foreign native reload ack")
        model = capture(self.controller); actual = policy.ammo(self.item)
        row["last_authority_ammo"] = actual
        if active or tasks != 0 or NativeReload.no_firing(self) or actual != tuple(ack["row"]["final_ammo"]) or model != ack["row"]["native_inventory_model"]: return
        stats = policy.snapshot()
        row.update(authority_final_ammo=actual, authority_inventory_model=model, native_ability_inactive=True, authority_tasks_after=tasks,
            authority_no_firing_after_end=False, authority_counters={key: value-self.before[key] for key, value in stats.items()
                if type(value) is int and key != "active_count"}, client=ack)
        NativeReload.set_ammo(self, self.originals[peer])
        row["authority_original_restored"] = capture(self.controller) == self.original_models[peer] and policy.ammo(self.item) == self.originals[peer]
        require(row["authority_original_restored"], "native authority original reload ammo/equipment restore failed")
        self.report["cases"].append(copy.deepcopy(row))
        atomic_write(self.root/("authority-"+str(self.position)+".json"), dict(run_id=self.run, row=row))
        atomic_write(self.root/(peer+"-restored.json"), dict(run_id=self.run, index=row["index"]))
        ue.log("UEP_RELOAD_MAGAZINE_NETWORK_CASE_OBSERVED "+peer+"/"+str(row["index"]))
        self.current = None; self.position += 1

    def restore(self):
        for peer in self.owners:
            self.select(peer)
            if self.ability.get_property("bIsActive"): self.ability.call_function("K2_EndAbility")
            NativeReload.set_ammo(self, self.originals[peer])
        self.report["original_player_states_restored"] = all(capture(owner["controller"]) == self.original_models[peer]
            for peer, owner in self.owners.items())
        if self.weapon_fixtures:
            self.report["equipped_fixture_states_restored"] = self.report["original_player_states_restored"]
            for peer, state in self.weapon_fixtures.items(): weapons.restore(self.weapon_controllers[peer], state)
            self.report["temporary_weapons_removed"] = all(weapons.restored(self.weapon_controllers[peer], state) for peer, state in self.weapon_fixtures.items())
            self.report["original_player_states_restored"] = self.report["temporary_weapons_removed"]

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 600., "native reload authority timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.weapon_prepared: self.prepare_weapons()
            elif not self.owners: self.setup()
            elif not self.prepared: self.prepare()
            else:
                isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
                if self.position == len(PEERS)*len(PLAN)*2:
                    complete = [read_json(self.root/(peer+"-complete.json")) for peer in PEERS]
                    if all(value is not None and value["run_id"] == self.run for value in complete):
                        if not self.released:
                            self.restore(); atomic_write(self.root/"release.json", dict(run_id=self.run)); self.released = True
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
        if error:
            self.report["failed_authority_observation"] = copy.deepcopy(self.current)
            if self.prepared and not self.released:
                try: self.restore()
                except Exception: error += traceback.format_exc()
            elif self.weapon_fixtures:
                for peer, state in self.weapon_fixtures.items():
                    try: weapons.restore(self.weapon_controllers[peer], state)
                    except Exception: error += traceback.format_exc()
        if self.equipment_observer is not None: self.report["equipment_integration"] = self.equipment_observer.close()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_RELOAD_MAGAZINE_NETWORK_"+("FAILED "+error if error else "READY")); ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown": self.report["status"] = "passed"
        atomic_write(self.path, self.report)
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_RELOAD_MAGAZINE_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPReloadMagazineNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPReloadMagazineNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
