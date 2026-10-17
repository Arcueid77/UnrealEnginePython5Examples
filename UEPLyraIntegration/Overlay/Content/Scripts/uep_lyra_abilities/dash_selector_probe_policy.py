"""Private literal-only native inheritance controls; never game abilities."""
import unreal_engine as ue


class AncestorPython:
    def __init__(self): self._uep_probe_parent_init = self.call_mixin_original("SharedValue")
    def AncestorValue(self): return self.call_mixin_original("AncestorValue")+100
    def SharedValue(self): return self.call_mixin_original("SharedValue")+1000
    def __uep_mixin_teardown__(self): self._uep_probe_parent_teardown = self.call_mixin_original("SharedValue")


class AncestorBlueprintFallback:
    def AncestorValue(self): return self.call_mixin_original("AncestorValue")
    def SharedValue(self): return self.call_mixin_original("SharedValue")


class ChildPython:
    def __init__(self): self._uep_probe_child_init = self.call_mixin_original("SharedValue")
    def ChildValue(self): return self.call_mixin_original("ChildValue")+200
    def SharedValue(self):
        before = self.call_mixin_original("SharedValue")
        parent = ue.call_function_by_class(self, self.get_class().get_super_class(), "SharedValue", {})["ReturnValue"]
        after = self.call_mixin_original("SharedValue")
        return before+parent+after+2000
    def __uep_mixin_teardown__(self): self._uep_probe_child_teardown = self.call_mixin_original("SharedValue")


class ChildBlueprintFallback:
    def ChildValue(self): return self.call_mixin_original("ChildValue")
    def SharedValue(self): return self.call_mixin_original("SharedValue")
