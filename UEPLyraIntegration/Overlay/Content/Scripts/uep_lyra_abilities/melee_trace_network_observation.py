"""Test-only around-activation reads; production handlers always run once."""
import traceback
import unreal_engine as ue
from . import melee_trace_mixin as policy
from .melee_hit_montage_mixin import CLASS

FLOOR = "/Game/UEPValidation/BP_MeleeNetworkFloor.BP_MeleeNetworkFloor_C"
PROFILES = (("Python", policy.LyraMeleeTracePythonProfile), ("BlueprintFallback", policy.LyraMeleeTraceBlueprintFallbackProfile))


def install(observer):
    cls = ue.load_class(CLASS)
    for name, base in PROFILES:
        def around(handler):
            def activate(instance):
                try: observer.before_activation(instance)
                except Exception: observer.observation_errors.append(traceback.format_exc())
                handler(instance)
                try: observer.after_activation(instance)
                except Exception: observer.observation_errors.append(traceback.format_exc())
            activate.override = "K2_ActivateAbility"
            return activate
        values = {key: base.__dict__[key] for key in ("SelectHitMontage", "NativeEnded", "AuthorityTrace", "__init__", "__uep_mixin_teardown__")}
        values["Activate"] = around(base.__dict__["Activate"])
        ue.register_mixin_profile(cls, name, type("ObservedMeleeTrace"+name, (), values))


def restore():
    cls = ue.load_class(CLASS)
    for name, base in PROFILES: ue.register_mixin_profile(cls, name, base)
    binding, = [value for value in ue.get_registered_mixins() if value["target_class"] == cls]
    return {name: len(value["functions"]) for name, value in binding["profiles"].items()} == dict(Python=4, BlueprintFallback=4)
