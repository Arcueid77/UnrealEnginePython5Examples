"""Nameplate discovery/descriptor orchestration; projection stays in Lyra C++."""
import copy
import unreal_engine as ue
from unreal_engine import FVector
from unreal_engine.structs import LinearColor
from uep_runtime import SubscriptionScope
from .weapon_observer import valid
from .nameplate_refs import optional_ref
from . import nameplate_messages as messages

CLASS = "/Game/UI/Indicators/NameplateManagerComponent.NameplateManagerComponent_C"
WIDGET = "/Game/UI/Indicators/W_Nameplate.W_Nameplate_C"
RESUME = "UEPResumeNameplateManagerObservation"
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "registrations": 0,
          "unregistrations": 0, "discover_broadcasts": 0, "destroy_nonlocal": 0,
          "duplicate_keys": 0, "endplays": 0, "helpers_rooted": 0, "helpers_unrooted": 0, "errors": []}
_stats["remove_traces"] = []  # Bounded metadata only, never UObject owners.


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_managers=list(_active.values()))


def trace_path(value):
    try:
        return value.get_path_name() if valid(value) else None
    except Exception:
        return None


def print_native(context, value):
    ue.find_class("KismetSystemLibrary").get_cdo().call_function("PrintString", context, value,
        True, True, LinearColor(R=0.0, G=.66, B=1.0, A=1.0), 2.0, "None")


def close(manager):
    scope, reader = manager._uep_np_manager_scope, manager._uep_np_manager_helper
    manager._uep_np_manager_scope = manager._uep_np_manager_helper = None
    _active.pop(id(manager), None)
    try:
        if scope is not None:
            scope.close()
            _stats["scopes_closed"] += 1
    except Exception as error:
        _stats["errors"].append(str(error))
        raise
    finally:
        if valid(reader):
            reader.remove_from_root()
            _stats["helpers_unrooted"] += 1


def close_original(manager):
    errors = []
    for field in ("AsyncListForAdd", "AsyncListenForRemove"):
        try:
            proxy = optional_ref(manager, field)
            # Runtime writes must not emit Editor property-change events;
            # those can reconstruct the owner and invalidate this component.
            manager.set_property(field, None)
            if valid(proxy):
                proxy.call_function("Cancel")
        except Exception as error:
            errors.append(error)
    if errors:
        _stats["errors"].extend(str(error) for error in errors)
        raise RuntimeError("original nameplate manager cancellation failed") from errors[0]


def listen(manager):
    if manager._uep_np_manager_scope is not None:
        return
    reader = ue.new_object(manager.PythonMessageAdapterClass)
    reader.add_to_root()
    _stats["helpers_rooted"] += 1
    scope = SubscriptionScope()
    manager._uep_np_manager_scope, manager._uep_np_manager_helper = scope, reader
    _stats["scopes_created"] += 1
    _active[id(manager)] = manager.get_path_name()
    try:
        for action, function in (("Add", "RegisterNameplateSource"), ("Remove", "UnregisterNameplateSource")):
            scope.listen_gameplay_message(manager, messages.PREFIX+action, messages.payload_type(messages.INFO),
                lambda proxy: messages.read(reader, proxy, True),
                lambda channel, value, function=function: manager.call_function(function, getattr(value, messages.PAWN)))
    except Exception:
        close(manager)
        raise


def clear_descriptors(manager):
    # Do not query a Blueprint function-local `Indicator` as an object property.
    entries = dict(manager.IndicatorMap)
    errors = []
    try:
        for descriptor in entries.values():
            try:
                if valid(descriptor):
                    descriptor.call_function("UnregisterIndicator")
                    _stats["unregistrations"] += 1
            except Exception as error:
                errors.append(error)
    finally:
        manager.set_property("IndicatorMap", {})
    if errors:
        _stats["errors"].extend(str(error) for error in errors)
        raise RuntimeError("nameplate descriptor cleanup failed") from errors[0]


class LyraNameplateManagerPythonProfile:
    def __init__(self):
        self._uep_np_manager_scope = self._uep_np_manager_helper = None
        self._uep_np_manager_ended = False
        self._uep_np_registrations = self._uep_np_unregistrations = 0

    def BeginPlay(self):
        self._uep_np_manager_ended = False
        owner = self.call_function("GetOwner")
        if (valid(owner) and owner.is_a(ue.find_class("LyraPlayerController")) and
                owner.call_function("IsLocalPlayerController")):
            self.call_function("Ready")
        else:
            _stats["destroy_nonlocal"] += 1
            # DefaultToSelf is a Blueprint pin default, not ProcessEvent's
            # argument default. Pass the caller explicitly in the script API.
            self.call_function("K2_DestroyComponent", self)

    BeginPlay.override = "ReceiveBeginPlay"

    def Ready(self):
        close(self)
        listen(self)
        # BOTH Add/Remove subscriptions exist before synchronous discovery.
        messages.broadcast(self, self._uep_np_manager_helper, "Discover", self)
        _stats["discover_broadcasts"] += 1

    def RegisterNameplateSource(self, IndicatedPawn):
        descriptor = ue.new_object(ue.find_class("IndicatorDescriptor"))
        descriptor.call_function("SetIndicatorClass", WIDGET)
        character = valid(IndicatedPawn) and IndicatedPawn.is_a(ue.find_class("Character"))
        if character:
            descriptor.call_function("SetSceneComponent", IndicatedPawn.CapsuleComponent)
            descriptor.call_function("SetProjectionMode", 1)
            descriptor.call_function("SetBoundingBoxAnchor", FVector(.5, .5, 1.0))
        else:
            descriptor.call_function("SetSceneComponent", IndicatedPawn.RootComponent if valid(IndicatedPawn) else None)
            descriptor.call_function("SetWorldPositionOffset", FVector(0.0, 0.0, 100.0))
            descriptor.call_function("SetProjectionMode", 0)
        descriptor.call_function("SetDataObject", IndicatedPawn)
        descriptor.call_function("SetVAlign", 3)
        descriptor.call_function("SetAutoRemoveWhenIndicatorComponentIsNull", True)
        descriptor.call_function("SetClampToScreen", True)
        entries = dict(self.IndicatorMap)
        if IndicatedPawn in entries:
            # Original Map_Add replaces its key but does not unregister the
            # former descriptor. Track the case; do not silently deduplicate
            # gameplay or pretend the old BP already did so.
            _stats["duplicate_keys"] += 1
        entries[IndicatedPawn] = descriptor
        self.set_property("IndicatorMap", entries)
        owner = self.call_function("GetOwner")
        controller = owner if valid(owner) and owner.is_a(ue.find_class("Controller")) else None
        native = ue.find_class("IndicatorLibrary").get_cdo().call_function("GetIndicatorManagerComponent", controller)
        if valid(native):
            native.call_function("AddIndicator", descriptor)
        else:
            local = bool(controller.call_function("IsLocalPlayerController")) if valid(controller) else False
            value = ue.find_class("KismetStringLibrary").get_cdo().call_function("Conv_BoolToString", local)
            print_native(self, value)
        _stats["registrations"] += 1
        self._uep_np_registrations += 1

    def UnregisterNameplateSource(self, IndicatedPawn):
        entries = dict(self.IndicatorMap)
        before = [trace_path(key) for key in entries]
        descriptor = entries.get(IndicatedPawn)
        if valid(descriptor):
            descriptor.call_function("UnregisterIndicator")
            _stats["unregistrations"] += 1
            self._uep_np_unregistrations += 1
        # Native unregister can synchronously release UMG/indicators and
        # reenter this manager for another Pawn. BP's Sequence then removes
        # from the LIVE Map, not the snapshot used by the earlier Map_Find.
        entries = dict(self.IndicatorMap)
        after_native = [trace_path(key) for key in entries]
        entries.pop(IndicatedPawn, None)
        self.set_property("IndicatorMap", entries)
        _stats["remove_traces"].append(dict(manager=trace_path(self), pawn=trace_path(IndicatedPawn),
            before=before, after_native=after_native, after=[trace_path(key) for key in entries]))
        del _stats["remove_traces"][:-24]

    def EndPlay(self, EndPlayReason):
        if self._uep_np_manager_ended:
            return
        self._uep_np_manager_ended = True
        print_native(self, "NameplateManager Shutdown")
        try:
            close(self)
        finally:
            clear_descriptors(self)
        _stats["endplays"] += 1

    EndPlay.override = "ReceiveEndPlay"

    def ResumeObservation(self):
        if not self._uep_np_manager_ended:
            listen(self)  # No discovery/model replay on a hidden Profile resume.

    ResumeObservation.override = RESUME

    def __uep_mixin_teardown__(self):
        close(self)  # Profile switching retains the native descriptor map.


class LyraNameplateManagerBlueprintFallbackProfile:
    def __init__(self):
        pass

    def Ready(self):
        close_original(self)
        self.call_mixin_original("Ready")

    def EndPlay(self, EndPlayReason):
        try:
            self.call_mixin_original("ReceiveEndPlay", EndPlayReason)
        finally:
            close_original(self)

    EndPlay.override = "ReceiveEndPlay"

    def ResumeObservation(self):
        close_original(self)
        self.call_mixin_original(RESUME)

    ResumeObservation.override = RESUME

    def __uep_mixin_teardown__(self):
        close_original(self)
