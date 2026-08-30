"""Automated proof for live Blueprint-class Python mixins."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine import FTransform, FVector
from unreal_engine.classes import Actor
from unreal_engine.structs import Key

from uep_third_person.constants import PICKUP_COUNT
from uep_third_person.utils import gameplay_objects, is_valid, request_exit

from . import __version__ as DEMO_VERSION
from .character_mixin import (
    BLUEPRINT_FALLBACK_PROFILE,
    BP_THIRD_PERSON_CHARACTER,
    MIXED_FUNCTIONS,
    PROFILE_FUNCTIONS,
    PYTHON_PROFILE,
    arm_reentrancy_probe,
    register_character_mixin,
    register_character_profiles_direct,
    reentrancy_probe_snapshot,
)
from .interface_probe import (
    BLUEPRINT_FALLBACK_PROFILE as INTERFACE_FALLBACK_PROFILE,
    PROBE_CHILD_CLASS_PATH,
    PROBE_CLASS_PATH,
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
        self.profile_fallback_move_distance = 0.0
        self.original_restore_distance = 0.0
        self.direct_reregister_distance = 0.0
        self.live_reregister_distance = 0.0
        self.initial_snapshot = None
        self.pre_restore_snapshot = None
        self.restored_move_function = None
        self.injected_move_function = None
        self.direct_registered_move_function = None
        self.re_registered_move_function = None
        self.registration_before = None
        self.registration_direct = None
        self.registration_after_reregister = None
        self.first_teardown_events = 0
        self.declared_initializations_before = 0
        self.declared_teardowns_before = 0
        self.invalid_registration_rejected = False
        self.invalid_registration_preserved_active = False
        self.profile_peer = None
        self.profile_peer_snapshot = None
        self.profile_router_report = None
        self.character_interface = None
        self.interface_contract = None
        self.interface_probe_owners = []
        self.interface_probe_components = []
        self.reentrancy_report = None
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

    def _registered_mixin(self, class_name):
        for registration in ue.get_registered_mixins():
            target = registration.get("target_class")
            if target is not None and target.get_name() == class_name:
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

    def _validate_interface_contract(self, world, pawn):
        interface_class = ue.find_class("UEPPythonMixinInterface")
        if interface_class is None:
            raise RuntimeError("UEPPythonMixinInterface reflection is missing")

        probe_class = ue.load_class(PROBE_CLASS_PATH)
        child_class = ue.load_class(PROBE_CHILD_CLASS_PATH)
        if probe_class is None or child_class is None:
            raise RuntimeError("asset-authored Mixin Interface probe classes are missing")

        registration = self._registered_mixin("BP_MixinInterfaceProbe_C")
        if registration is None:
            raise RuntimeError("package-load discovery did not register the Interface BP")
        if self._registered_mixin("BP_MixinInterfaceProbeChild_C") is not None:
            raise RuntimeError("inherited Interface child incorrectly owns a second router")
        mixin_set = registration.get("mixin_set")
        if mixin_set is None:
            raise RuntimeError("declared Interface router lost its Mixin Set")
        if registration.get("default_profile") != INTERFACE_FALLBACK_PROFILE:
            raise RuntimeError("Interface probe has the wrong default profile")
        profile_functions = {
            name: tuple(sorted(profile["functions"]))
            for name, profile in registration.get("profiles", {}).items()
        }
        if profile_functions != {
            "ArrayRoute": (
                "AddInstances",
                "BatchUpdateInstancesTransforms",
            ),
            "BlueprintFallback": ("SetCullDistances",),
        }:
            raise RuntimeError(
                "unexpected Interface probe profile union: "
                + repr(profile_functions)
            )

        for index, component_class in enumerate((probe_class, child_class)):
            owner = world.actor_spawn(
                Actor,
                pawn.get_actor_location() + FVector(0.0, 800.0 + index * 150.0, 0.0),
            )
            if not is_valid(owner):
                raise RuntimeError("unable to spawn an Interface probe owner")
            component = owner.add_actor_component(
                component_class,
                f"UEPMixinInterfaceProbe{index}",
            )
            if not is_valid(component):
                raise RuntimeError("unable to create an Interface probe component")
            self.interface_probe_owners.append(owner)
            self.interface_probe_components.append(component)

        fallback_results = []
        snapshots = []
        for index, component in enumerate(self.interface_probe_components):
            if ue.get_mixin_profile(component) != INTERFACE_FALLBACK_PROFILE:
                raise RuntimeError("Interface graph did not select its constant profile")
            explicit_result = component.call_mixin_original(
                "AddInstances",
                [FTransform()],
                True,
                False,
                False,
            )
            explicit_return = (
                explicit_result[0]
                if isinstance(explicit_result, tuple)
                else explicit_result
            )
            if explicit_return != [0]:
                raise RuntimeError(
                    "explicit original AddInstances call lost its native return: "
                    + repr(explicit_result)
                )
            component.ClearInstances()
            call_result = component.AddInstances(
                [FTransform()],
                True,
                False,
                False,
            )
            # UEP's public Python UFunction API retains its historical convention
            # of echoing const array refs as tuple outputs. The first element is
            # the real return value populated by the preserved native UFunction.
            return_value = call_result[0] if isinstance(call_result, tuple) else call_result
            if return_value != [0]:
                raise RuntimeError(
                    "automatic original fallback lost the AddInstances return value: "
                    + repr(call_result)
                )

            explicit_scalar_result = component.call_mixin_original(
                "BatchUpdateInstancesTransforms",
                0,
                [FTransform()],
                False,
                False,
                False,
            )
            explicit_scalar_return = (
                explicit_scalar_result[0]
                if isinstance(explicit_scalar_result, tuple)
                else explicit_scalar_result
            )
            scalar_result = component.BatchUpdateInstancesTransforms(
                0,
                [FTransform()],
                False,
                False,
                False,
            )
            scalar_return = (
                scalar_result[0]
                if isinstance(scalar_result, tuple)
                else scalar_result
            )
            if explicit_scalar_return is not True or scalar_return is not True:
                raise RuntimeError(
                    "native scalar/const-array fallback lost its bool return: "
                    + repr((explicit_scalar_result, scalar_result))
                )
            component.SetCullDistances(100 + index, 1000 + index)
            snapshot = component.interface_probe_snapshot()
            if snapshot["profile"] != INTERFACE_FALLBACK_PROFILE:
                raise RuntimeError("Interface probe initialized the wrong profile")
            if snapshot["initializations"] != 1 or snapshot["python_calls"] != 1:
                raise RuntimeError("Interface probe lifecycle/call counters are wrong")
            fallback_results.append(
                {
                    "explicit_return_value": list(explicit_return),
                    "return_value": list(return_value),
                    "tuple_arity": len(call_result)
                    if isinstance(call_result, tuple)
                    else 0,
                    "const_input_echo_count": len(call_result[1])
                    if isinstance(call_result, tuple) and len(call_result) > 1
                    else 0,
                    "scalar_fallback": {
                        "explicit_return": explicit_scalar_return,
                        "automatic_return": scalar_return,
                        "tuple_arity": len(scalar_result)
                        if isinstance(scalar_result, tuple)
                        else 0,
                        "const_input_echo_count": len(scalar_result[1])
                        if isinstance(scalar_result, tuple) and len(scalar_result) > 1
                        else 0,
                    },
                }
            )
            snapshots.append(snapshot)

        self.interface_contract = {
            "interface_class": interface_class.get_name(),
            "mixin_set_class": mixin_set.get_class().get_name(),
            "mixin_set_asset": mixin_set.get_name(),
            "default_profile": registration["default_profile"],
            "profile_count": len(registration["profiles"]),
            "declaring_class": registration["target_class"].get_name(),
            "inherited_child_class": child_class.get_name(),
            "router_owner_count": 1,
            "profile_functions": profile_functions,
            "fallback_results": fallback_results,
            "snapshots": snapshots,
        }

    def _validate_initial_contract(self, world, game_mode, controller, pawn):
        self._validate_interface_contract(world, pawn)

        self._assert_class_identity(game_mode, controller, pawn)
        registration = self._registered_character_mixin()
        if registration is None:
            raise RuntimeError("character mixin registration is missing")
        functions = tuple(sorted(registration["functions"]))
        if functions != MIXED_FUNCTIONS:
            raise RuntimeError(
                "unexpected mixed function set: " + ", ".join(functions)
            )
        profiles = registration.get("profiles", {})
        actual_profile_functions = {
            profile_name: tuple(sorted(profile["functions"]))
            for profile_name, profile in profiles.items()
        }
        expected_profile_functions = {
            profile_name: tuple(sorted(functions))
            for profile_name, functions in PROFILE_FUNCTIONS.items()
        }
        if actual_profile_functions != expected_profile_functions:
            raise RuntimeError(
                "unexpected per-profile function map: "
                + repr(actual_profile_functions)
            )
        if registration.get("default_profile") != PYTHON_PROFILE:
            raise RuntimeError("Python is not the default character profile")
        character_mixin_set = registration.get("mixin_set")
        if (
            character_mixin_set is None
            or character_mixin_set.get_name() != "DA_ThirdPersonCharacterMixin"
        ):
            raise RuntimeError("playable Character was not registered from its Mixin Set")
        character_cdo = BP_THIRD_PERSON_CHARACTER.get_cdo()
        cdo_mixin_set = character_cdo.GetPythonMixinSet()
        cdo_profile = str(character_cdo.GetPythonMixinProfile())
        if cdo_mixin_set != character_mixin_set:
            raise RuntimeError("Character CDO returned a different Mixin Set")
        if cdo_profile != PYTHON_PROFILE:
            raise RuntimeError("Character CDO profile variable is not Python")
        if str(pawn.PythonMixinProfile) != PYTHON_PROFILE:
            raise RuntimeError("spawned Character lost its Blueprint profile default")
        self.character_interface = {
            "mixin_set": character_mixin_set.get_name(),
            "profile_variable": "PythonMixinProfile",
            "cdo_profile": cdo_profile,
            "pawn_profile_property": str(pawn.PythonMixinProfile),
        }
        self.registration_before = {
            "registration_id": registration["registration_id"],
            "target_class": registration["target_class"].get_name(),
            "functions": functions,
            "default_profile": registration["default_profile"],
            "profiles": actual_profile_functions,
            "mixin_set": character_mixin_set.get_name(),
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
        if snapshot["profile"] != PYTHON_PROFILE:
            raise RuntimeError("live pawn did not select the default Python profile")
        self.initial_snapshot = snapshot
        self.injected_move_function = pawn.find_function("Move")

        peer_location = pawn.get_actor_location() + FVector(0.0, 400.0, 50.0)
        self.profile_peer = world.actor_spawn(
            BP_THIRD_PERSON_CHARACTER,
            peer_location,
            pawn.get_actor_rotation(),
        )
        if not is_valid(self.profile_peer):
            raise RuntimeError("unable to spawn the same-BP profile peer")
        self.profile_peer.PythonMixinProfile = BLUEPRINT_FALLBACK_PROFILE
        ue.clear_mixin_profile(self.profile_peer)
        if ue.get_mixin_profile(self.profile_peer) != BLUEPRINT_FALLBACK_PROFILE:
            raise RuntimeError("peer did not read its Blueprint profile variable")
        ue.set_mixin_profile(
            self.profile_peer,
            PYTHON_PROFILE,
        )
        if ue.get_mixin_profile(self.profile_peer) != PYTHON_PROFILE:
            raise RuntimeError("explicit profile did not override the Blueprint selector")
        ue.clear_mixin_profile(self.profile_peer)
        if ue.get_mixin_profile(self.profile_peer) != BLUEPRINT_FALLBACK_PROFILE:
            raise RuntimeError("clearing the peer profile did not re-read Blueprint")
        self.profile_peer.Aim(0.0, 0.0)
        self.profile_peer_snapshot = self.profile_peer.mixin_snapshot()
        if self.profile_peer.get_class() != pawn.get_class():
            raise RuntimeError("profile peer does not share the pawn Blueprint class")
        if ue.get_mixin_profile(pawn) != PYTHON_PROFILE:
            raise RuntimeError("main pawn profile changed while configuring peer")
        if ue.get_mixin_profile(self.profile_peer) != BLUEPRINT_FALLBACK_PROFILE:
            raise RuntimeError("peer did not retain its per-instance profile")
        if self.profile_peer_snapshot["profile"] != BLUEPRINT_FALLBACK_PROFILE:
            raise RuntimeError("peer helper dispatch used the wrong Python class")
        if self.profile_peer_snapshot["aim"] != 1:
            raise RuntimeError("peer UFunction did not route to its selected profile")
        self.profile_router_report = {
            "same_blueprint_class": True,
            "selection_source": "Blueprint instance variable",
            "main_profile": ue.get_mixin_profile(pawn),
            "peer_profile": ue.get_mixin_profile(self.profile_peer),
            "peer_profile_property": str(self.profile_peer.PythonMixinProfile),
            "peer_snapshot": self.profile_peer_snapshot,
        }

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
            "schema_version": 4,
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
            "registration_direct": self.registration_direct,
            "registration_after_reregister": self.registration_after_reregister,
            "invalid_registration": {
                "rejected": self.invalid_registration_rejected,
                "preserved_active": self.invalid_registration_preserved_active,
            },
            "initial_snapshot": self.initial_snapshot,
            "character_interface": self.character_interface,
            "profile_router": self.profile_router_report,
            "interface_contract": self.interface_contract,
            "reentrancy": self.reentrancy_report,
            "pre_restore_snapshot": self.pre_restore_snapshot,
            "movement_distance": round(self.movement_distance, 3),
            "profile_fallback_move_distance": round(
                self.profile_fallback_move_distance,
                3,
            ),
            "look_delta": round(self.look_delta, 3),
            "jump_height": round(self.jump_height, 3),
            "blueprint_original_move_distance": round(
                self.original_restore_distance,
                3,
            ),
            "direct_reregister_move_distance": round(
                self.direct_reregister_distance,
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
                "direct_differs_from_restored": (
                    self.direct_registered_move_function is not None
                    and self.restored_move_function is not None
                    and self.direct_registered_move_function is not self.restored_move_function
                ),
                "declared_differs_from_direct": (
                    self.re_registered_move_function is not None
                    and self.direct_registered_move_function is not None
                    and self.re_registered_move_function is not self.direct_registered_move_function
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
        if final_snapshot["initializations"] != self.declared_initializations_before + 1:
            raise RuntimeError("declared Mixin Set did not initialize the live pawn")
        if final_snapshot["teardowns"] != self.declared_teardowns_before:
            raise RuntimeError("declared re-registration lost prior lifecycle state")

        self.reentrancy_report = reentrancy_probe_snapshot()
        if self.reentrancy_report["initializer_mutations_rejected"] < 3:
            raise RuntimeError("initializer registry mutations were not rejected")
        if self.reentrancy_report["nested_peer_dispatches"] != 1:
            raise RuntimeError("nested peer initialization did not run exactly once")

        unregister_all_count = ue.unregister_all_mixins()
        if unregister_all_count != 2:
            raise RuntimeError("final unregister_all_mixins count was not two")
        self.runtime.shutdown()
        self.reentrancy_report = reentrancy_probe_snapshot()
        if self.reentrancy_report["teardown_mutations_rejected"] < 3:
            raise RuntimeError("teardown registry mutations were not rejected")
        if is_valid(self.profile_peer):
            self.profile_peer.actor_destroy()
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
            "interface_probe": {
                "teardowns": [
                    component.InterfaceProbeTeardowns
                    for component in self.interface_probe_components
                ],
                "helpers_removed": all(
                    not hasattr(component, "interface_probe_snapshot")
                    for component in self.interface_probe_components
                ),
            },
        }
        for owner in self.interface_probe_owners:
            if is_valid(owner):
                owner.actor_destroy()
        if any(
            (
                self.teardown_report["mixin_count"] != 0,
                self.teardown_report["runtime_active"],
                not self.teardown_report["session_released"],
                not self.teardown_report["class_preserved"],
                not self.teardown_report["helper_removed"],
                self.teardown_report["interface_probe"]["teardowns"] != [1, 1],
                not self.teardown_report["interface_probe"]["helpers_removed"],
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
                        world,
                        game_mode,
                        controller,
                        pawn,
                    )
                    self.start_location = pawn.get_actor_location()
                    pawn.PythonMixinProfile = BLUEPRINT_FALLBACK_PROFILE
                    ue.clear_mixin_profile(pawn)
                    self.phase = "profile_fallback_move"
                    self.phase_elapsed = 0.0
                    self.phase_ticks = 0
            elif self.phase == "profile_fallback_move":
                if "W" not in self.held_keys:
                    self._set_key(controller, "W", PRESSED, 1.0)
                self.profile_fallback_move_distance = (
                    pawn.get_actor_location() - self.start_location
                ).length()
                if self.phase_elapsed >= 0.8:
                    self._set_key(controller, "W", RELEASED, 0.0)
                    snapshot = pawn.mixin_snapshot()
                    if snapshot["profile"] != BLUEPRINT_FALLBACK_PROFILE:
                        raise RuntimeError("main pawn did not switch to fallback profile")
                    if snapshot["move"] != 0:
                        raise RuntimeError(
                            "fallback profile unexpectedly implemented Python Move"
                        )
                    if self.profile_fallback_move_distance <= 25.0:
                        raise RuntimeError(
                            "missing profile Move did not fall back to Blueprint"
                        )
                    pawn.PythonMixinProfile = PYTHON_PROFILE
                    ue.clear_mixin_profile(pawn)
                    if ue.get_mixin_profile(self.profile_peer) != (
                        BLUEPRINT_FALLBACK_PROFILE
                    ):
                        raise RuntimeError(
                            "switching the main pawn changed the peer profile"
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
                    expected_teardown_events = (
                        self.pre_restore_snapshot["teardowns"] + 1
                    )
                    if self.first_teardown_events != expected_teardown_events:
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
                    register_character_profiles_direct()
                    pawn.PythonMixinProfile = PYTHON_PROFILE
                    self.profile_peer.PythonMixinProfile = BLUEPRINT_FALLBACK_PROFILE
                    ue.clear_mixin_profile(pawn)
                    ue.clear_mixin_profile(self.profile_peer)
                    arm_reentrancy_probe(self.profile_peer)
                    registration = self._registered_character_mixin()
                    if registration is None:
                        raise RuntimeError("direct profile registration failed")
                    if registration.get("mixin_set") is not None:
                        raise RuntimeError("direct registration unexpectedly retained a Mixin Set")
                    self.registration_direct = {
                        "registration_id": registration["registration_id"],
                        "target_class": registration["target_class"].get_name(),
                        "functions": tuple(sorted(registration["functions"])),
                        "default_profile": registration["default_profile"],
                        "profiles": tuple(sorted(registration["profiles"])),
                        "mixin_set": None,
                    }
                    if (
                        self.registration_direct["registration_id"]
                        == self.registration_before["registration_id"]
                    ):
                        raise RuntimeError("direct router generation did not change")
                    self.direct_registered_move_function = pawn.find_function("Move")
                    if self.direct_registered_move_function is self.restored_move_function:
                        raise RuntimeError("direct registration kept original Move")
                    self.start_location = pawn.get_actor_location()
                    self._set_key(controller, "W", PRESSED, 1.0)
                    self.phase = "direct_reregistered_move"
                    self.phase_elapsed = 0.0
                    self.phase_ticks = 0
            elif self.phase == "direct_reregistered_move":
                self.direct_reregister_distance = (
                    pawn.get_actor_location() - self.start_location
                ).length()
                if self.phase_elapsed >= 0.8:
                    self._set_key(controller, "W", RELEASED, 0.0)
                    snapshot = pawn.mixin_snapshot()
                    if snapshot["move"] <= 0 or self.direct_reregister_distance <= 25.0:
                        raise RuntimeError("direct Python API did not drive the live pawn")
                    if not ue.unregister_mixin(BP_THIRD_PERSON_CHARACTER):
                        raise RuntimeError("unable to restore after direct API regression")
                    if pawn.find_function("Move") is not self.restored_move_function:
                        raise RuntimeError("direct API unregister did not restore original Move")

                    self.declared_initializations_before = (
                        pawn.PythonMixinInitializationEvents
                    )
                    self.declared_teardowns_before = pawn.PythonMixinTeardownEvents
                    register_character_mixin()
                    registration = self._registered_character_mixin()
                    mixin_set = registration.get("mixin_set") if registration else None
                    if (
                        registration is None
                        or mixin_set is None
                        or mixin_set.get_name() != "DA_ThirdPersonCharacterMixin"
                    ):
                        raise RuntimeError("declared Character Mixin Set re-registration failed")
                    self.registration_after_reregister = {
                        "registration_id": registration["registration_id"],
                        "target_class": registration["target_class"].get_name(),
                        "functions": tuple(sorted(registration["functions"])),
                        "default_profile": registration["default_profile"],
                        "profiles": tuple(sorted(registration["profiles"])),
                        "mixin_set": mixin_set.get_name(),
                    }
                    if self.registration_after_reregister["registration_id"] in (
                        self.registration_before["registration_id"],
                        self.registration_direct["registration_id"],
                    ):
                        raise RuntimeError("declared router generation did not change")
                    pawn.PythonMixinProfile = PYTHON_PROFILE
                    self.profile_peer.PythonMixinProfile = BLUEPRINT_FALLBACK_PROFILE
                    ue.clear_mixin_profile(pawn)
                    ue.clear_mixin_profile(self.profile_peer)
                    self.re_registered_move_function = pawn.find_function("Move")
                    if self.re_registered_move_function is self.restored_move_function:
                        raise RuntimeError("declared re-registration kept original Move")
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
                ue.unregister_all_mixins()
            except Exception:
                pass
            if is_valid(self.profile_peer):
                self.profile_peer.actor_destroy()
            for owner in self.interface_probe_owners:
                if is_valid(owner):
                    owner.actor_destroy()
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
