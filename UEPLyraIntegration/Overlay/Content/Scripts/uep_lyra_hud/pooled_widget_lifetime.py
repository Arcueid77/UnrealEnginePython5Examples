"""Read-only UIExtension pool membership; native pool release is not Destruct.

One shared sampler queries GetAllEntries, never edits a native pool or replays
widget events. Inactive entries disarm their script subscriptions. A naturally
reinserted widget can resume on its normal Tick/Construct.
"""

import copy
import unreal_engine as ue
from .weapon_observer import valid

_records, _ticker = {}, None
_refreshing = False
_stats = {"registered": 0, "unregistered": 0, "deactivations": 0, "reactivations": 0, "samples": 0, "errors": []}


def extension_points(widget):
    tree = widget.get_outer()
    if not valid(tree) or not tree.is_a(ue.find_class("WidgetTree")):
        return []  # Viewport-owned test widgets are not pooled entries.
    pending, visited, points = [tree.RootWidget], set(), []
    panel, user, extension = (ue.find_class(name) for name in ("PanelWidget", "UserWidget", "UIExtensionPointWidget"))
    while pending:
        child = pending.pop()
        if not valid(child) or id(child) in visited:
            continue
        visited.add(id(child))
        if len(visited) > 2048:
            raise RuntimeError("UI tree traversal exceeded bounded size")
        if child.is_a(extension):
            points.append(child)
        elif child.is_a(panel):
            pending.extend(child.call_function("GetChildAt", index) for index in range(child.call_function("GetChildrenCount")))
        elif child.is_a(user) and valid(child.WidgetTree):
            pending.append(child.WidgetTree.RootWidget)
    return points


def entries(point):
    return list(point.call_function("GetAllEntries")) if valid(point) else []


def may_activate(widget):
    point = getattr(widget, "_uep_pool_owner", None)
    return point is None or (valid(point) and widget in entries(point))


def watch(widget, deactivate, activate=None):
    global _ticker
    if id(widget) in _records:
        return
    points = extension_points(widget)
    if not points:
        return
    _records[id(widget)] = {"widget": widget, "points": points, "deactivate": deactivate,
                            "activate": activate, "inactive": False}
    _stats["registered"] += 1
    if _ticker is None:
        _ticker = ue.add_ticker(_tick)


def unwatch(widget):
    global _ticker
    if _records.pop(id(widget), None) is not None:
        _stats["unregistered"] += 1
    if not _records and _ticker is not None:
        handle, _ticker = _ticker, None
        ue.remove_ticker(handle)


def refresh():
    global _refreshing
    if _refreshing:
        return
    _refreshing = True
    try:
        _refresh()
    finally:
        _refreshing = False


def _refresh():
    cache = {}
    for key, record in list(_records.items()):
        if _records.get(key) is not record:
            continue
        widget = record["widget"]
        if not valid(widget):
            unwatch(widget)
            continue
        try:
            point = getattr(widget, "_uep_pool_owner", None)
            if point is None:
                for candidate in record["points"]:
                    if id(candidate) not in cache:
                        cache[id(candidate)] = entries(candidate)
                    if widget in cache[id(candidate)]:
                        widget._uep_pool_owner = point = candidate
                        break
                if point is None:
                    continue  # Native factory has not appended its entry yet.
            if id(point) not in cache:
                cache[id(point)] = entries(point)
            _stats["samples"] += 1
            mounted = widget in cache[id(point)]
            if not mounted and not record["inactive"]:
                _stats["deactivations"] += 1
                record["inactive"] = True  # Disarm before callback/reentry.
                record["deactivate"](widget)
            if not mounted and (record["activate"] is None or not valid(point)):
                unwatch(widget)
            elif mounted and record["inactive"]:
                record["inactive"] = False
                _stats["reactivations"] += 1
                record["activate"](widget)  # Explicit observation, not Construct.
        except Exception as error:
            _stats["errors"].append(str(error))
            unwatch(widget)
            raise


def _tick(delta):
    refresh()
    return bool(_records)


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_records), ticker_active=_ticker is not None,
                source="read-only-native-UIExtension-active-entry-membership")
