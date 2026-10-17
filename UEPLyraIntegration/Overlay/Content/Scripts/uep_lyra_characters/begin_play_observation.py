"""New native Actors only; synchronous fixture default override always restores."""
import copy
from contextlib import contextmanager
import time
import unreal_engine as ue
from .inventory_wait_transitions import Transition as OwnedTransition
from .initial_inventory_contract import require, CLASS
from .initial_inventory_validation import state
from .outline_validation import path, gc
from . import begin_play_mixin as policy, team_listener_mixin as listener, visibility_mixin as visibility
from . import inventory_wait_mixin as wait, initial_inventory_mixin as loadout

SCENARIOS = [(name, 0, 1, profile) for name in ("pending", "ready") for profile in ("BlueprintFallback", "Python")]


@contextmanager
def default_profile(cls, profile):
    # Test-only, game-thread/synchronous window. Never save the CDO or replay
    # BeginPlay. Fresh native objects copy this ordinary FName default.
    cdo = cls.get_cdo(); original = str(cdo.get_property("PythonMixinProfile"))
    try:
        cdo.set_property("PythonMixinProfile", profile); yield
    finally: cdo.set_property("PythonMixinProfile", original)
    require(str(cdo.get_property("PythonMixinProfile")) == original, "fixture CDO Profile did not immediately restore")


class Trial(OwnedTransition):
    def __init__(self, world, scenario):
        self.cls = ue.load_class(CLASS); self.cdo_original = str(self.cls.get_cdo().get_property("PythonMixinProfile"))
        with default_profile(self.cls, scenario[3] if scenario[0] == "ready" else "Python"):
            super().__init__(world, None, scenario)

    def start(self):
        name, _, _, profile = self.scenario
        if name == "ready": self.actor = self.owner.pawn
        else:
            with default_profile(self.cls, profile): self.actor = self.world.actor_spawn(self.cls, ue.FVector(200000., 200000., 2000.))
        require(str(ue.get_mixin_profile(self.actor)) == profile, "new Actor did not copy selected pre-BeginPlay Profile")
        self.row = dict(name=name, profile=profile, native_character_class=path(self.actor.get_class()), native_actor_path=path(self.actor),
            actual_native_new_actor_begin_play=True, begin_play_manually_replayed=False, fixture_cdo_profile_temporarily_overridden_for_spawn=True,
            cdo_profile_restored_immediately=str(self.cls.get_cdo().get_property("PythonMixinProfile")) == self.cdo_original,
            actor_was_not_rooted=not self.actor.is_rooted())
        self.enter("observe-begin")

    def stop(self):
        self.begin_ref = policy.evidence(self.actor); self.begin_snapshot = copy.deepcopy(self.begin_ref)
        self.row.update(begin_play_counters=self.begin_snapshot, listener_counters=copy.deepcopy(listener.evidence(self.actor)),
            visibility_counters=copy.deepcopy(visibility.evidence(self.actor)), native_hidden=bool(self.actor.get_property("bHidden")),
            native_inventory_model=state(self.owner.controller) if self.scenario[0] == "ready" else None,
            cdo_profile_restored_immediately=str(self.cls.get_cdo().get_property("PythonMixinProfile")) == self.cdo_original)
        self.wait_ref, self.loadout_ref = wait.evidence(self.actor), loadout.evidence(self.actor)
        self.quiet_snapshot = (copy.deepcopy(self.wait_ref), copy.deepcopy(self.loadout_ref))
        self.close(); gc(); self.enter("cleanup-gc")

    def step(self):
        if self.phase == "owner-ready":
            require(time.monotonic()-self.started < 20, "native BeginPlay owned bot readiness timeout")
            if self.owner.ready(): self.start()
            return False
        if self.phase == "observe-begin":
            if time.monotonic()-self.phase_started >= .2: self.stop()
            return False
        done = super().step()
        if done: self.row.update(begin_play_quiet_after_destroy=self.begin_ref == self.begin_snapshot,
            cdo_profile_still_restored=str(self.cls.get_cdo().get_property("PythonMixinProfile")) == self.cdo_original)
        return done
