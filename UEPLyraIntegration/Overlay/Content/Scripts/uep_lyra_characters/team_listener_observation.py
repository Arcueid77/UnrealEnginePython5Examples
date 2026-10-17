"""Reuse native discovery/cancellation/GC; observe factory policy independently."""
import copy
from .team_observer_observation import Context as ObserverContext
from . import team_listener_mixin as policy


class Context(ObserverContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, actor in self.actors.items():
            self.startup[key]["listener_factory_counters"] = copy.deepcopy(policy.evidence(actor))

    def produce(self, key, profile, calls):
        self.listener_before = copy.deepcopy(policy.evidence(self.actors[key]))
        super().produce(key, profile, calls)

    def complete(self):
        row = super().complete()
        row["listener_counters"] = {key: value-self.listener_before[key] for key, value in policy.evidence(self.actors[self.key]).items()}
        return row
