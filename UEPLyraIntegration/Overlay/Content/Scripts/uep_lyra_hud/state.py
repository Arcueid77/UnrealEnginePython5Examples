"""Process-local, JSON-safe evidence for the Lyra healthbar mixin."""

import copy


_live_widgets = {}


_state = {
    "registered": False,
    "registration_count": 0,
    "source_asset_available": False,
    "initialized_widgets": 0,
    "construct_count": 0,
    "destruct_count": 0,
    "teardown_count": 0,
    "controller_bind_count": 0,
    "controller_unbind_count": 0,
    "health_bind_count": 0,
    "health_unbind_count": 0,
    "visual_update_count": 0,
    "active_widgets": [],
    "instances": {},
    "health_events": [],
    "errors": [],
}


def _widget_key(widget):
    try:
        return widget.get_path_name()
    except Exception:
        return str(widget)


def _entry(widget):
    key = _widget_key(widget)
    entry = _state["instances"].setdefault(
        key,
        {
            "constructs": 0,
            "destructs": 0,
            "teardowns": 0,
            "controller_binds": 0,
            "controller_unbinds": 0,
            "health_binds": 0,
            "health_unbinds": 0,
            "visual_updates": 0,
            "last_pawn": None,
            "last_health_component": None,
            "last_health": None,
            "last_max_health": None,
            "last_normalized_health": None,
            "last_event": None,
        },
    )
    return key, entry


def mark_asset_available(available):
    _state["source_asset_available"] = bool(available)


def mark_registered():
    _state["registered"] = True
    _state["registration_count"] += 1


def record_initialized(widget):
    _entry(widget)
    _state["initialized_widgets"] += 1


def record_construct(widget):
    key, entry = _entry(widget)
    _live_widgets[key] = widget
    entry["constructs"] += 1
    _state["construct_count"] += 1
    if key not in _state["active_widgets"]:
        _state["active_widgets"].append(key)


def record_destruct(widget):
    key, entry = _entry(widget)
    _live_widgets.pop(key, None)
    entry["destructs"] += 1
    _state["destruct_count"] += 1
    if key in _state["active_widgets"]:
        _state["active_widgets"].remove(key)


def record_teardown(widget):
    key, entry = _entry(widget)
    _live_widgets.pop(key, None)
    entry["teardowns"] += 1
    _state["teardown_count"] += 1
    if key in _state["active_widgets"]:
        _state["active_widgets"].remove(key)


def record_controller_bind(widget, controller):
    _, entry = _entry(widget)
    entry["controller_binds"] += 1
    _state["controller_bind_count"] += 1


def record_controller_unbind(widget):
    _, entry = _entry(widget)
    entry["controller_unbinds"] += 1
    _state["controller_unbind_count"] += 1


def record_health_bind(widget, pawn, health_component):
    _, entry = _entry(widget)
    entry["health_binds"] += 1
    entry["last_pawn"] = _widget_key(pawn)
    entry["last_health_component"] = _widget_key(health_component)
    _state["health_bind_count"] += 1


def record_health_unbind(widget):
    _, entry = _entry(widget)
    entry["health_unbinds"] += 1
    _state["health_unbind_count"] += 1


def record_visual_update(
    widget,
    event,
    health,
    max_health,
    normalized_health,
    old_value=None,
    new_value=None,
):
    key, entry = _entry(widget)
    entry["visual_updates"] += 1
    entry["last_event"] = event
    entry["last_health"] = health
    entry["last_max_health"] = max_health
    entry["last_normalized_health"] = normalized_health
    _state["visual_update_count"] += 1
    item = {
        "widget": key,
        "event": event,
        "health": health,
        "max_health": max_health,
        "normalized_health": normalized_health,
        "old_value": old_value,
        "new_value": new_value,
    }
    _state["health_events"].append(item)
    if len(_state["health_events"]) > 64:
        del _state["health_events"][:-64]


def record_error(widget, operation, detail):
    _state["errors"].append(
        {
            "widget": _widget_key(widget),
            "operation": operation,
            "detail": str(detail),
        }
    )
    if len(_state["errors"]) > 32:
        del _state["errors"][:-32]


def snapshot():
    result = copy.deepcopy(_state)
    result["active_widget_count"] = len(result["active_widgets"])
    return result


def active_widget_objects():
    stale = []
    result = []
    for key, widget in _live_widgets.items():
        try:
            if widget is not None and widget.is_valid():
                result.append(widget)
            else:
                stale.append(key)
        except Exception:
            stale.append(key)
    for key in stale:
        _live_widgets.pop(key, None)
    return result
