"""Actual native bot creation/Possess; collect only test-owned factory proxies."""
import copy
import unreal_engine as ue
from .inventory_wait_transitions import Transition as WaitTransition
from .initial_inventory_contract import require
from .outline_validation import path
from uep_lyra_world.effect_pad_mixin import valid
from . import possessed_mixin as policy


def live():
    return {path(value): value for value in ue.tobject_iterator(ue.find_class("AsyncAction_ExperienceReady")) if valid(value)}


class Transition(WaitTransition):
    def __init__(self, *args):
        self.possession_proxies = []; self.possession_proxy_paths = []
        self.bootstrap_proxies = []; self.bootstrap_paths = []; before = set(live())
        try:
            super().__init__(*args)
            self.native_controller_path = path(self.owner.controller)
            self.owner_startup = copy.deepcopy(policy.evidence(self.owner.pawn))
            self.capture_factory(before, expected_path=self.owner_startup["last_proxy"], bootstrap=True)
        except Exception:
            if hasattr(self, "closed"): self.close()
            raise

    def capture_factory(self, before, expected_path=None, bootstrap=False):
        added = {name: value for name, value in live().items() if name not in before}
        selected = added if expected_path is None else {name: value for name, value in added.items() if name == expected_path}
        require(len(selected) == 1, "actual native possession factory identity differs: "+str(list(added)))
        extra = {name: value for name, value in added.items() if name not in selected}
        require(bootstrap or not extra, "unidentified native factory during isolated Pawn possession")
        self.possession_proxies.extend(selected.values()); self.possession_proxy_paths.extend(selected)
        # Bot Controller BeginPlay also waits for Experience. Keep those exact
        # newly created task identities separate, and prove their cleanup too.
        self.bootstrap_proxies.extend(extra.values()); self.bootstrap_paths.extend(extra)

    def spawn(self):
        before = set(live()); super().spawn()
        if self.scenario[1] != 0: self.capture_factory(before)

    def step(self):
        before = set(live()) if self.scenario[1] == 0 and self.phase == "waiting" else None
        done = super().step()
        if before is not None and self.phase == "released": self.capture_factory(before)
        if done:
            self.row.update(native_possession_controller=self.native_controller_path, native_possession_counters=self.factory_snapshot,
                old_owned_pawn_natural_python_factory=self.owner_startup,
                native_possession_factory_proxy_paths=list(self.possession_proxy_paths),
                native_possession_factory_proxies_created=len(self.possession_proxies),
                native_possession_factory_proxies_collected=all(not valid(value) for value in self.possession_proxies),
                native_controller_bootstrap_experience_proxy_paths=list(self.bootstrap_paths),
                native_controller_bootstrap_experience_proxies_collected=all(not valid(value) for value in self.bootstrap_proxies),
                possession_event_manually_called_by_fixture=False)
        return done

    def close(self):
        if not self.closed and valid(self.actor):
            self.factory_snapshot = copy.deepcopy(policy.evidence(self.actor))
        return super().close()
