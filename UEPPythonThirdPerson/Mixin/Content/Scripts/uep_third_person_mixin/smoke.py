"""Automated proof for live Blueprint-class Python mixins."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.structs import Key

from uep_third_person.constants import PICKUP_COUNT
from uep_third_person.utils import gameplay_objects, is_valid, request_exit

from . import __version__ as DEMO_VERSION
from .character_mixin import (
    BP_THIRD_PERSON_CHARACTER,
    MIXED_FUNCTIONS,
    register_character_mixin,
)


SMOKE_RESULT_PREFIX = "-UEPMixinThirdPersonSmokeResult="
PRESSED = 0
RELEASED = 1


def _command_line_value(prefix):
    for argument in sys.argv:
        if argument.startswith(prefix):
            return argument[len(prefix):].strip('"')
    return None


class MixinThirdPersonSmoke:
    def __init__(self, runtime, result_path):
        self.runtime = runtime
        self.result_path = result_path
        self.elapsed = 0.0
        self.phase = "waiting"
        self.phase_elapsed = 0.0
        self.phase_ticks = 0
        self.finished = False
        self.held_keys = set()
        self.start_location = None
        self.start_rotation = None
        self.movement_distance = 0.0
        self.look_delta = 0.0
        self.jump_height = 0.0
        self.original_restore_distance = 0.0
        self.live_reregister_distance = 0.0
        self.initial_snapshot = None
        self.pre_restore_snapshot = None
        self.restored_move_function = None
        self.injected_move_function = None
        self.re_registered_move_function = None
        self.registration_before = None
        self.registration_after_reregister = None
        self.first_teardown_events = 0
        self.invalid_registration_rejected = False
        self.invalid_registration_preserved_active = False
        self.gameplay_report = None
        self.teardown_report = None

    def _set_key(self, controller, key_name, event_type, amount):
        controller.input_key(Key(KeyName=key_name), event_type, amount)
        if event_type == PRESSED:
            self.held_keys.add(key_name)
        else:
            self.held_keys.discard(key_name)

    def _release_keys(self, controller):
        if not is_valid(controller):
            self.held_keys.clear()
            return
        for key_name in tuple(self.held_keys):
            self._set_key(controller, key_name, RELEASED, 0.0)

    def _registered_character_mixin(self):
        for registration in ue.get_registered_mixins():
            target = registration.get("target_class")
            if target is not None and target.get_name() == "BP_ThirdPersonCharacter_C":
                return registration
        return None

    def _session_report(self):
        session = self.runtime.session
        if session is None or session.closed:
            return None
        return {
            "generation": session.generation,
            "progress": session.gameplay.progress.snapshot(),
            "remaining_pickups": len(session.gameplay.pickups),
            "companion_valid": is_valid(session.gameplay.companion),
            "companion_movement": round(
                session.gameplay.companion_movement(),
                3,
            ),
            "hud": session.hud.snapshot(),
        }

    def _assert_class_identity(self, game_mode, controller, pawn):
        actual = (
            game_mode.get_class().get_name(),
            controller.get_class().get_name(),
            pawn.get_class().get_name(),
        )
        expected = (
            "BP_ThirdPersonGameMode_C",
            "BP_ThirdPersonPlayerController_C",
            "BP_ThirdPersonCharacter_C",
        )
        if actual != expected:
            raise RuntimeError(
                "mixin changed the official Blueprint class identity: "
                + ", ".join(actual)
            )

    def _validate_initial_contract(self, game_mode, controller, pawn):
        self._assert_class_identity(game_mode, controller, pawn)
        registration = self._registered_character_mixin()
        if registration is None:
            raise RuntimeError("character mixin registration is missing")
        functions = tuple(sorted(registration["functions"]))
        if functions != MIXED_FUNCTIONS:
            raise RuntimeError(
                "unexpected mixed function set: " + ", ".join(functions)
            )
        self.registration_before = {
            "registration_id": registration["registration_id"],
            "target_class": registration["target_class"].get_name(),
            "functions": functions,
        }

        snapshot = pawn.mixin_snapshot()
        if not snapshot["initialized"]:
            raise RuntimeError("per-UObject mixin state was not initialized")
        if snapshot["begin_play"] != 1:
            raise RuntimeError("mixed ReceiveBeginPlay did not execute exactly once")
        if snapshot["original_begin_play"] != 1:
            raise RuntimeError("Python did not call the original BeginPlay implementation")
        if snapshot["initializations"] != 1 or snapshot["teardowns"] != 0:
            raise RuntimeError("initial mixin lifecycle counters are incorrect")
        self.initial_snapshot = snapshot
        self.injected_move_function = pawn.find_function("Move")

        class InvalidSignatureMixin:
            def Move(self):
                pass

        try:
            ue.register_mixin(
                BP_THIRD_PERSON_CHARACTER,
                InvalidSignatureMixin,
            )
        except TypeError:
            self.invalid_registration_rejected = True
        else:
            raise RuntimeError("invalid Python Move signature was accepted")
        registration_after_rejection = self._registered_character_mixin()
        self.invalid_registration_preserved_active = (
            registration_after_rejection is not None
            and registration_after_rejection["registration_id"]
            == self.registration_before["registration_id"]
            and pawn.find_function("Move") is self.injected_move_function
        )
        if not self.invalid_registration_preserved_active:
            raise RuntimeError("invalid replacement removed the active mixin")

        session = self.runtime.session
        if session is None or session.closed:
            raise RuntimeError("Python collectible/HUD session is missing")
        if not session.hud.attached or session.hud.update_count <= 0:
            raise RuntimeError("Python viewport HUD is not active")
        if len(session.gameplay.pickups) != PICKUP_COUNT:
            raise RuntimeError("Python collectible round is incomplete")
        if not is_valid(session.gameplay.companion):
            raise RuntimeError("Python companion is missing")
        if not is_valid(pawn.Mesh.get_anim_instance()):
            raise RuntimeError("the official Blueprint animation instance is missing")

    def _write_result(self, status, game_mode, controller, pawn, error=None):
        if self.finished:
            return
        self.finished = True
        plugin = ue.find_plugin("UnrealEnginePython")
        report = {
            "schema_version": 1,
            "status": status,
            "engine_version": [
                ue.ENGINE_MAJOR_VERSION,
                ue.ENGINE_MINOR_VERSION,
                ue.ENGINE_PATCH_VERSION,
            ],
            "python_version": ".".join(
                str(value) for value in sys.version_info[:3]
            ),
            "uep_version": plugin.version_name if plugin is not None else None,
            "demo_version": DEMO_VERSION,
            "game_mode_class": (
                game_mode.get_class().get_name() if is_valid(game_mode) else None
            ),
            "controller_class": (
                controller.get_class().get_name() if is_valid(controller) else None
            ),
            "character_class": (
                pawn.get_class().get_name() if is_valid(pawn) else None
            ),
            "registration_before": self.registration_before,
            "registration_after_reregister": self.registration_after_reregister,
            "invalid_registration": {
                "rejected": self.invalid_registration_rejected,
                "preserved_active": self.invalid_registration_preserved_active,
            },
            "initial_snapshot": self.initial_snapshot,
            "pre_restore_snapshot": self.pre_restore_snapshot,
            "movement_distance": round(self.movement_distance, 3),
            "look_delta": round(self.look_delta, 3),
            "jump_height": round(self.jump_height, 3),
            "blueprint_original_move_distance": round(
                self.original_restore_distance,
                3,
            ),
            "live_reregister_move_distance": round(
                self.live_reregister_distance,
                3,
            ),
            "function_identity": {
                "injected_differs_from_restored": (
                    self.injected_move_function is not None
                    and self.restored_move_function is not None
                    and self.injected_move_function is not self.restored_move_function
                ),
                "restored_differs_from_reregistered": (
                    self.restored_move_function is not None
                    and self.re_registered_move_function is not None
                    and self.restored_move_function is not self.re_registered_move_function
                ),
            },
            "gameplay": self.gameplay_report,
            "teardown": self.teardown_report,
            "error": error,
        }
        path = Path(self.result_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        marker = (
            "UEP_MIXIN_THIRD_PERSON_SMOKE_PASSED"
            if status == "passed"
            else "UEP_MIXIN_THIRD_PERSON_SMOKE_FAILED"
        )
        (ue.log if status == "passed" else ue.log_error)(marker)

    def _finish(self, game_mode, controller, pawn):
        final_snapshot = pawn.mixin_snapshot()
        if final_snapshot["move"] <= 0:
            raise RuntimeError("re-registered mixin did not drive the live pawn")
        if self.live_reregister_distance <= 25.0:
            raise RuntimeError("live pawn did not move after mixin re-registration")
        if final_snapshot["initializations"] != 2:
            raise RuntimeError("live pawn was not initialized for the new generation")
        if final_snapshot["teardowns"] != self.first_teardown_events:
            raise RuntimeError("mixin teardown state was not retained across generations")

        unregister_all_count = ue.unregister_all_mixins()
        if unregister_all_count != 1:
            raise RuntimeError("final unregister_all_mixins count was not one")
        self.runtime.shutdown()
        self.teardown_report = {
            "unregister_all_count": unregister_all_count,
            "mixin_count": len(ue.get_registered_mixins()),
            "initialization_events": pawn.PythonMixinInitializationEvents,
            "teardown_events": pawn.PythonMixinTeardownEvents,
            "runtime_active": self.runtime.active,
            "session_released": self.runtime.session is None,
            "class_preserved": (
                pawn.get_class().get_name() == "BP_ThirdPersonCharacter_C"
            ),
            "helper_removed": not hasattr(pawn, "mixin_snapshot"),
        }
        if any(
            (
                self.teardown_report["mixin_count"] != 0,
                self.teardown_report["runtime_active"],
                not self.teardown_report["session_released"],
                not self.teardown_report["class_preserved"],
                not self.teardown_report["helper_removed"],
            )
        ):
            raise RuntimeError("mixin/runtime teardown contract failed")

        self._write_result("passed", game_mode, controller, pawn)
        request_exit()

    def tick(self, delta_seconds):
        world = game_mode = controller = pawn = None
        try:
            self.elapsed += delta_seconds
            self.phase_elapsed += delta_seconds
            self.phase_ticks += 1
            world, game_mode, controller, pawn = gameplay_objects()
            if not all(
                is_valid(value)
                for value in (world, game_mode, controller, pawn)
            ):
                if self.elapsed > 60.0:
                    raise RuntimeError("official Third Person world was not ready")
                return True

            if self.runtime.last_error:
                raise RuntimeError("runtime failed:\n" + self.runtime.last_error)

            if self.phase == "waiting":
                if self.phase_elapsed >= 0.5 and self.runtime.session is not None:
                    self._validate_initial_contract(
                        game_mode,
                        controller,
                        pawn,
                    )
                    self.start_location = pawn.get_actor_location()
                    self.phase = "moving"
                    self.phase_elapsed = 0.0
                    self.phase_ticks = 0
            elif self.phase == "moving":
                if "W" not in self.held_keys:
                    self._set_key(controller, "W", PRESSED, 1.0)
                self.movement_distance = (
                    pawn.get_actor_location() - self.start_location
                ).length()
                if self.phase_elapsed >= 0.8:
                    self._set_key(controller, "W", RELEASED, 0.0)
                    snapshot = pawn.mixin_snapshot()
                    if snapshot["move"] <= 0 or self.movement_distance <= 25.0:
                        raise RuntimeError(
                            "W did not travel through Blueprint input into Python Move"
                        )
                    self.start_rotation = pawn.get_control_rotation()
                    self.phase = "looking"
                    self.phase_elapsed = 0.0
                    self.phase_ticks = 0
            elif self.phase == "looking":
                controller.input_axis(Key(KeyName="MouseX"), 1.5, delta_seconds)
                controller.input_axis(Key(KeyName="MouseY"), 0.5, delta_seconds)
                rotation = pawn.get_control_rotation()
                self.look_delta = abs(
                    rotation.yaw - self.start_rotation.yaw
                ) + abs(rotation.pitch - self.start_rotation.pitch)
                if self.phase_elapsed >= 0.35:
                    snapshot = pawn.mixin_snapshot()
                    if snapshot["aim"] <= 0 or self.look_delta <= 0.1:
                        raise RuntimeError(
                            "mouse input did not travel through Blueprint input into Python Aim"
                        )
                    self.start_location = pawn.get_actor_location()
                    self._set_key(controller, "SpaceBar", PRESSED, 1.0)
                    self.phase = "jumping"
                    self.phase_elapsed = 0.0
                    self.phase_ticks = 0
            elif self.phase == "jumping":
                self.jump_height = max(
                    self.jump_height,
                    pawn.get_actor_location().z - self.start_location.z,
                )
                if self.phase_ticks == 6:
                    self._set_key(controller, "SpaceBar", RELEASED, 0.0)
                if self.phase_elapsed >= 1.4:
                    if self.jump_height <= 10.0:
                        raise RuntimeError(
                            "retained Blueprint/native jump logic did not execute"
                        )
                    self.pre_restore_snapshot = pawn.mixin_snapshot()
                    self.phase = "collecting"
                    self.phase_elapsed = 0.0
                    self.phase_ticks = 0
            elif self.phase == "collecting":
                session = self.runtime.session
                if session is None or session.pawn != pawn:
                    raise RuntimeError("gameplay session changed during collection")
                if session.gameplay.progress.phase == "victory":
                    self.gameplay_report = self._session_report()
                    if self.gameplay_report["companion_movement"] <= 1.0:
                        raise RuntimeError("Python companion did not move")
                    if not self.gameplay_report["hud"]["attached"]:
                        raise RuntimeError("Python HUD detached before validation")
                    if not ue.unregister_mixin(BP_THIRD_PERSON_CHARACTER):
                        raise RuntimeError("explicit mixin restoration failed")
                    if self._registered_character_mixin() is not None:
                        raise RuntimeError("mixin registry survived restoration")
                    if pawn.get_class().get_name() != "BP_ThirdPersonCharacter_C":
                        raise RuntimeError("restoration changed the pawn class")
                    if hasattr(pawn, "mixin_snapshot"):
                        raise RuntimeError("mixin helper survived restoration")
                    self.first_teardown_events = pawn.PythonMixinTeardownEvents
                    if self.first_teardown_events != 1:
                        raise RuntimeError("per-object mixin teardown hook did not run")
                    self.restored_move_function = pawn.find_function("Move")
                    if self.restored_move_function is self.injected_move_function:
                        raise RuntimeError("original Blueprint Move was not restored")
                    self.start_location = pawn.get_actor_location()
                    self._set_key(controller, "W", PRESSED, 1.0)
                    self.phase = "original_move"
                    self.phase_elapsed = 0.0
                    self.phase_ticks = 0
                else:
                    locations = session.gameplay.pickup_locations()
                    if not locations:
                        raise RuntimeError("pickup actors disappeared")
                    pawn.set_actor_location(locations[0])
                    if self.phase_elapsed >= 10.0:
                        raise RuntimeError("automated collection timed out")
            elif self.phase == "original_move":
                self.original_restore_distance = (
                    pawn.get_actor_location() - self.start_location
                ).length()
                if self.phase_elapsed >= 0.8:
                    self._set_key(controller, "W", RELEASED, 0.0)
                    if self.original_restore_distance <= 25.0:
                        raise RuntimeError(
                            "restored Blueprint Move did not drive the pawn"
                        )
                    register_character_mixin()
                    registration = self._registered_character_mixin()
                    if registration is None:
                        raise RuntimeError("live pawn mixin re-registration failed")
                    self.registration_after_reregister = {
                        "registration_id": registration["registration_id"],
                        "target_class": registration["target_class"].get_name(),
                        "functions": tuple(sorted(registration["functions"])),
                    }
                    if (
                        self.registration_after_reregister["registration_id"]
                        == self.registration_before["registration_id"]
                    ):
                        raise RuntimeError("mixin generation did not change")
                    self.re_registered_move_function = pawn.find_function("Move")
                    if self.re_registered_move_function is self.restored_move_function:
                        raise RuntimeError("live re-registration kept original Move")
                    self.start_location = pawn.get_actor_location()
                    self._set_key(controller, "W", PRESSED, 1.0)
                    self.phase = "reregistered_move"
                    self.phase_elapsed = 0.0
                    self.phase_ticks = 0
            elif self.phase == "reregistered_move":
                self.live_reregister_distance = (
                    pawn.get_actor_location() - self.start_location
                ).length()
                if self.phase_elapsed >= 0.8:
                    self._set_key(controller, "W", RELEASED, 0.0)
                    self._finish(game_mode, controller, pawn)
                    return False

            return True
        except Exception:
            details = traceback.format_exc()
            ue.log_error(details)
            self._release_keys(controller)
            try:
                ue.unregister_mixin(BP_THIRD_PERSON_CHARACTER)
            except Exception:
                pass
            self.runtime.shutdown()
            self._write_result(
                "failed",
                game_mode,
                controller,
                pawn,
                details,
            )
            request_exit()
            return False


def start_smoke_if_requested(runtime):
    result_path = _command_line_value(SMOKE_RESULT_PREFIX)
    if not result_path:
        return None, None
    smoke = MixinThirdPersonSmoke(runtime, result_path)
    return smoke, ue.add_ticker(smoke.tick)
