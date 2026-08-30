"""Plain profile classes used by the asset-authored Interface/MixinSet probe."""


PROBE_CLASS_PATH = (
    "/Game/UEPTests/BP_MixinInterfaceProbe."
    "BP_MixinInterfaceProbe_C"
)
PROBE_CHILD_CLASS_PATH = (
    "/Game/UEPTests/BP_MixinInterfaceProbeChild."
    "BP_MixinInterfaceProbeChild_C"
)
PROBE_MIXIN_SET_PATH = (
    "/Game/UEPTests/DA_MixinInterfaceProbe."
    "DA_MixinInterfaceProbe"
)

ARRAY_ROUTE_PROFILE = "ArrayRoute"
BLUEPRINT_FALLBACK_PROFILE = "BlueprintFallback"


def _initialize(instance, profile):
    instance.InterfaceProbeProfile = profile
    instance.InterfaceProbeInitializations = (
        getattr(instance, "InterfaceProbeInitializations", 0) + 1
    )
    instance.InterfaceProbeTeardowns = getattr(
        instance,
        "InterfaceProbeTeardowns",
        0,
    )
    instance.InterfaceProbePythonCalls = getattr(
        instance,
        "InterfaceProbePythonCalls",
        0,
    )


def _teardown(instance):
    instance.InterfaceProbeTeardowns += 1


def _snapshot(instance):
    return {
        "profile": instance.InterfaceProbeProfile,
        "initializations": instance.InterfaceProbeInitializations,
        "teardowns": instance.InterfaceProbeTeardowns,
        "python_calls": instance.InterfaceProbePythonCalls,
    }


class ArrayRouteProfile:
    """Provides the routed function so it belongs to the class-level union."""

    def __init__(self):
        _initialize(self, ARRAY_ROUTE_PROFILE)

    def __uep_mixin_teardown__(self):
        _teardown(self)

    def AddInstances(
        self,
        instance_transforms,
        should_return_indices,
        world_space=False,
        update_navigation=True,
    ):
        self.InterfaceProbePythonCalls += 1
        return [777] if should_return_indices else []

    def BatchUpdateInstancesTransforms(
        self,
        start_instance_index,
        new_instance_transforms,
        world_space=False,
        mark_render_state_dirty=False,
        teleport=False,
    ):
        self.InterfaceProbePythonCalls += 1
        return True

    def interface_probe_snapshot(self):
        return _snapshot(self)


class BlueprintFallbackProfile:
    """Omits AddInstances so its return + const-array call stays fully native."""

    def __init__(self):
        _initialize(self, BLUEPRINT_FALLBACK_PROFILE)

    def __uep_mixin_teardown__(self):
        _teardown(self)

    def SetCullDistances(self, start_cull_distance, end_cull_distance):
        self.InterfaceProbePythonCalls += 1
        self.call_mixin_original(
            "SetCullDistances",
            start_cull_distance,
            end_cull_distance,
        )

    def interface_probe_snapshot(self):
        return _snapshot(self)
