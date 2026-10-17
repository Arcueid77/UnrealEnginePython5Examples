"""Resolve compiler-owned receiver symbols from retained native binding objects."""
import unreal_engine as ue
from .enhanced_input_contract import ACTIONS, CLASS


def function_names(cls=None):
    cls = cls if cls is not None else ue.find_class(CLASS)
    if cls is None: raise RuntimeError("retained Character must be loaded before input profile registration")
    result = {}
    for binding in ue.tobject_iterator(ue.find_class("EnhancedInputActionDelegateBinding")):
        if binding.get_outer() != cls: continue
        for entry in binding.get_property("InputActionDelegateBindings"):
            asset = entry.InputAction.get_path_name()
            for key, value in ACTIONS.items():
                expected = "/ShooterCore/Input/Actions/"+value[0]+"."+value[0]
                if asset == expected:
                    if key in result or int(entry.TriggerEvent) != 1: raise RuntimeError("ambiguous/non-Triggered original input binding: "+key)
                    result[key] = str(entry.FunctionNameToBind)
    if set(result) != set(ACTIONS): raise RuntimeError("original five EnhancedInput action bindings are incomplete")
    return result


class Receiver:
    """Existing UEP accepts callable descriptors and reads .override at each registration."""
    def __init__(self, action, function):
        self.action, self.function, self.__wrapped__ = action, function, function

    @property
    def override(self): return function_names()[self.action]

    def __call__(self, *args, **kwargs): return self.function(*args, **kwargs)

    def __get__(self, instance, owner): return self.function.__get__(instance, owner)


def receiver(action): return lambda function: Receiver(action, function)
