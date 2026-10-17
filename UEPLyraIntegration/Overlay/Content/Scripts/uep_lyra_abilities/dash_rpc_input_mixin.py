"""Only the two stores after native SendInfo ingress; RPC/GAS/tasks stay native."""
from .dash_selector_mixin import LyraDashSelectorPythonProfile, LyraDashSelectorBlueprintFallbackProfile

GATE = "UEPDashStoreRemoteInput"


def vector(value): return [float(value.x), float(value.y), float(value.z)]
def path(value): return value.get_path_name() if value is not None else None


def evidence(ability):
    value = getattr(ability, "_uep_dash_rpc_input", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, last=None)
        ability._uep_dash_rpc_input = value
    return value


def received(ability, direction, montage, python):
    value = evidence(ability); value["python_calls" if python else "fallback_calls"] += 1
    value["last"] = dict(direction=vector(direction), montage=path(montage),
        ability_authority=bool(ability.call_function("K2_HasAuthority")))
    if python:
        ability.set_property("Direction", direction)
        ability.set_property("Montage", montage)
    # False skips ONLY the two original stores, then rejoins native Commit.
    return not python


class LyraDashRPCInputPythonProfile:
    SelectDirectionalMontage = LyraDashSelectorPythonProfile.__dict__["SelectDirectionalMontage"]
    def StoreRemoteInput(self, Vector, Montage): return received(self, Vector, Montage, True)
    StoreRemoteInput.override = GATE


class LyraDashRPCInputBlueprintFallbackProfile:
    SelectDirectionalMontage = LyraDashSelectorBlueprintFallbackProfile.__dict__["SelectDirectionalMontage"]
    def StoreRemoteInput(self, Vector, Montage): return received(self, Vector, Montage, False)
    StoreRemoteInput.override = GATE
