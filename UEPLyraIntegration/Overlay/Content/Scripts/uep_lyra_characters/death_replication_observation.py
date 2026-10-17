"""Read-only real Health signal/body witnesses; no callback or state replay."""
import copy
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from .outline_validation import path
from .health_changed_observation import health_component, health
from .death_started_observation import senses, clock, frame_delta, delta
from .equipment_hide_observation import equipment
from .ragdoll_observation import physical
from . import death_started_mixin as death, ragdoll_mixin as ragdoll, equipment_hide_mixin as hiding


def perception_systems(world):
    # Mirror UAIPerceptionSystem::GetCurrent's actual reflected pointer path.
    # UEP.get_world supports only World/Actor/Component, not AISubsystem.
    ai = world.get_property("AISystem")
    system = ai.get_property("PerceptionSystem") if valid(ai) else None
    return [path(system)] if valid(system) else []


class Witness:
    def __init__(self, actor, profile):
        self.actor, self.world, self.profile = actor, actor.get_world(), profile
        self.original_profile = str(ue.get_mixin_profile(actor)); ue.set_mixin_profile(actor, profile)
        self.refs = [death.evidence(actor), ragdoll.evidence(actor), hiding.evidence(actor)]
        self.before = copy.deepcopy(self.refs); self.signals, self.errors, self.body = [], [], None
        self.maximum_delta = frame_delta(self.world); self.invalid_at = self.quiet_before = None
        self.scope = SubscriptionScope(); self.scope_closed = False
        self.row = dict(actor=path(actor), native_class=path(actor.get_class()), profile=profile,
            player_id=int(actor.get_property("PlayerState").PlayerId), native_role=int(actor.call_function("GetLocalRole")),
            actor_was_not_rooted=not actor.is_rooted(), health_before=health(actor),
            senses_before=senses(actor), configured_montages=[path(value) for value in actor.get_property("Death Montages")],
            perception_systems=perception_systems(self.world),
            fixture_replayed_callback=False, fixture_changed_animation_physics=False)
        self.scope.bind_event(health_component(actor), "OnDeathStarted", self.observed)

    def observed(self, owning_actor):
        try:
            self.signals.append(dict(owning_actor=path(owning_actor), native_health=health(self.actor),
                native_death_state=int(health_component(self.actor).call_function("GetDeathState")),
                montage=path(self.actor.call_function("GetCurrentMontage")), senses=senses(self.actor),
                frame=int(ue.find_class("KismetSystemLibrary").get_cdo().call_function("GetFrameCount")), game_seconds=clock(self.world)))
        except Exception: self.errors.append(traceback.format_exc())

    def close_scope(self):
        if not self.scope_closed: self.scope.close(); self.scope_closed = True

    def sample(self):
        self.maximum_delta = max(self.maximum_delta, frame_delta(self.world))
        if valid(self.actor):
            entered = sum(self.refs[1][key]-self.before[1][key] for key in ("python_calls", "fallback_calls"))
            if self.body is None and entered:
                _, instances, actors = equipment(self.actor)
                self.body = dict(physical=physical(self.actor), equipment_instances=len(instances),
                    weapon_paths=[path(value) for value in actors], weapon_hidden=[bool(value.get_property("bHidden")) for value in actors])
        elif self.invalid_at is None:
            self.invalid_at, self.quiet_before = clock(self.world), copy.deepcopy(self.refs)
            self.close_scope(); self.actor = None

    def close(self):
        self.sample(); self.close_scope()
        restored = not valid(self.actor)
        if valid(self.actor):
            ue.set_mixin_profile(self.actor, self.original_profile)
            restored = str(ue.get_mixin_profile(self.actor)) == self.original_profile
        self.row.update(signals=copy.deepcopy(self.signals), observer_errors=list(self.errors),
            observer=dict(created=1, closed=int(self.scope.closed), active=self.scope.count),
            death=delta(self.refs[0], self.before[0]), ragdoll=delta(self.refs[1], self.before[1]), hide=delta(self.refs[2], self.before[2]),
            body=copy.deepcopy(self.body), maximum_world_delta=self.maximum_delta,
            old_actor_invalid=not valid(self.actor), quiet_after_destroy=self.quiet_before is not None and self.refs == self.quiet_before,
            quiet_game_seconds=0. if self.invalid_at is None else clock(self.world)-self.invalid_at,
            profile_restored_or_actor_destroyed=restored, evidence_after_destroy_is_pod=True)
        self.actor = None
        return copy.deepcopy(self.row)
