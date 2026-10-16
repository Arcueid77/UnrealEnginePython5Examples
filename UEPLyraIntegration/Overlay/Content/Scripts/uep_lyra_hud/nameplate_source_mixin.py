"""Pawn nameplate discovery business; native component lifecycle is retained."""
import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from .weapon_observer import valid
from .nameplate_refs import optional_ref
from . import nameplate_messages as messages

CLASS = "/Game/UI/Indicators/NameplateSource.NameplateSource_C"
RESUME = "UEPResumeNameplateDiscovery"
PROXY = "UEPOriginalNameplateDiscoverProxy"
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "adds": 0, "removes": 0,
          "discoveries": 0, "null_managers": 0, "helpers_rooted": 0, "helpers_unrooted": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_sources=list(_active.values()))


def helper(source):
    if source._uep_np_source_helper is None:
        value = ue.new_object(source.PythonMessageAdapterClass)
        value.add_to_root()
        _stats["helpers_rooted"] += 1
        source._uep_np_source_helper = value
    return source._uep_np_source_helper


def discover(source, value):
    manager = getattr(value, messages.MANAGER)
    if valid(manager):
        manager.call_function("RegisterNameplateSource", messages.owner_pawn(source))
        _stats["discoveries"] += 1
        source._uep_np_discoveries += 1
    else:
        # A null reflected target in the original BP performs no registration.
        _stats["null_managers"] += 1


def listen(source):
    if source._uep_np_source_scope is not None:
        return
    reader, scope = helper(source), SubscriptionScope()
    source._uep_np_source_scope = scope
    _stats["scopes_created"] += 1
    _active[id(source)] = source.get_path_name()
    try:
        scope.listen_gameplay_message(source, messages.PREFIX+"Discover", messages.payload_type(messages.REQUEST),
            lambda proxy: messages.read(reader, proxy, False), lambda channel, value: discover(source, value))
    except Exception:
        close(source)
        raise


def close(source):
    scope, reader = source._uep_np_source_scope, source._uep_np_source_helper
    source._uep_np_source_scope = source._uep_np_source_helper = None
    _active.pop(id(source), None)
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


def close_original(source):
    proxy = optional_ref(source, PROXY)
    # Runtime write: attribute assignment emits Editor PostEditChange and can
    # rerun the owner's construction scripts, destroying a dynamic component.
    source.set_property(PROXY, None)
    if valid(proxy):
        proxy.call_function("Cancel")


class LyraNameplateSourcePythonProfile:
    def __init__(self):
        self._uep_np_source_scope = self._uep_np_source_helper = None
        self._uep_np_source_ended = False
        self._uep_np_discoveries = 0

    def BeginPlay(self):
        self._uep_np_source_ended = False
        reader = helper(self)
        # Preserve the original sequence: announce Add BEFORE discovery listen.
        messages.broadcast(self, reader, "Add", messages.owner_pawn(self))
        _stats["adds"] += 1
        listen(self)

    BeginPlay.override = "ReceiveBeginPlay"

    def EndPlay(self, EndPlayReason):
        if self._uep_np_source_ended:
            return
        self._uep_np_source_ended = True
        reader = helper(self)
        try:
            messages.broadcast(self, reader, "Remove", messages.owner_pawn(self))
            _stats["removes"] += 1
        finally:
            close(self)

    EndPlay.override = "ReceiveEndPlay"

    def ResumeDiscovery(self):
        if not self._uep_np_source_ended:
            listen(self)  # Listener only: no fabricated BeginPlay/Add.

    ResumeDiscovery.override = RESUME

    def __uep_mixin_teardown__(self):
        close(self)  # A Profile switch is not an EndPlay/Remove announcement.


class LyraNameplateSourceBlueprintFallbackProfile:
    def __init__(self):
        pass

    def BeginPlay(self):
        close_original(self)
        self.call_mixin_original("ReceiveBeginPlay")

    BeginPlay.override = "ReceiveBeginPlay"

    def EndPlay(self, EndPlayReason):
        try:
            self.call_mixin_original("ReceiveEndPlay", EndPlayReason)
        finally:
            close_original(self)

    EndPlay.override = "ReceiveEndPlay"

    def ResumeDiscovery(self):
        close_original(self)
        self.call_mixin_original(RESUME)

    ResumeDiscovery.override = RESUME

    def __uep_mixin_teardown__(self):
        close_original(self)
