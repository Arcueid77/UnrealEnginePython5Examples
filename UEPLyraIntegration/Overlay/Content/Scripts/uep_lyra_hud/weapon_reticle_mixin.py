"""Production reticle BP business; native spread/projection/UMG stay native.

The original ADS custom-event execution pin and its animation chain are
disconnected. Preserve that no-op animation behavior; do not "repair" template
business during migration. Elimination animation is an active runtime path.
"""

import copy
import unreal_engine as ue

from uep_runtime import SubscriptionScope
from .weapon_observer import valid


ON = "ON_1_5C60262A40576A9B456771A11BE74887"
CONTROLLER = "Controller_6_18E0704C47A404BDF6B92284D521D293"
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "ads_messages": 0,
          "elimination_messages": 0, "foreign_messages": 0, "ticks": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()))


def bounds(value, minimum, maximum):
    # Match the BP's nested Greater/Select nodes, including boundary equality.
    return (maximum if value > maximum else value) if value > minimum else minimum


def geometry(kind, radius):
    if kind == "Pistol":
        return radius, bounds(radius * 2, 40, 80), bounds(radius * 2, 40, 80)
    if kind == "Rifle":
        return radius, bounds(radius * 2, 48, 96), bounds(radius * 2, 48, 96)
    if kind == "Shotgun":
        # Only CrossHairs radius is capped; width/height use the native radius.
        return (96 if radius > 96 else radius), bounds(radius * 1.25, 32, 64), bounds(radius * 2, 56, 160)
    raise RuntimeError("unknown authored reticle kind: " + kind)


def close(widget):
    scope, helper = widget._uep_reticle_scope, widget._uep_reticle_reader
    widget._uep_reticle_scope = widget._uep_reticle_reader = None
    _active.pop(id(widget), None)
    try:
        if scope is not None:
            scope.close()
            _stats["scopes_closed"] += 1
    finally:
        if valid(helper):
            helper.remove_from_root()


def read_payload(widget, name, proxy):
    payload, success = widget._uep_reticle_reader.call_function(name, proxy)
    if success is not True:
        raise RuntimeError("typed reticle message extraction failed: " + name)
    return payload


def on_ads(widget, payload):
    if getattr(payload, CONTROLLER) != widget.call_function("GetOwningPlayer"):
        _stats["foreign_messages"] += 1
        return
    widget.call_function("ADS", bool(getattr(payload, ON)))
    _stats["ads_messages"] += 1


def on_elimination(widget, payload):
    actor = payload.Instigator
    # Preserve the original cast, owning-controller match and suicide filter.
    if (not valid(actor) or not actor.is_a(ue.find_class("LyraPlayerState")) or actor == payload.Target
            or actor.call_function("GetLyraPlayerController") != widget.call_function("GetOwningPlayer")):
        _stats["foreign_messages"] += 1
        return
    widget.call_function("Eliminate")
    _stats["elimination_messages"] += 1


def start(widget):
    if widget._uep_reticle_scope is not None and not widget._uep_reticle_scope.closed:
        return
    helper = ue.new_object(widget.PythonMessageAdapterClass)
    helper.add_to_root()
    widget._uep_reticle_reader = helper
    scope = SubscriptionScope()
    widget._uep_reticle_scope = scope
    try:
        ui = ue.load_object(ue.find_class("UserDefinedStruct"), "/ShooterCore/Input/Abilities/Struct_UIMessaging.Struct_UIMessaging")
        scope.listen_gameplay_message(widget, "Gameplay.Message.ADS", ui,
                                      lambda proxy: read_payload(widget, "ReadUI", proxy),
                                      lambda channel, payload: on_ads(widget, payload))
        scope.listen_gameplay_message(widget, "Lyra.Elimination.Message", ue.find_struct("LyraVerbMessage"),
                                      lambda proxy: read_payload(widget, "ReadVerb", proxy),
                                      lambda channel, payload: on_elimination(widget, payload))
    except Exception:
        scope.close()
        helper.remove_from_root()
        widget._uep_reticle_scope = widget._uep_reticle_reader = None
        raise
    _stats["scopes_created"] += 1
    _active[id(widget)] = widget.get_path_name()


class LyraWeaponReticlePythonProfile:
    def __init__(self):
        self._uep_reticle_scope = self._uep_reticle_reader = None
        self._uep_reticle_ads = False
        self._uep_reticle_eliminations = 0
        self._uep_reticle_ticks = 0

    def Construct(self):
        start(self)

    def Destruct(self):
        close(self)

    def __uep_mixin_teardown__(self):
        close(self)

    def Tick(self, MyGeometry, InDeltaTime):
        start(self)  # Fresh Profile resumes observation without replaying Construct.
        radius = float(self.call_function("ComputeMaxScreenspaceSpreadRadius"))
        radius, width, height = geometry(str(self.UEPReticleKind), radius)
        self.CrossHairs.call_function("SetRadius", radius)
        self.SBOuterReticle.call_function("SetWidthOverride", width)
        self.SBOuterReticle.call_function("SetHeightOverride", height)
        self._uep_reticle_ticks += 1
        _stats["ticks"] += 1

    def ADS(self, ON):
        # The BP event stores its parameter but executes no animation nodes.
        self._uep_reticle_ads = bool(ON)

    def Eliminate(self):
        animation = self.Elimination
        if self.call_function("IsAnimationPlayingForward", animation):
            self.call_function("StopAnimation", animation)
            self.call_function("SetAnimationCurrentTime", animation, 0.0)
        self.call_function("PlayAnimationForward", animation, 1.0, False)
        self._uep_reticle_eliminations += 1


class LyraWeaponReticleBlueprintFallbackProfile:
    def Construct(self):
        self.call_mixin_original("Construct")

    def Destruct(self):
        self.call_mixin_original("Destruct")

    def Tick(self, MyGeometry, InDeltaTime):
        self.call_mixin_original("Tick", MyGeometry, InDeltaTime)

    def ADS(self, ON):
        self.call_mixin_original("ADS", ON)

    def Eliminate(self):
        self.call_mixin_original("Eliminate")
