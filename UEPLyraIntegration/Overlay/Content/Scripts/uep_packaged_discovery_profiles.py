"""Profiles for an explicitly requested fresh-package discovery fixture."""


class PythonProfile:
    def RunCommand(self):
        self.set_property('PythonCalls', self.get_property('PythonCalls')+1)


class BlueprintFallbackProfile:
    def RunCommand(self):
        self.call_mixin_original('RunCommand')
