"""Reuse the original level actors and physical two-owner pickup scenarios."""
import copy
import unreal_engine as ue
from uep_lyra_world.spawner_network_validation import SpawnerNetwork as Original
from . import spawner as policy
from .spawner_network_contract import PLAN,validate_cases


class Network(Original):
    plan=PLAN
    case_validator=staticmethod(validate_cases)

    def trigger(self):
        self.cpp_before=copy.deepcopy(policy.metrics(self.pad));super().trigger()

    def collect(self,stage):
        ready=super().collect(stage)
        if ready and stage=='restored':self.current['cpp_policy_delta']={k:v-self.cpp_before[k] for k,v in policy.metrics(self.pad).items()}
        return ready


runtime=Network();ticker=ue.add_ticker(runtime.tick)
