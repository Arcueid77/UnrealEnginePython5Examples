"""Native lethal GAS only; never invoke/replay the Health delegate receiver."""
import copy
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from .health_changed_observation import health_component
from .ragdoll_observation import NaturalHideTrial
from .inventory_wait_transitions import Transition as OwnedTransition
from .outline_validation import path, gc
from .health_changed_observation import health
from .initial_inventory_contract import require
from . import death_started_mixin as policy, ragdoll_mixin as ragdoll, equipment_hide_mixin as hiding
from . import inventory_wait_mixin as wait, initial_inventory_mixin as loadout

SCENARIOS = [(name, profile) for name in ("default", "single-montage", "empty-montages", "destroy-pending", "switch-pending") for profile in ("BlueprintFallback", "Python")]


def delta(value, before):
    return {key: item-before[key] if type(item) is int and key != "uuid" else copy.deepcopy(item[len(before[key]):]) if key == "trace" else copy.deepcopy(item) for key, item in value.items()}


def senses(actor):
    return [path(value) for value in actor.get_property("AIPerceptionStimuliSource").get_property("RegisterAsSourceForSenses")]


def clock(world): return float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", world))
def frame_delta(world): return float(ue.find_class("GameplayStatics").get_cdo().call_function("GetWorldDeltaSeconds", world))


class NaturalTrial(NaturalHideTrial):
    def __init__(self, *args):
        self.max_delta = 0.; super().__init__(*args)
    def start(self):
        self.death_ref = policy.evidence(self.owner.pawn); self.death_before = copy.deepcopy(self.death_ref)
        self.before_senses = senses(self.owner.pawn)
        self.configured_montages = [path(value) for value in self.owner.pawn.get_property("Death Montages")]
        self.max_delta = frame_delta(self.world)
        scope = None; signals, errors = [], []
        if self.scenario[0] == "native-death":
            # Append a read-only observer AFTER the original BP binding. Capture
            # at the true Health delegate boundary, before later damage/hit-react
            # presentation can legitimately replace the currently playing montage.
            scope = SubscriptionScope()
            def observed(owning_actor):
                try:
                    signals.append(dict(native_prefix_sight_sources=senses(self.owner.pawn),
                        native_prefix_current_montage=path(self.owner.pawn.call_function("GetCurrentMontage")),
                        native_prefix_health=health(self.owner.pawn), signal_actual_owning_actor=path(owning_actor)))
                except Exception: errors.append(traceback.format_exc())
            scope.bind_event(health_component(self.owner.pawn), "OnDeathStarted", observed)
        try: super().start()
        finally:
            if scope is not None: scope.close()
        if self.scenario[0] == "native-death":
            require(not errors and len(signals) == 1, "actual native Health death witness missing/repeated/failed: "+str(errors))
            self.row.update(signals[0]); self.row.update(actor_path=path(self.actor),
                native_after_damage_current_montage=path(self.actor.call_function("GetCurrentMontage")),
                death_signal_observer=dict(created=1, closed=int(scope.closed), active=scope.count, callbacks=len(signals), errors=errors))
    def step(self):
        if not self.closed: self.max_delta = max(self.max_delta, frame_delta(self.world))
        return super().step()
    def capture_hide(self):
        super().capture_hide()
        self.row.update(death_started_counters=delta(policy.evidence(self.actor), self.death_before),
            native_sight_sources_before=self.before_senses, configured_death_montages=list(self.configured_montages),
            native_sight_sources_after=senses(self.actor), maximum_observed_world_delta=self.max_delta,
            health_delegate_manually_replayed=False)


class Trial(NaturalTrial):
    def __init__(self, world, scenario):
        self.case, profile = scenario; self.switch_profile = None; self.destroyed_pending = False
        super().__init__(world, None, ("native-death", 0, 1, profile))
    def start(self):
        actor = self.owner.pawn; self.original_montages = list(actor.get_property("Death Montages"))
        if self.case == "single-montage":
            require(self.original_montages, "original native Character has no death montage control")
            actor.set_property("Death Montages", self.original_montages[:1])
        elif self.case == "empty-montages": actor.set_property("Death Montages", [])
        super().start()
        self.row.update(death_case=self.case, entry_profile=self.scenario[3], actor_path=path(self.actor),
            native_current_profile_after_entry=str(ue.get_mixin_profile(self.actor)), native_lethal_gas_death=True,
            native_health_after=health(self.actor), native_sight_sources_before=self.before_senses,
            configured_death_montages=list(self.configured_montages), health_delegate_manually_replayed=False)
        if self.case == "switch-pending":
            self.switch_profile = "Python" if self.scenario[3] == "BlueprintFallback" else "BlueprintFallback"
            ue.set_mixin_profile(self.actor, self.switch_profile)
        self.row["profile_before_resume"] = str(ue.get_mixin_profile(self.actor))
        if self.case == "destroy-pending":
            self.destroyed_pending = True; self.destroyed_game_time = clock(self.world)
            self.death_snapshot = copy.deepcopy(self.death_ref); self.ragdoll_ref = ragdoll.evidence(self.actor); self.ragdoll_snapshot = copy.deepcopy(self.ragdoll_ref)
            self.hide_ref = hiding.evidence(self.actor); self.hide_snapshot = copy.deepcopy(self.hide_ref)
            self.wait_ref, self.loadout_ref = wait.evidence(self.actor), loadout.evidence(self.actor)
            self.quiet_snapshot = (copy.deepcopy(self.wait_ref), copy.deepcopy(self.loadout_ref))
            self.actor.set_property("Death Montages", self.original_montages)
            self.close(); gc(); self.enter("destroy-death-wait")
    def capture_hide(self):
        super().capture_hide()
        self.death_snapshot = copy.deepcopy(self.death_ref)
        self.actor.set_property("Death Montages", self.original_montages)
        self.row["montage_configuration_restored_before_destroy"] = list(self.actor.get_property("Death Montages")) == self.original_montages
    def step(self):
        if self.phase == "destroy-death-wait":
            require(time.monotonic()-self.phase_started < 3., "destroyed native death observation clock stopped")
            if clock(self.world)-self.destroyed_game_time >= .75:
                self.row.update(death_started_counters=delta(self.death_ref, self.death_before), maximum_observed_world_delta=self.max_delta,
                    destroyed_owner_observed_for_game_seconds=clock(self.world)-self.destroyed_game_time,
                    montage_configuration_restored_before_destroy=True, native_sight_sources_after=self.row["native_prefix_sight_sources"],
                    no_ragdoll_after_destroy=self.ragdoll_ref == self.ragdoll_snapshot)
                self.enter("cleanup-gc")
            return False
        if self.destroyed_pending:
            done = OwnedTransition.step(self)
        else: done = super().step()
        if done:
            self.row.update(death_started_quiet_after_destroy=self.death_ref == self.death_snapshot,
                destroyed_pending=self.destroyed_pending, callback_receiver_called_by_fixture=False,
                hide_quiet_after_destroy=self.hide_ref == self.hide_snapshot)
        return done
