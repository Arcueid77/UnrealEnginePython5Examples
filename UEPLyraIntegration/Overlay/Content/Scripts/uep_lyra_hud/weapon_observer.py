"""One read-only sampler, change notifications for all weapon presenters.

Lyra's inventory StatTags FastArray has no public change delegate. Do not claim
this is a replication callback: we sample once per engine frame, cache each
controller/item read within that frame, and notify only changed subscribers.
No inventory, equipment or GAS writes belong here. Destruct/router teardown
must remove subscriptions; the final removal also releases the native ticker.
"""

import copy
import traceback

import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope


# A controlled reload must first tear down the routers. Also cancel any old
# observer handle here so an accidental module reload cannot duplicate tickers.
if "close" in globals():
    close()

_subscriptions = {}
_controllers = {}
_ticker = None
_serial = 0
_stats = {"subscribed": 0, "unsubscribed": 0, "samples": 0,
          "notifications": 0, "item_reads": 0, "native_signals": 0,
          "scope_created": 0, "scope_closed": 0, "events": [], "errors": []}
TAGS = ("Lyra.ShooterGame.Weapon.MagazineAmmo", "Lyra.ShooterGame.Weapon.SpareAmmo",
        "Lyra.ShooterGame.Weapon.MagazineSize")


def valid(obj):
    try:
        return obj is not None and obj.is_valid()
    except Exception:
        return False


def path(obj):
    return obj.get_path_name() if valid(obj) else None


def subscribe(widget, kind, renderer=None):
    global _ticker, _serial
    old = getattr(widget, "_uep_weapon_subscription", None)
    if old in _subscriptions and _subscriptions[old]["widget"] == widget:
        return old
    _serial += 1
    token = _serial
    widget._uep_weapon_subscription = token
    _subscriptions[token] = {"widget": widget, "kind": kind, "renderer": renderer, "last": None, "controller": None}
    _stats["subscribed"] += 1
    if _ticker is None:
        _ticker = ue.add_ticker(_tick)
    return token


def unsubscribe(widget):
    token = getattr(widget, "_uep_weapon_subscription", None)
    widget._uep_weapon_subscription = None
    _remove(token)


def _remove(token):
    global _ticker
    removed = _subscriptions.pop(token, None)
    if removed is not None:
        _stats["unsubscribed"] += 1
        _release_controller(removed["controller"])
    if not _subscriptions and _ticker is not None:
        handle, _ticker = _ticker, None
        ue.remove_ticker(handle)


def close():
    for token in list(_subscriptions):
        _remove(token)


def _native_signal(*args):
    # Messages are GameInstance-wide; always re-read each subscriber through
    # its own controller. Never apply another player's untyped payload.
    _stats["native_signals"] += 1
    refresh()


def _release_controller(key):
    if key not in _controllers:
        return
    record = _controllers[key]
    record["references"] -= 1
    if record["references"] == 0:
        del _controllers[key]
        record["scope"].close()
        _stats["scope_closed"] += 1


def _observe_controller(subscription, controller, key):
    if key == subscription["controller"]:
        return
    _release_controller(subscription["controller"])
    subscription["controller"] = None
    if key is None:
        return
    if key not in _controllers:
        scope = SubscriptionScope()
        try:
            scope.bind_event(controller, "OnPossessedPawnChanged", _native_signal)
            for channel in ("Lyra.QuickBar.Message.ActiveIndexChanged", "Lyra.QuickBar.Message.SlotsChanged"):
                scope.listen_gameplay_signal(controller, channel, _native_signal)
        except Exception:
            scope.close()
            raise
        _controllers[key] = {"scope": scope, "references": 0}
        _stats["scope_created"] += 1
    _controllers[key]["references"] += 1
    subscription["controller"] = key


def _read(subscription, controllers, items):
    widget = subscription["widget"]
    controller = widget.call_function("GetOwningPlayer")
    controller_path = path(controller)
    # Paths can be reused by a later World. The scope retains the wrapper, so
    # its Python identity cannot be recycled while this record is alive.
    controller_key = (controller_path, id(controller)) if controller_path is not None else None
    _observe_controller(subscription, controller, controller_key)
    if controller_key not in controllers:
        quickbar = (controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
                    if valid(controller) else None)
        pawn = controller.get_controlled_pawn() if valid(controller) else None
        active = quickbar.call_function("GetActiveSlotItem") if valid(quickbar) else None
        controllers[controller_key] = (quickbar, active, path(pawn))
    quickbar, active, pawn_key = controllers[controller_key]
    item = active if subscription["kind"] == "panel" else widget.InventoryInstance
    item_key = path(item)
    if item_key not in items:
        items[item_key] = tuple(int(item.call_function("GetStatTagStackCount", GameplayTag(TagName=tag)))
                               for tag in TAGS) if valid(item) else (0, 0, 0)
        _stats["item_reads"] += int(item_key is not None)
    values = items[item_key]
    signature = (controller_key, pawn_key, item_key) + values
    return {"controller": controller_path, "pawn": pawn_key, "item_path": item_key,
            "item": item, "quickbar": quickbar, "magazine": values[0],
            "spare": values[1], "maximum": values[2]}, signature


def refresh(widget=None):
    """Production sampler; optional one-widget refresh for initialization."""
    from .ammo_mixin import render_counter, render_panel
    controllers, items = {}, {}
    for token, subscription in list(_subscriptions.items()):
        target = subscription["widget"]
        if widget is not None and widget != target:
            continue
        if _subscriptions.get(token) is not subscription:
            continue
        if not valid(target):
            _remove(token)
            continue
        try:
            value, signature = _read(subscription, controllers, items)
            _stats["samples"] += 1
            if signature == subscription["last"]:
                continue
            renderer = subscription["renderer"] or (render_panel if subscription["kind"] == "panel" else render_counter)
            renderer(target, value)
            subscription["last"] = signature
            _stats["notifications"] += 1
            _stats["events"].append({"sequence": _stats["notifications"], "widget": path(target),
                                     "kind": subscription["kind"], **{key: value[key] for key in
                                     ("controller", "pawn", "item_path", "magazine", "spare", "maximum")}})
            del _stats["events"][:-64]
        except Exception:
            detail = traceback.format_exc()
            _stats["errors"].append(detail)
            del _stats["errors"][:-16]
            _remove(token)
            ue.log_error(detail)


def _tick(delta):
    refresh()
    return bool(_subscriptions)


def snapshot():
    return {**copy.deepcopy(_stats), "source": "read-only-frame-sampler",
            "active_count": len(_subscriptions), "ticker_active": _ticker is not None,
            "active_scopes": len(_controllers),
            "message_source": "native-QuickBar-and-possession-signals",
            "active_widgets": [path(entry["widget"]) for entry in _subscriptions.values()]}
