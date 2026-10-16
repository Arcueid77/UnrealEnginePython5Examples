"""Bounded test-owned native inventory/overlap proof, not production networking."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine import FVector, FTransform
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_bots import isolate_bots
from . import inventory_pad_mixin as policy
from .inventory_pad_contract import CASES, equal


def check(value, message):
    if not value:
        raise AssertionError(message)


def path(value):
    return value.get_path_name() if valid(value) else None


def native_inventory(controller):
    inventory = controller.get_component_by_type(ue.find_class("LyraInventoryManagerComponent"))
    quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
    return {"items": [path(item.ItemDef) for item in inventory.call_function("GetAllItems")],
            "slots": [path(item.ItemDef) if valid(item) else None for item in quickbar.call_function("GetSlots")],
            "active": int(quickbar.call_function("GetActiveSlotIndex"))}


def construction(actor):
    material = actor.Pad.call_function("GetMaterial", 0)
    color = material.call_function("K2_GetVectorParameterValue", "Color")
    value = {"text": str(actor.Text.get_property("Text")), "pickup_mesh": path(actor.PickUpMesh),
             "color": [float(color.r), float(color.g), float(color.b), float(color.a)]}
    if actor.is_a(ue.load_class(policy.MESH_CLASS)):
        value["component_mesh"] = path(actor.SkeletalMesh.call_function("GetSkeletalMeshAsset"))
    return value


class Validation:
    def __init__(self, result):
        self.result, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.actors, self.finished, self.sequence = [], False, 0
        self.report = {"schema_version": 1, "status": "running", "error": None, "cases": [],
            "full_acceptance": False, "network_acceptance": False, "production_placement_tested": False,
            "production_equipment_gas_tested": False, "remote_audio_tested": False, "packaged_runtime": False,
            "native_exception_gate_tested": False,
            "manual_lifecycle_event": False, "overlap_handler_called_by_probe": False,
            "inventory_properties_written_by_probe": False, "fixture_native_inventory_setup": True,
            "test_owned_controller_pawn_services": True, "numeric_tolerance": .001}

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def own(self, actor):
        check(valid(actor), "native test actor creation failed")
        self.actors.append(actor)
        return actor

    def component(self, actor, name):
        return actor.call_function("AddComponentByClass", ue.find_class(name), False, FTransform(), False)

    def spawn_pad(self, cls, profile, location, destroy=False):
        transform = FTransform()
        transform.translation = location
        actor = self.own(self.statics.call_function("BeginDeferredActorSpawnFromClass", self.world, cls, transform, 1, None))
        ue.set_mixin_profile(actor, profile)
        actor.set_property("ItemDefinition", self.definition)
        actor.set_property("bDestroyOnPickup", destroy)
        self.statics.call_function("FinishSpawningActor", actor, transform)
        return actor

    def create_pair(self, cls, scenario="visual"):
        self.sequence += 1
        self.pair = []
        for index, profile in enumerate(("Python", "BlueprintFallback")):
            center = FVector(12000.0+self.sequence*1600.0, 10000.0+index*1500.0, 700.0)
            pad = self.spawn_pad(cls, profile, center, scenario == "destroy")
            controller = self.own(self.world.actor_spawn(ue.find_class("PlayerController"), FVector(center.x+600.0, center.y, center.z)))
            self.component(controller, "LyraInventoryManagerComponent")
            self.component(controller, "LyraQuickBarComponent")
            pawn = self.own(self.world.actor_spawn(ue.find_class("DefaultPawn"), FVector(center.x+600.0, center.y, center.z)))
            if scenario != "no-controller":
                controller.call_function("Possess", pawn)
            if scenario == "full":
                inventory = controller.get_component_by_type(ue.find_class("LyraInventoryManagerComponent"))
                quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
                for slot in range(len(quickbar.call_function("GetSlots"))):
                    item = inventory.call_function("AddItemDefinition", self.definition, 1)
                    quickbar.call_function("AddItemToSlot", slot, item)
            self.pair.append((pad, controller, pawn))
        self.same_class = self.pair[0][0].get_class() == self.pair[1][0].get_class()

    def clear_pair(self):
        for pad, controller, pawn in self.pair:
            for actor in (pad, pawn, controller):
                if valid(actor):
                    actor.actor_destroy()  # Native AController::K2_DestroyActor is deliberately a no-op.
        self.pair = []

    def record(self, name, actual, original):
        check(name == CASES[len(self.report["cases"])], "inventory case order differs")
        check(self.same_class and equal(actual, original), "inventory BP/Python mismatch: "+name+" "+repr((actual, original)))
        self.report["cases"].append({"name": name, "passed": True, "same_class": self.same_class, "python": actual, "blueprint": original})
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        ue.log("UEP_INVENTORY_PAD_CASE_PASSED "+name)

    def ready(self):
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge):
                continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            state = bridge.call_function("CaptureSnapshot")
            if not (state.bExperienceLoaded and state.bHealthReady and not state.bDamageImmune):
                continue
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if not valid(controller):
                continue
            quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
            item = quickbar.call_function("GetActiveSlotItem") if valid(quickbar) else None
            if not valid(item):
                continue
            self.world, self.definition = world, item.ItemDef
            self.parent, self.child = ue.load_class(policy.CLASS), ue.load_class(policy.MESH_CLASS)
            self.create_pair(self.parent)
            self.enter("parent-construction")
            return

    def yaw(self):
        return [float(pad.SkeletalMesh.get_property("RelativeRotation").yaw) for pad, controller, pawn in self.pair]

    def pickup_start(self):
        cls, self.scenario, self.case_name = self.plan.pop(0)
        self.create_pair(cls, self.scenario)
        self.before = [native_inventory(controller) for pad, controller, pawn in self.pair]
        for pad, controller, pawn in self.pair:
            location = pad.Volume.call_function("K2_GetComponentLocation")
            check(pawn.set_actor_location(location), "native collision relocation rejected")
        self.enter("pickup")

    def finish(self, error=None):
        self.finished = True
        try:
            for actor in reversed(self.actors):
                if valid(actor):
                    actor.actor_destroy()
            survivors = [path(actor) for actor in self.actors if valid(actor)]
            check(not survivors, "test-owned actors survived native destruction: "+repr(survivors))
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
            elapsed_seconds=time.monotonic()-self.started, native_test_actors_destroyed=sum(not valid(actor) for actor in self.actors),
            actors_created=len(self.actors), policy=policy.snapshot())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_INVENTORY_PAD_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .inventory_pad_contract import validate
                self.report["status"] = "passed"
                validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_INVENTORY_PAD_SHUTDOWN_"+self.report["status"].upper())

    def tick(self, delta):
        if self.finished:
            return False
        try:
            check(time.monotonic()-self.started < 200, "inventory total timeout: "+self.phase)
            if self.phase == "ready":
                self.ready()
                return True
            if time.monotonic()-self.phase_started < .5:
                return True
            if self.phase == "parent-construction":
                self.record(CASES[0], construction(self.pair[0][0]), construction(self.pair[1][0]))
                self.clear_pair()
                self.create_pair(self.child)
                self.enter("mesh-construction")
            elif self.phase == "mesh-construction":
                self.record(CASES[1], construction(self.pair[0][0]), construction(self.pair[1][0]))
                self.yaws = self.yaw()
                self.tick_before = policy.snapshot()["mesh_ticks"]
                self.enter("mesh-tick")
            elif self.phase == "mesh-tick":
                now = self.yaw()
                changes = [(value-before+180.0)%360.0-180.0 for value, before in zip(now, self.yaws)]
                check(changes[0] > 1.0 and policy.snapshot()["mesh_ticks"] > self.tick_before, "no automatic native mesh Tick entered Python")
                self.record(CASES[2], {"yaw_change": changes[0]}, {"yaw_change": changes[1]})
                ue.set_mixin_profile(self.pair[0][0], "BlueprintFallback")
                self.yaws = self.yaw()
                self.enter("mesh-profile-original")
            elif self.phase == "mesh-profile-original":
                now = self.yaw()
                check(abs((now[0]-self.yaws[0])-(now[1]-self.yaws[1])) < .001, "native original Profile Tick differs")
                ue.set_mixin_profile(self.pair[0][0], "Python")
                self.yaws = self.yaw()
                self.enter("mesh-profile-python")
            elif self.phase == "mesh-profile-python":
                now = self.yaw()
                self.record(CASES[3], {"yaw_change": now[0]-self.yaws[0]}, {"yaw_change": now[1]-self.yaws[1]})
                self.clear_pair()
                self.plan = [(cls, scenario, CASES[4+number*2+kind]) for number, scenario in
                    enumerate(("empty", "full", "no-controller", "destroy")) for kind, cls in enumerate((self.parent, self.child))]
                self.pickup_start()
            elif self.phase == "pickup":
                values = [{"inventory": native_inventory(controller), "pad_destroyed": not valid(pad)} for pad, controller, pawn in self.pair]
                if self.scenario in ("empty", "destroy"):
                    check(all(len(value["inventory"]["items"]) == 1 and value["inventory"]["active"] == 0 for value in values), "native overlap did not grant/select exactly one item")
                else:
                    check(all(value["inventory"] == before for value, before in zip(values, self.before)), "invalid/full overlap changed native inventory")
                check(all(value["pad_destroyed"] is (self.scenario == "destroy") for value in values), "native pad destruction policy differs")
                self.record(self.case_name, values[0], values[1])
                self.clear_pair()
                if self.plan:
                    self.pickup_start()
                else:
                    self.finish()
                    return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


result = next(arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("-UEPInventoryPadResult="))
validation = Validation(result)
atexit.register(validation.finalize)
ticker = ue.add_ticker(validation.tick)
