"""Test-owned native bot/controllers/components; never remove a user's component."""
import copy
import time
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid, ability_system
from uep_lyra_abilities.auto_respawn_helpers_validation import instances
from uep_lyra_abilities.auto_respawn_helpers_mixin import CLASS as RESPAWN
from .health_changed_observation import OwnedAI
from .initial_inventory_validation import state
from .initial_inventory_contract import P, require
from .inventory_clear_mixin import CLASS, components
from .team_observer_observation import proxies
from .outline_validation import gc, path
from . import inventory_wait_mixin as policy, inventory_ready_mixin as ready, initial_inventory_mixin as loadout

SCENARIOS = [(name, stage, calls, profile) for name, stage, calls in (
    ("controller", 0, 1), ("controller-repeat", 0, 2), ("inventory", 1, 1),
    ("inventory-repeat", 1, 2), ("quickbar", 2, 1), ("quickbar-repeat", 2, 2)) for profile in ("BlueprintFallback", "Python")]
CUE = "/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C"


def end_owned_respawn(actor):
    asc = ability_system(actor) if valid(actor) else None
    if valid(asc):
        for value in instances(asc, ue.load_class(RESPAWN)):
            if value.get_property("bIsActive"): value.call_function("K2_EndAbility")


def delta(after, before): return {key: after[key]-before[key] for key in after if type(after[key]) is int}


class Transition:
    def __init__(self, world, probe, scenario):
        self.world, self.probe, self.scenario = world, probe, scenario
        self.started = self.phase_started = time.monotonic(); self.phase = "owner-ready"
        self.actor = self.added_component = None; self.closed = False; self.original_proxies = set(proxies())
        self.owner = None
        try:
            self.owner = OwnedAI(world); self.owner.pawn.call_function("SetReplicates", False)
        except Exception:
            self.close(); raise

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()

    def spawn(self):
        _, stage, _, profile = self.scenario
        end_owned_respawn(self.owner.pawn)
        self.owner.pawn.call_function("ClearInventory")
        self.owner.controller.call_function("UnPossess")
        mode = ue.find_class("GameplayStatics").get_cdo().call_function("GetGameMode", self.world)
        self.actor = mode.call_function("SpawnDefaultPawnAtTransform", self.owner.controller, ue.FTransform(ue.FVector(200000., 200000., 2000.)))
        require(valid(self.actor) and self.actor.get_class().get_path_name() == CLASS, "owned late-ready spawn did not preserve native Character/PawnData path")
        self.actor.call_function("SetReplicates", False); ue.set_mixin_profile(self.actor, profile)
        self.row = dict(name=self.scenario[0], stage=stage, calls=self.scenario[2], profile=profile,
            native_character_class=path(self.actor.get_class()), actor_was_not_rooted=not self.actor.is_rooted(),
            components_manipulated_on_test_owned_controller_only=True, private_inventory_properties_written=False)
        if stage == 0: self.start_calls()
        else:
            self.owner.controller.call_function("Possess", self.actor); self.enter("initial-grant")

    def start_calls(self):
        self.before_ready = copy.deepcopy(ready.evidence(self.actor)); self.before_loadout = copy.deepcopy(loadout.evidence(self.actor)); self.before_wait = copy.deepcopy(policy.evidence(self.actor))
        for _ in range(self.scenario[2]): self.probe.call_function("Grant", self.actor)
        self.enter("waiting")

    def helpers(self):
        value = loadout.evidence(self.actor)
        return sum(value[key]-self.before_loadout[key] for key in ("python_calls", "fallback_calls"))

    def step(self):
        require(time.monotonic()-self.started < 25, "owned readiness transition timeout: "+self.phase+"/"+self.scenario[0])
        name, stage, calls, profile = self.scenario
        if self.phase == "owner-ready":
            if self.owner.ready(): self.spawn()
        elif self.phase == "initial-grant":
            if sum(loadout.evidence(self.actor)[key] for key in ("python_calls", "fallback_calls")) != 1: return False
            end_owned_respawn(self.actor); self.actor.call_function("ClearInventory")
            cls = ue.find_class(policy.CLASSES[stage]); component = self.owner.controller.get_component_by_type(cls)
            require(valid(component), "owned missing-component control has no original component")
            self.removed_component_path = path(component); component.destroy_component()
            require(not valid(self.owner.controller.get_component_by_type(cls)), "owned original component was not actually removed")
            self.start_calls()
        elif self.phase == "waiting":
            entries = delta(ready.evidence(self.actor), self.before_ready)
            if entries["python_calls"]+entries["fallback_calls"] != calls or time.monotonic()-self.phase_started < .2: return False
            require(self.helpers() == 0, "owned missing readiness component granted early")
            missing = not valid(self.actor.call_function("GetController")) if stage == 0 else not valid(self.owner.controller.get_component_by_type(ue.find_class(policy.CLASSES[stage])))
            require(missing, "native fixture was not actually missing its checkpoint")
            self.row.update(native_checkpoint_really_missing_before_release=True, no_grant_before_native_readiness=True,
                before_release_ready=entries, before_release_wait=copy.deepcopy(policy.evidence(self.actor)))
            if stage == 0: self.owner.controller.call_function("Possess", self.actor)
            else:
                self.added_component = self.owner.controller.add_actor_component(ue.find_class(policy.CLASSES[stage]), "UEPWaitLate"+str(stage))
                require(valid(self.added_component) and self.added_component.component_is_registered() and
                    self.owner.controller.get_component_by_type(ue.find_class(policy.CLASSES[stage])) == self.added_component,
                    "native late component did not actually register on its owned controller")
            self.row["native_readiness_released"] = True; self.enter("released")
        elif self.phase == "released":
            expected = 2 if stage == 0 else 1
            require(self.helpers() <= expected, "repeated readiness created extra native grants")
            if self.helpers() != expected or time.monotonic()-self.phase_started < .2: return False
            model = state(self.owner.controller); _, inventory = components(self.owner.controller)
            paths = [path(value) for value in inventory.call_function("GetAllItems")]
            self.row.update(native_model=model, native_grants=self.helpers(), native_new_item_paths=paths,
                actual_item_definition=P, after_ready=delta(ready.evidence(self.actor), self.before_ready), after_wait=copy.deepcopy(policy.evidence(self.actor)))
            self.wait_ref, self.loadout_ref = policy.evidence(self.actor), loadout.evidence(self.actor)
            self.quiet_snapshot = (copy.deepcopy(self.wait_ref), copy.deepcopy(self.loadout_ref))
            self.close(); gc(); self.enter("cleanup-gc")
        elif self.phase == "cleanup-gc" and time.monotonic()-self.phase_started >= .2:
            if any(valid(value) for value in self.owned_proxies):
                if time.monotonic()-self.phase_started < 2.:
                    gc(); return False
                self.row["retained_observer_diagnostics"] = [dict(path=path(value), rooted=value.is_rooted(), active=bool(value.call_function("IsActive"))) for value in self.owned_proxies if valid(value)]
                require(False, "owned Character observer still retained after repeated native GC")
            pooled = [dict(cue=cue_path, cue_class=CUE, observed_target_was_test_owned=True,
                observer=observer_path, collected=not valid(value), inactive=not valid(value) or not value.call_function("IsActive"),
                unrooted=not valid(value) or not value.is_rooted(), native_cue_field_never_written=True,
                native_cue_handle_still_matches=not valid(value) or valid(cue) and cue.get_property("TeamColorWatcherHandle") == value,
                native_cue_hidden_owner_cleared=not valid(value) or valid(cue) and bool(cue.get_property("bHidden")) and not valid(cue.call_function("GetOwner")))
                for cue, value, cue_path, observer_path in self.pooled_cues]
            self.row.update(owned_new_pawn_destroyed=not valid(self.actor), cleanup=self.cleanup,
                no_late_script_work_after_owned_destruction=(self.wait_ref, self.loadout_ref) == self.quiet_snapshot,
                owned_team_observers_collected=all(not valid(value) for value in self.owned_proxies),
                native_pooled_cue_observers=pooled, original_active_proxies_preserved=set(proxies()) == self.original_proxies)
            return True
        return False

    def close(self):
        if self.closed: return self.cleanup
        if valid(self.actor): end_owned_respawn(self.actor)
        if self.owner is not None and valid(self.owner.pawn): end_owned_respawn(self.owner.pawn)
        added = {name: value for name, value in proxies().items() if name not in self.original_proxies}
        # GCNL_Spawning is retained native GameplayCue pooling, not a Character
        # wait resource. Identify its exact public BP handle AND owned target;
        # never clear the handle, destroy the shared Cue or cancel its watcher.
        self.pooled_cues = []
        for cue in ue.tobject_iterator(ue.load_class(CUE)):
            if not valid(cue) or cue.get_world() != self.world: continue
            value = cue.get_property("TeamColorWatcherHandle")
            if path(value) in added and cue.get_property("TargetActor") in (self.actor, self.owner.pawn if self.owner is not None else None):
                self.pooled_cues.append((cue, value, path(cue), path(value)))
        pooled_paths = {value[3] for value in self.pooled_cues}
        self.owned_proxies = [value for name, value in added.items() if name not in pooled_paths]
        if valid(self.actor): self.actor.actor_destroy()
        self.cleanup = self.owner.close() if self.owner is not None else {}
        # new_object makes the unregistered test producer Python-owned. Drop
        # that wrapper after native destruction: its retained SpawnedBotList
        # must not keep dead Controller BP frames alive across the GC check.
        if self.owner is not None: self.owner.creator = None
        for value in self.owned_proxies:
            if valid(value): value.call_function("Cancel")
        self.closed = True
        return self.cleanup
