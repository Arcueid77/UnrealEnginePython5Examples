"""Physical pad pickup -> native inventory/equipment -> real Lyra fire input.

Only disposable-stage test pads are destroyed. Additional inventory entries
are removed with native services; the real player's original slots/item IDs,
selected slot, position, movement mode and aim are restored before exit.
"""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine import FVector, FTransform
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_hud.ammo_mixin import _stat, MAGAZINE_AMMO
from uep_lyra_network_bots import isolate_bots
from uep_lyra_weapon_input import aim_above_players
from . import inventory_pad_mixin as policy
from .inventory_pad_player_contract import CASES


def check(value, message):
    if not value:
        raise AssertionError(message)


def path(value):
    return value.get_path_name() if valid(value) else None


class Validation:
    def __init__(self, result):
        self.result, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.finished, self.index, self.actors = False, 0, []
        self.controller = self.pawn = self.inventory = self.quickbar = self.movement = None
        self.original_items = None
        self.sides, self.rollbacks, self.frames = [], [], []
        self.report = {"schema_version": 1, "status": "running", "error": None, "cases": [],
            "network_acceptance": False, "full_acceptance": False, "packaged_runtime": False,
            "overlap_handler_called_by_probe": False, "ammo_properties_written": False,
            "inventory_properties_written": False, "manual_lifecycle_event": False,
            "fixture_native_inventory_setup": True, "fixture_native_pawn_teleport": True,
            "original_player_restored": False}

    def enter(self, phase):
        self.phase, self.phase_started = phase, time.monotonic()

    def items(self):
        return self.inventory.call_function("GetAllItems")

    def fingerprint(self):
        return {"items": sorted(path(item) for item in self.items()),
                "slots": [path(item) for item in self.quickbar.call_function("GetSlots")],
                "active": int(self.quickbar.call_function("GetActiveSlotIndex"))}

    def normalized(self):
        return {"items": sorted(path(item.ItemDef) for item in self.items()),
                "slots": [path(item.ItemDef) if valid(item) else None for item in self.quickbar.call_function("GetSlots")],
                "active": int(self.quickbar.call_function("GetActiveSlotIndex"))}

    def input(self, pressed):
        for name in ("IA_Weapon_Fire", "IA_Weapon_Fire_Auto"):
            action = ue.load_object(ue.find_class("InputAction"), "/Game/Input/Actions/"+name+"."+name)
            self.controller.inject_enhanced_input_for_action(action, pressed)

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
            if not (state.bExperienceLoaded and state.bHealthReady and state.bAbilitySystemReady and state.bHeroInputReady and not state.bDamageImmune):
                continue
            check(str(state.NetMode) == "Standalone", "player inventory needs standalone authority")
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):
                continue
            quickbar = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
            inventory = controller.get_component_by_type(ue.find_class("LyraInventoryManagerComponent"))
            if not valid(quickbar) or not valid(inventory) or not valid(quickbar.call_function("GetActiveSlotItem")):
                continue
            self.world, self.controller, self.pawn = world, controller, controller.get_controlled_pawn()
            self.inventory, self.quickbar = inventory, quickbar
            self.movement = self.pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
            check(valid(self.movement), "native Character movement unavailable")
            check(int(quickbar.call_function("GetNextFreeItemSlot")) >= 0, "initial Lyra inventory has no free slot")
            self.original_items = {path(item) for item in self.items()}
            self.original = self.fingerprint()
            self.original_location = self.pawn.get_actor_location()
            self.original_rotation = controller.call_function("GetControlRotation")
            self.original_mode, self.original_custom_mode = int(self.movement.MovementMode), int(self.movement.CustomMovementMode)
            self.movement.call_function("StopMovementImmediately")
            self.movement.call_function("DisableMovement")
            aim_above_players(controller)
            self.definition = ue.load_class("/ShooterCore/Weapons/Pistol/ID_Pistol.ID_Pistol_C")
            self.classes = [ue.load_class(policy.CLASS), ue.load_class(policy.MESH_CLASS)]
            self.report.update(net_mode="Standalone", controller=path(controller), pawn=path(self.pawn))
            self.begin()
            return

    def rollback(self):
        self.input(False)
        for slot, item in enumerate(self.quickbar.call_function("GetSlots")):
            if valid(item) and path(item) not in self.original_items:
                self.quickbar.call_function("RemoveItemFromSlot", slot)
        for item in self.items():
            if path(item) not in self.original_items:
                self.inventory.call_function("RemoveItemInstance", item)
        if int(self.quickbar.call_function("GetActiveSlotIndex")) != self.original["active"]:
            self.quickbar.call_function("SetActiveSlotIndex", self.original["active"])
        check(self.fingerprint() == self.original, "native inventory rollback changed original item/slot identity")

    def begin(self):
        self.profile = ("Python", "BlueprintFallback")[self.index % 2]
        self.case_index = self.index//2
        self.full = self.case_index >= 2
        if self.full:
            for slot, item in enumerate(self.quickbar.call_function("GetSlots")):
                if item is None:
                    created = self.inventory.call_function("AddItemDefinition", self.definition, 1)
                    self.quickbar.call_function("AddItemToSlot", slot, created)
        self.before, self.before_count = self.normalized(), len(self.items())
        center = FVector(self.original_location.x+6000.0+self.index*900.0, self.original_location.y, self.original_location.z+500.0)
        transform = FTransform()
        transform.translation = center
        cls = self.classes[self.case_index % 2]
        pad = self.statics.call_function("BeginDeferredActorSpawnFromClass", self.world, cls, transform, 1, None)
        check(valid(pad), "real-player pad native deferred spawn failed")
        self.actors.append(pad)
        ue.set_mixin_profile(pad, self.profile)
        pad.set_property("ItemDefinition", self.definition)
        pad.set_property("bDestroyOnPickup", False)
        self.statics.call_function("FinishSpawningActor", pad, transform)
        self.pad, self.expected_class = pad, cls.get_path_name()
        check(ue.get_mixin_profile(pad) == self.profile, "wrong real-player pad Profile")
        self.expected_slot = int(self.quickbar.call_function("GetNextFreeItemSlot"))
        check(self.pawn.set_actor_location(pad.Volume.call_function("K2_GetComponentLocation")), "real Pawn physical relocation rejected")
        self.input_frames = 0
        self.enter("overlap")

    def side_done(self, value):
        self.input(False)
        self.sides.append(value)
        self.frames.append(self.input_frames)
        self.rollback()
        self.rollbacks.append(True)
        check(self.pad.get_class().get_path_name() == self.expected_class, "real-player pad type changed")
        self.pad.actor_destroy()
        if self.index % 2:
            check(self.sides[0] == self.sides[1], "real-player BP/Python mismatch: "+repr(self.sides))
            self.report["cases"].append({"name": CASES[self.case_index], "passed": True, "same_class": True,
                "python": self.sides[0], "blueprint": self.sides[1], "native_input_frames": self.frames,
                "native_rollbacks": self.rollbacks})
            ue.log("UEP_INVENTORY_PLAYER_CASE_PASSED "+CASES[self.case_index])
            self.sides, self.frames, self.rollbacks = [], [], []
        self.index += 1
        if self.index == 8:
            self.finish()
        else:
            self.begin()

    def finish(self, error=None):
        self.finished = True
        try:
            if self.original_items is not None:
                self.rollback()
                check(self.pawn.set_actor_location(self.original_location), "original player location restoration rejected")
                self.movement.call_function("StopMovementImmediately")
                self.movement.call_function("SetMovementMode", self.original_mode, self.original_custom_mode)
                self.controller.call_function("SetControlRotation", self.original_rotation)
                location, rotation = self.pawn.get_actor_location(), self.controller.call_function("GetControlRotation")
                restore = {"inventory_identity_equal": self.fingerprint() == self.original,
                    "position_max_error": max(abs(getattr(location, key)-getattr(self.original_location, key)) for key in ("x", "y", "z")),
                    "aim_max_error": max(abs(getattr(rotation, key)-getattr(self.original_rotation, key)) for key in ("pitch", "yaw", "roll")),
                    "movement": [int(self.movement.MovementMode), int(self.movement.CustomMovementMode)],
                    "expected_movement": [self.original_mode, self.original_custom_mode]}
                self.report["player_restore"] = restore
                self.report["original_player_restored"] = (restore["inventory_identity_equal"] and restore["position_max_error"] < .01 and
                    restore["aim_max_error"] < .01 and restore["movement"] == restore["expected_movement"])
                check(self.report["original_player_restored"], "real-player native restore observation differs")
            for pad in self.actors:
                if valid(pad):
                    pad.actor_destroy()
            check(not any(valid(pad) for pad in self.actors), "real-player fixture pad retained")
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
            actors_created=len(self.actors), actors_destroyed=sum(not valid(pad) for pad in self.actors),
            elapsed_seconds=time.monotonic()-self.started)
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_INVENTORY_PLAYER_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .inventory_pad_player_contract import validate
                self.report["status"] = "passed"
                validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_INVENTORY_PLAYER_SHUTDOWN_"+self.report["status"].upper())

    def tick(self, delta):
        if self.finished:
            return False
        try:
            check(time.monotonic()-self.started < 240, "real-player inventory timeout: "+self.phase)
            if self.phase == "ready":
                self.ready()
            elif self.phase == "overlap" and time.monotonic()-self.phase_started > .25:
                if self.full:
                    self.side_done({"item_delta": len(self.items())-self.before_count,
                                    "inventory_unchanged": self.normalized() == self.before})
                else:
                    check(len(self.items()) == self.before_count+1, "real Pawn overlap did not grant exactly one item")
                    self.item = self.quickbar.call_function("GetActiveSlotItem")
                    check(int(self.quickbar.call_function("GetActiveSlotIndex")) == self.expected_slot, "native new item not selected")
                    equipment = self.quickbar.get_property("EquippedItem")
                    check(valid(equipment) and equipment.call_function("GetInstigator") == self.item, "native equipment not bound to granted item")
                    self.equipment_class, self.magazine_before = path(equipment.get_class()), int(_stat(self.item, MAGAZINE_AMMO))
                    check(self.magazine_before > 0, "native granted pistol has no loaded ammo")
                    self.enter("fire")
            elif self.phase == "fire":
                magazine = int(_stat(self.item, MAGAZINE_AMMO))
                if magazine < self.magazine_before:
                    self.side_done({"item_delta": len(self.items())-self.before_count, "selected_slot": self.expected_slot,
                        "definition": path(self.item.ItemDef), "equipment_class": self.equipment_class,
                        "native_equipment_instigator_matches": True, "magazine_before": self.magazine_before, "magazine_after": magazine})
                else:
                    check(time.monotonic()-self.phase_started < 5.0, "newly equipped native pistol did not fire via Enhanced Input")
                    self.input((time.monotonic()-self.phase_started) % .30 < .12)
                    self.input_frames += 1
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False


if any(value.startswith("-UEPInventoryPadPlayerResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPInventoryPadPlayerResult="))
    validation = Validation(result)
    atexit.register(validation.finalize)
    ticker = ue.add_ticker(validation.tick)
