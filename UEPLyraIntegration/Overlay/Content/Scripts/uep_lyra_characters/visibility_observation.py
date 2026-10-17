"""Actual native InitState registration/delivery on disposable native Lyra bots."""
import copy
import time
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from .inventory_wait_transitions import Transition as OwnedTransition, end_owned_respawn
from .possessed_observation import Transition as PossessionTransition
from .initial_inventory_contract import require
from .outline_validation import gc, path
from . import visibility_mixin as policy, inventory_wait_mixin as wait, initial_inventory_mixin as loadout

SCENARIOS = [(name, 0, calls, profile) for name, calls in (("single", 1), ("repeat", 2), ("destroy-pending", 1), ("switch-pending", 1))
    for profile in ("BlueprintFallback", "Python")]


class Transition(PossessionTransition):
    def spawn(self):
        super().spawn()
        self.row.update(visibility_after_spawn=copy.deepcopy(policy.evidence(self.actor)), native_hidden_after_spawn=bool(self.actor.get_property("bHidden")))

    def close(self):
        if not self.closed and self.actor is not None:
            from uep_lyra_world.effect_pad_mixin import valid
            if valid(self.actor) and hasattr(self, "row"):
                self.row.update(visibility_before_destroy=copy.deepcopy(policy.evidence(self.actor)), native_hidden_before_destroy=bool(self.actor.get_property("bHidden")),
                    native_visibility_actor_path=path(self.actor), inventory_latent_uuids=list(wait.evidence(self.actor)["uuids"] or []))
        return super().close()


class Trial(OwnedTransition):
    def __init__(self, world, scenario):
        super().__init__(world, None, scenario)

    def start(self):
        name, _, calls, profile = self.scenario
        self.actor = self.owner.pawn; end_owned_respawn(self.actor)
        ue.set_mixin_profile(self.actor, profile); self.actor.call_function("SetActorHiddenInGame", True)
        self.visibility = policy.evidence(self.actor); self.before = copy.deepcopy(self.visibility)
        component = self.actor.get_component_by_type(ue.find_class("LyraPawnExtensionComponent"))
        for _ in range(calls): self.actor.call_function(policy.REGISTER, component, GameplayTag(TagName="InitState.GameplayReady"), True)
        after = copy.deepcopy(self.visibility)
        require(sum(after[key]-self.before[key] for key in ("python_calls", "fallback_calls")) == calls, "actual native immediate InitState signal count differs")
        self.row = dict(name=name, profile=profile, native_actor_path=path(self.actor), native_character_class=path(self.actor.get_class()),
            native_component_path=path(component), native_registration_calls=calls, callback_manually_replayed=False,
            actual_native_initstate_registration=True, payload=after["last_payload"], hidden_before_resume=bool(self.actor.get_property("bHidden")),
            actor_was_not_rooted=not self.actor.is_rooted(), native_hidden_fields_written_directly=False)
        if name == "switch-pending": ue.set_mixin_profile(self.actor, "Python" if profile == "BlueprintFallback" else "BlueprintFallback")
        self.row["profile_before_resume"] = str(ue.get_mixin_profile(self.actor))
        if name == "destroy-pending": self.stop()
        else: self.enter("observe-visibility")

    def stop(self):
        self.row.update(visibility_delta={key: self.visibility[key]-self.before[key] for key in ("python_calls", "fallback_calls", "delay_requests", "resumes", "show_calls")},
            trace=copy.deepcopy(self.visibility["trace"]), native_hidden_before_destroy=bool(self.actor.get_property("bHidden")))
        self.visibility_snapshot = copy.deepcopy(self.visibility)
        self.wait_ref, self.loadout_ref = wait.evidence(self.actor), loadout.evidence(self.actor)
        self.quiet_snapshot = (copy.deepcopy(self.wait_ref), copy.deepcopy(self.loadout_ref))
        self.close(); gc(); self.enter("cleanup-gc")

    def step(self):
        if self.phase == "owner-ready":
            require(time.monotonic()-self.started < 20, "visibility owned native bot readiness timeout")
            if self.owner.ready(): self.start()
            return False
        if self.phase == "observe-visibility":
            require(time.monotonic()-self.phase_started < 5, "visibility native next-tick continuation timeout")
            if time.monotonic()-self.phase_started >= .2:
                require(not self.actor.get_property("bHidden"), "native InitState/next-tick path did not actually show Actor")
                self.stop()
            return False
        done = super().step()
        if done: self.row["visibility_quiet_after_destroy"] = self.visibility == self.visibility_snapshot
        return done
