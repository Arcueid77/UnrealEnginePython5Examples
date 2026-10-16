"""Real native component lifecycle and original BP, never lifecycle replay."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine import FVector, FTransform
from . import nameplate_source_mixin as sources, nameplate_manager_mixin as managers
from . import nameplate_messages as messages
from .nameplate_components_contract import CASES
from .weapon_observer import valid
from uep_lyra_network_bots import isolate_bots


def check(value, reason):
    if not value:
        raise AssertionError(reason)


def path(value):
    return value.get_path_name() if valid(value) else None


def vector(value):
    return [float(value.x), float(value.y), float(value.z)]


def descriptor(value):
    return {"data": path(value.call_function("GetDataObject")),
            "scene": path(value.call_function("GetSceneComponent")),
            "widget": path(value.call_function("GetIndicatorClass")),
            "projection": int(value.call_function("GetProjectionMode")),
            "anchor": vector(value.call_function("GetBoundingBoxAnchor")),
            "offset": vector(value.call_function("GetWorldPositionOffset")),
            "vertical": int(value.call_function("GetVAlign")),
            "clamp": bool(value.call_function("GetClampToScreen")),
            "auto_remove": bool(value.call_function("GetAutoRemoveWhenIndicatorComponentIsNull"))}


class Validation:
    def __init__(self, result):
        self.result, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.actors, self.components, self.tracked_descriptors = [], [], {}
        self.helper = None
        self.finished = False
        self.report = {"schema_version": 1, "status": "running", "cases": [], "error": None,
            "full_acceptance": False, "network_acceptance": False, "packaged_runtime": False,
            "fixture_lifecycle_event_invoked": False, "native_health_team_inventory_written": False,
            "projection_parity_tested": False, "legacy_policy_silently_fixed": False,
            "actual_production_manager": False, "native_indicator_membership_read": False,
            "native_source_endplay": False, "native_nonlocal_destroy": False,
            "native_baseline_endplay": False, "legacy_duplicate_confirmed": False,
            "fixture_only_orphans_cleaned": False}

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def native_members(self):
        return {path(value): value for value in self.native.get_property("Indicators") if valid(value)}

    def entries(self, manager):
        return dict(manager.IndicatorMap)

    def capture(self, manager):
        members = self.native_members()
        values = self.entries(manager)
        result = {}
        for pawn, item in values.items():
            check(valid(pawn) and valid(item), "invalid native descriptor/map entry")
            self.tracked_descriptors[path(item)] = item
            check(path(item) in members, "map descriptor missing from native manager")
            result[path(pawn)] = descriptor(item)
        return result

    def record(self, name, actual, original, same_class=True):
        check(CASES[len(self.report["cases"])] == name, "component case order differs")
        check(actual == original and same_class, "component BP difference: " + name + " " + repr((actual, original)))
        self.report["cases"].append({"name": name, "passed": True, "same_class": same_class,
                                     "python": actual, "blueprint": original})
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        ue.log("UEP_NAMEPLATE_COMPONENT_CASE_PASSED " + name)

    def compare(self, name):
        self.record(name, self.capture(self.candidate), self.capture(self.baseline),
                    self.candidate.get_class() == self.baseline.get_class())

    def add_component(self, owner, cls, profile):
        component = owner.call_function("AddComponentByClass", cls, False, FTransform(), True)
        check(valid(component), "native deferred component creation failed")
        self.components.append(component)
        ue.set_mixin_profile(component, profile)
        owner.call_function("FinishAddComponent", component, False, FTransform())
        return component

    def spawn_source(self, cls_name, profile):
        pawn = self.world.actor_spawn(ue.find_class(cls_name), FVector(15000.0, 15000.0+len(self.actors)*1000.0, 500.0))
        self.actors.append(pawn)
        source = self.add_component(pawn, self.source_cls, profile)
        check(valid(source), "source native BeginPlay unexpectedly destroyed it")
        return pawn, source

    def ready(self):
        statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge):
                continue
            isolate_bots(statics, world, ue.find_class("LyraPlayerBotController"))
            state = bridge.call_function("CaptureSnapshot")
            if not (state.bExperienceLoaded and state.bHealthReady and not state.bDamageImmune):
                continue
            controller = statics.call_function("GetPlayerController", world, 0)
            if not valid(controller):
                continue
            self.manager_cls, self.source_cls = ue.load_class(managers.CLASS), ue.load_class(sources.CLASS)
            found = controller.call_function("K2_GetComponentsByClass", self.manager_cls)
            found = [value for value in found if valid(value) and ue.get_mixin_profile(value) == "Python"]
            if len(found) != 1 or not found[0].IndicatorMap:
                continue
            self.world, self.controller, self.candidate = world, controller, found[0]
            self.native = ue.find_class("IndicatorLibrary").get_cdo().call_function("GetIndicatorManagerComponent", controller)
            check(valid(self.native), "native indicator manager missing")
            self.initial_members = set(self.native_members())
            self.report.update(actual_production_manager=True, native_indicator_membership_read=True,
                               production_manager=path(self.candidate))
            self.helper = ue.new_object(self.candidate.PythonMessageAdapterClass)
            self.helper.add_to_root()
            self.baseline = self.add_component(controller, self.manager_cls, "BlueprintFallback")
            self.enter("initial")
            return

    def cleanup(self):
        for component in self.components:
            if valid(component):
                component.call_function("K2_DestroyComponent", component)
        # Deliberately duplicated original-BP descriptors can be orphaned by
        # Map_Add. This is fixture-only cleanup, not a production policy fix.
        for key, item in self.tracked_descriptors.items():
            if key not in getattr(self, "initial_members", set()) and valid(item):
                item.call_function("UnregisterIndicator")
        if valid(getattr(self, "native", None)):
            for key, item in self.native_members().items():
                if key not in self.initial_members:
                    item.call_function("UnregisterIndicator")
            check(set(self.native_members()).issubset(self.initial_members), "fixture descriptor still natively registered")
        for actor in self.actors:
            if valid(actor):
                actor.call_function("K2_DestroyActor")
        if valid(self.helper):
            self.helper.remove_from_root()
            self.helper = None
        self.report["fixture_only_orphans_cleaned"] = True

    def finish(self, error=None):
        self.finished = True
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic()-self.started)
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_NAMEPLATE_COMPONENTS_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report.update(source_shutdown=sources.snapshot(), manager_shutdown=managers.snapshot())
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        if self.report["status"] == "passed":
            try:
                from .nameplate_components_contract import validate
                validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_NAMEPLATE_COMPONENTS_SHUTDOWN_" + self.report["status"].upper())

    def tick(self, delta):
        if self.finished:
            return False
        try:
            check(time.monotonic()-self.started < 180, "component total timeout: " + self.phase)
            if self.phase == "ready":
                self.ready()
                return True
            if time.monotonic()-self.phase_started < 0.6:
                return True
            if self.phase == "initial":
                self.record(CASES[0], {"nonempty": bool(self.capture(self.candidate)),
                    "local": bool(self.candidate.call_function("GetOwner").call_function("IsLocalPlayerController"))},
                    {"nonempty": bool(self.capture(self.baseline)),
                    "local": bool(self.baseline.call_function("GetOwner").call_function("IsLocalPlayerController"))},
                    self.candidate.get_class() == self.baseline.get_class())
                check(bool(self.candidate.IndicatorMap) and bool(self.baseline.IndicatorMap), "native managers did not discover sources")
                self.compare(CASES[1])
                self.character, self.py_source = self.spawn_source("Character", "Python")
                self.enter("character")
            elif self.phase == "character":
                self.compare(CASES[2])
                item = self.entries(self.candidate)[self.character]
                check(descriptor(item)["projection"] == 1 and descriptor(item)["anchor"] == [.5, .5, 1.0], "character descriptor policy differs")
                self.pawn, self.bp_source = self.spawn_source("DefaultPawn", "BlueprintFallback")
                self.enter("pawn")
            elif self.phase == "pawn":
                self.compare(CASES[3])
                item = descriptor(self.entries(self.candidate)[self.pawn])
                check(item["projection"] == 0 and item["offset"] == [0.0, 0.0, 100.0], "plain Pawn descriptor policy differs")
                self.before_candidate = {path(k): path(v) for k, v in self.entries(self.candidate).items()}
                self.before_baseline = self.entries(self.baseline)
                self.discoveries = self.py_source._uep_np_discoveries
                messages.broadcast(self.controller, self.helper, "Discover", self.baseline)
                self.enter("discover")
            elif self.phase == "discover":
                self.compare(CASES[4])
                check(self.py_source._uep_np_discoveries == self.discoveries+1, "targeted discovery did not enter Python Source")
                check(self.before_candidate == {path(k): path(v) for k, v in self.entries(self.candidate).items()}, "targeted discovery changed another manager")
                check(path(self.before_baseline[self.pawn]) != path(self.entries(self.baseline)[self.pawn]), "original-BP Source did not register on Discover")
                self.duplicate_old = [self.entries(value)[self.character] for value in (self.candidate, self.baseline)]
                for manager in (self.candidate, self.baseline):
                    manager.call_function("RegisterNameplateSource", self.character)
                self.enter("duplicate")
            elif self.phase == "duplicate":
                self.compare(CASES[5])
                membership = self.native_members()
                check(all(path(item) in membership for item in self.duplicate_old), "legacy descriptor was silently deduplicated")
                check(all(path(item) != path(self.entries(manager)[self.character]) for item, manager in
                          zip(self.duplicate_old, (self.candidate, self.baseline))), "duplicate did not replace Map value")
                self.report["legacy_duplicate_confirmed"] = True
                self.adds_before = sources.snapshot()["adds"]
                for profile in ("BlueprintFallback", "Python"):
                    ue.set_mixin_profile(self.py_source, profile)
                    self.py_source.call_function(sources.RESUME)
                    messages.broadcast(self.controller, self.helper, "Discover", self.candidate)
                self.enter("source-profile")
            elif self.phase == "source-profile":
                self.compare(CASES[6])
                check(sources.snapshot()["adds"] == self.adds_before, "Profile resume fabricated Source BeginPlay/Add")
                self.maps_before = {path(k): path(v) for k, v in self.entries(self.candidate).items()}
                self.discover_before = managers.snapshot()["discover_broadcasts"]
                for profile in ("BlueprintFallback", "Python"):
                    ue.set_mixin_profile(self.candidate, profile)
                    self.candidate.call_function(managers.RESUME)
                self.enter("manager-profile")
            elif self.phase == "manager-profile":
                self.compare(CASES[7])
                check(self.maps_before == {path(k): path(v) for k, v in self.entries(self.candidate).items()}, "Manager resume replayed descriptor creation")
                check(managers.snapshot()["discover_broadcasts"] == self.discover_before, "Manager resume replayed Discover")
                for source in (self.py_source, self.bp_source):
                    source.call_function("K2_DestroyComponent", source)
                self.enter("remove")
            elif self.phase == "remove":
                self.compare(CASES[8])
                check(not valid(self.py_source) and not valid(self.bp_source), "native Source destruction did not complete")
                for manager in (self.candidate, self.baseline):
                    check(self.character not in self.entries(manager) and self.pawn not in self.entries(manager), "native EndPlay Remove did not clear maps")
                self.report["native_source_endplay"] = True
                rejected = [self.add_component(self.character, self.manager_cls, profile) for profile in ("Python", "BlueprintFallback")]
                self.record(CASES[9], {"destroyed": not valid(rejected[0])}, {"destroyed": not valid(rejected[1])})
                check(not any(valid(value) for value in rejected), "nonlocal managers remained alive")
                self.report["native_nonlocal_destroy"] = True
                self.end_probe = self.add_component(self.controller, self.manager_cls, "Python")
                self.enter("baseline-end-prepare")
            elif self.phase == "baseline-end-prepare":
                check(self.capture(self.end_probe) == self.capture(self.baseline), "native manager EndPlay probe discovery differs")
                self.end_same_class = self.end_probe.get_class() == self.baseline.get_class()
                self.end_probe.call_function("K2_DestroyComponent", self.end_probe)
                self.baseline.call_function("K2_DestroyComponent", self.baseline)
                self.enter("baseline-end")
            elif self.phase == "baseline-end":
                self.record(CASES[10], {"destroyed": not valid(self.end_probe)},
                            {"destroyed": not valid(self.baseline)}, self.end_same_class)
                check(not valid(self.end_probe) and not valid(self.baseline), "native manager EndPlay did not finish")
                self.report["native_baseline_endplay"] = True
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPNameplateComponentsResult="))
validation = Validation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
