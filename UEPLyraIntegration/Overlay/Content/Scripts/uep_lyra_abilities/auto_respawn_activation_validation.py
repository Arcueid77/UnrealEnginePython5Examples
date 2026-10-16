"""Observe real native startup and preserve listener/UI ownership in natural play."""
import atexit
import copy
import sys
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_events_validation import Validation as EventValidation
from . import auto_respawn_activation_mixin as activation
from .auto_respawn_activation_contract import validate


class ActivationEvidence:
    def __init__(self, *args):
        super().__init__(*args)
        self.report.update(activation_reset_ui_removal_business_migrated=True,
            activation_natural_regression_only=True, full_auto_respawn_acceptance=False)

    def attach(self, world, controller):
        attached = super().attach(world, controller)
        if attached and "activation_startup" not in self.report:
            self.report["activation_startup"] = activation.instance_snapshot(self.ability)
            self.report["activation_startup_profile"] = str(ue.get_mixin_profile(self.ability))
        return attached

    def query(self):
        row = super().query()
        proxy = self.ability.get_property(activation.PROXY)
        row["activation_state"] = dict(listening=bool(self.ability.IsListeningForReset),
            proxy_active=valid(proxy) and bool(proxy.call_function("IsActive")),
            ended=bool(self.ability.get_property(activation.ENDED)))
        return row

    def trial_begin_evidence(self):
        super().trial_begin_evidence()
        self.activation_before = activation.instance_snapshot(self.ability)

    def trial_end_evidence(self):
        super().trial_end_evidence()
        after = activation.instance_snapshot(self.ability)
        self.row["activation_counters"] = {key: after.get(key, 0)-self.activation_before.get(key, 0) for key in activation.snapshot()}

    def validate_report(self): return validate(self.report)


class Validation(ActivationEvidence, EventValidation): pass


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoRespawnHelpersResult=")), None)
if result and "-UEPAutoRespawnActivation" in sys.argv:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
