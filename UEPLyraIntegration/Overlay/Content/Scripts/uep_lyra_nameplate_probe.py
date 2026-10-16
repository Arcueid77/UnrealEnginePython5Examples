"""Read native component maps/indicators and compare production UI with old BP.

Only the baseline uses explicit BindIndicator interface calls. Production
Source/Manager/Widget receive their native lifecycle and indicator callbacks.
No message, health, team, inventory or lifecycle event is injected here.
"""
import sys
import unreal_engine as ue
from unreal_engine import FTransform
from uep_lyra_hud import nameplate_mixin as widgets, nameplate_source_mixin as sources, nameplate_manager_mixin as managers
from uep_lyra_hud.nameplate_refs import optional_ref
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_protocol import require

_original_remove_traces = []


class OriginalRemoveDiagnostic(managers.LyraNameplateManagerBlueprintFallbackProfile):
    """Opt-in fixture only: preserve the BP body and record native call boundaries."""
    def UnregisterNameplateSource(self, IndicatedPawn):
        row = {"manager": path(self), "pawn": path(IndicatedPawn),
               "before": [path(key) for key in self.IndicatorMap]}
        try:
            return self.call_mixin_original("UnregisterNameplateSource", IndicatedPawn)
        finally:
            row["after"] = [path(key) for key in self.IndicatorMap]
            _original_remove_traces.append(row)
            del _original_remove_traces[:-24]


def path(value):
    return value.get_path_name() if valid(value) else None


def config(item):
    def vector(value):
        return [float(value.x), float(value.y), float(value.z)]
    return {"pawn": path(item.call_function("GetDataObject")), "scene": path(item.call_function("GetSceneComponent")),
            "projection": int(item.call_function("GetProjectionMode")), "anchor": vector(item.call_function("GetBoundingBoxAnchor")),
            "offset": vector(item.call_function("GetWorldPositionOffset")), "class": path(item.call_function("GetIndicatorClass")),
            "vertical": int(item.call_function("GetVAlign")), "clamp": bool(item.call_function("GetClampToScreen")),
            "auto_remove": bool(item.call_function("GetAutoRemoveWhenIndicatorComponentIsNull"))}


def visual(widget):
    material = widget.Health.call_function("GetDynamicMaterial")
    resource = widget.Health.Brush.ResourceObject
    if valid(resource) and resource.is_a(ue.find_class("MaterialInstanceDynamic")):
        resource = resource.Parent
    return {"name": str(widget.Name.call_function("GetText")), "visibility": int(widget.call_function("GetVisibility")),
            "resource": path(resource),
            "progress": float(material.call_function("K2_GetScalarParameterValue", "Progress")) if valid(material) else 0.0}


class NameplateProbe:
    def __init__(self):
        self.manager = self.original = None
        self.world_token = None
        self.widget_pairs = {}
        self.previous_pawns = set()
        self.map_removals, self.world_epochs = 0, 0
        self.debug = {"reason": "not-created"}
        self.native_bind_pairs = 0
        self.trace_original_remove = "-UEPNameplateOriginalTrace" in sys.argv
        self.trace_profile_registered = False
        self.roots_created = self.roots_released = 0
        self.bind_observer = self.capture_native_bind
        self.release_observer = self.release_native_pair
        widgets._validation_bind_observers.append(self.bind_observer)
        widgets._validation_release_observers.append(self.release_observer)

    def root_evidence(self):
        return {"created": self.roots_created, "released": self.roots_released,
                "active": self.roots_created-self.roots_released,
                "pair_count": len(self.widget_pairs), "mounts_for_native_construct": True}

    def release_native_pair(self, candidate):
        key = path(candidate)
        if key in self.widget_pairs:
            self.close_pair(key)

    def close_pair(self, key):
        widget, indicator, _pawn = self.widget_pairs.pop(key)
        if valid(widget):
            try:
                widget.call_function("UnbindIndicator", optional_ref(widget, "Indicator"))
            finally:
                widget.RemoveFromParent()
                widget.remove_from_root()
                self.roots_released += 1
        if valid(indicator):
            indicator.remove_from_root()
            self.roots_released += 1

    def close(self, final=False):
        for key in list(self.widget_pairs):
            self.close_pair(key)
        if valid(self.original):
            self.original.call_function("K2_DestroyComponent", self.original)
        self.manager = self.original = None
        self.previous_pawns = set()
        if final and self.bind_observer in widgets._validation_bind_observers:
            widgets._validation_bind_observers.remove(self.bind_observer)
        if final and self.release_observer in widgets._validation_release_observers:
            widgets._validation_release_observers.remove(self.release_observer)
        if final:
            require(self.roots_created == self.roots_released, "test-owned nameplate comparator root leak")

    def capture_native_bind(self, candidate, native_indicator):
        controller = candidate.call_function("GetOwningPlayer")
        if not valid(controller) or not valid(candidate.Pawn):
            return
        key = path(candidate)
        if key in self.widget_pairs:
            self.close_pair(key)  # Native Indicator pool reused the same UI for a new Pawn.
        indicator = ue.new_object(ue.find_class("IndicatorDescriptor"))
        indicator.add_to_root()
        self.roots_created += 1
        indicator.call_function("SetDataObject", native_indicator.call_function("GetDataObject"))
        indicator.call_function("SetSceneComponent", native_indicator.call_function("GetSceneComponent"))
        widget = controller.create_widget(candidate.get_class())
        widget.add_to_root()
        self.roots_created += 1
        self.widget_pairs[key] = widget, indicator, path(candidate.Pawn)
        # This runs within another object's native Mixin call. Select the
        # authored instance Name BEFORE the first routed Bind; do not mutate
        # the registry with set_mixin_profile during a callback.
        widget.set_property("PythonMixinProfile", "BlueprintFallback")
        for field in ("HideOwnerName", "ShowTeamNamesOnly"):
            widget.set_property(field, getattr(candidate, field))
        # Preserve the native UMG Construct epoch used by the original BP.
        # An unmounted comparator stayed at designer defaults on respawn in
        # Network11, so it is not evidence of equivalent native initialization.
        widget.AddToViewport(450)
        widget.call_function("SetRenderOpacity", 0.0)
        require(ue.get_mixin_profile(widget) == "BlueprintFallback", "original baseline did not use its authored instance selector")
        widget.call_function("BindIndicator", indicator)
        self.native_bind_pairs += 1

    def baseline(self, controller, candidate):
        value = self.widget_pairs.get(path(candidate))
        return value[0] if value is not None and value[2] == path(candidate.Pawn) else None

    def observe(self, controller, player):
        manager_class = ue.load_class(managers.CLASS)
        found = [value for value in controller.call_function("K2_GetComponentsByClass", manager_class)
                 if valid(value) and ue.get_mixin_profile(value) == "Python"]
        require(len(found) <= 1, "duplicate production local nameplate managers")
        if len(found) != 1 or not found[0].IndicatorMap:
            self.debug = {"reason": "production-local-manager-unavailable", "count": len(found)}
            return None
        manager = found[0]
        if manager != self.manager or self.world_token != player["world_token"]:
            if valid(self.original):
                self.original.call_function("K2_DestroyComponent", self.original)
            # New-world native Binds can already have created the next pairs.
            # Reconcile below, rather than deleting those correctly timed BPs.
            self.previous_pawns = set()
            self.manager, self.world_token = manager, player["world_token"]
            self.world_epochs += 1
            profile = "BlueprintFallback"
            if self.trace_original_remove:
                if not self.trace_profile_registered:
                    ue.register_mixin_profile(manager_class, "OriginalRemoveDiagnostic", OriginalRemoveDiagnostic)
                    self.trace_profile_registered = True
                profile = "OriginalRemoveDiagnostic"
            self.original = controller.call_function("AddComponentByClass", manager_class, False, FTransform(), True)
            ue.set_mixin_profile(self.original, profile)
            controller.call_function("FinishAddComponent", self.original, False, FTransform())
        require(valid(self.original), "original-BP nameplate manager destroyed unexpectedly")
        native = ue.find_class("IndicatorLibrary").get_cdo().call_function("GetIndicatorManagerComponent", controller)
        if not valid(native):
            self.debug = {"reason": "native-indicator-manager-unavailable"}
            return None
        members = {path(item) for item in native.get_property("Indicators") if valid(item)}
        actual, original = dict(manager.IndicatorMap), dict(self.original.IndicatorMap)
        if set(actual) != set(original):
            self.debug = {"reason": "source-discovery-not-converged", "python": [path(p) for p in actual], "blueprint": [path(p) for p in original],
                          "manager_remove_traces": managers.snapshot()["remove_traces"][-6:],
                          "original_remove_traces": _original_remove_traces[-6:]}
            return None
        rows = []
        for pawn, indicator in actual.items():
            baseline = original[pawn]
            if not all(valid(item) for item in (pawn, indicator, baseline)):
                self.debug = {"reason": "native-map-removal-pending"}
                return None
            require(path(indicator) in members and path(baseline) in members, "nameplate descriptor missing from native Indicators")
            py, bp = config(indicator), config(baseline)
            require(py == bp, "nameplate native descriptor configuration differs: " + repr((path(pawn), py, bp)))
            components = pawn.call_function("K2_GetComponentsByClass", ue.load_class(sources.CLASS))
            if not any(valid(source) for source in components):
                self.debug = {"reason": "source-endplay-map-removal-pending", "pawn": path(pawn)}
                return None
            player_state = optional_ref(pawn, "PlayerState")
            rows.append({"pawn": path(pawn), "player_id": int(player_state.PlayerId) if valid(player_state) else None,
                         "python": py, "blueprint": bp, "native_membership": True, "native_source": True})
        pawns = {row["pawn"] for row in rows}
        self.map_removals += len(self.previous_pawns-pawns)
        self.previous_pawns = pawns
        if player["pawn_path"] not in pawns:
            self.debug = {"reason": "own-pawn-not-discovered", "pawns": sorted(pawns)}
            return None
        candidates = [ue.find_object(name) for name in widgets.snapshot()["active_widgets"]]
        candidates = [item for item in candidates if valid(item) and item.call_function("GetOwningPlayer") == controller and
                      valid(optional_ref(item, "Pawn")) and item.Pawn in actual and optional_ref(item, "Indicator") == actual[item.Pawn] and item._uep_np_init_callbacks > 0]
        keys = {path(item) for item in candidates}
        for key in list(self.widget_pairs):
            if key not in keys:
                self.close_pair(key)
        if not candidates:
            self.debug = {"reason": "production-native-indicator-widget-unavailable"}
            return None
        comparisons = []
        for candidate in candidates:
            baseline = self.baseline(controller, candidate)
            if not valid(baseline):
                self.debug = {"reason": "native-bind-comparator-unavailable", "widget": path(candidate)}
                return None
            py, bp = visual(candidate), visual(baseline)
            if py != bp:
                self.debug = {"reason": "native-nameplate-ui-not-converged", "pawn": path(candidate.Pawn), "python": py, "blueprint": bp}
                return None
            health = widgets.health_for(candidate.Pawn)
            maximum = float(health.call_function("GetMaxHealth")) if valid(health) else 0.0
            health_evidence = {"available": maximum > 0.0, "maximum": maximum, "normalized": None,
                "unavailable_reason": None if maximum > 0.0 else "native-attribute-set-not-initialized"}
            if maximum > 0.0 and valid(candidate.Health.Brush.ResourceObject):
                normalized = float(health.call_function("GetHealthNormalized"))
                health_evidence["normalized"] = normalized
                if abs(py["progress"]-normalized) > .0001:
                    self.debug = {"reason": "native-health-nameplate-not-converged", "pawn": path(candidate.Pawn),
                        "own_pawn": player["pawn_path"], "widget": path(candidate), "python": py, "blueprint": bp,
                        "native_health": float(health.call_function("GetHealth")),
                        "native_maximum": float(health.call_function("GetMaxHealth")), "native_normalized": normalized,
                        "pawn_controller": path(candidate.Pawn.call_function("GetController"))}
                    return None
            comparisons.append({"widget": path(candidate), "pawn": path(candidate.Pawn), "profile": str(ue.get_mixin_profile(candidate)),
                "class": candidate.get_class().get_name(), "same_class": candidate.get_class() == baseline.get_class(),
                "automatic_native_binding": True, "same_native_bind_comparator": True, "native_health": health_evidence,
                "python": py, "blueprint": bp})
        self.debug = {"reason": "ready", "pawns": sorted(pawns), "widget_count": len(comparisons), "world_epochs": self.world_epochs}
        return {"controller": path(controller), "pawn": player["pawn_path"], "world_token": self.world_token,
            "production_local_manager": path(manager), "manager_profile": str(ue.get_mixin_profile(manager)),
            "manager_same_class": manager.get_class() == self.original.get_class(), "descriptors": rows, "widgets": comparisons,
            "map_removals_observed": self.map_removals, "world_epochs": self.world_epochs,
            "bp_baseline_epoch_policy": "BP comparator Bind in production native Bind callback; no production replay or value copying",
            "native_bind_pairs": self.native_bind_pairs,
            "diagnostic_original_remove_wrapper": self.trace_original_remove,
            "original_remove_traces": _original_remove_traces[-6:],
            "comparator_roots": self.root_evidence(),
            "synthetic_messages": False, "native_state_written": False, "projection_parity_tested": False,
            "production_lifecycle_replayed": False}


def server_observation():
    from uep_lyra_nameplate_placement import read_placement
    state = {"sources": sources.snapshot(), "managers": managers.snapshot(), "widgets": widgets.snapshot()}
    state["native_placement"] = read_placement()
    require(state["managers"]["active_count"] == 0 and state["widgets"]["active_count"] == 0, "dedicated server retained local nameplates")
    return state
