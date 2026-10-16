"""Lyra lifecycle and authority-only gameplay probe for automated runs."""

import json
import math
import os
from pathlib import Path
import re
import sys
import time
import traceback

import unreal_engine as ue

from uep_lyra_hud import state as hud_state


GAME_WORLD_TYPES = (1, 3, 5)  # Game, PIE, GamePreview
RESULT_PREFIX = "-UEPLyraSmokeResult="
MODE_PREFIX = "-UEPLyraMode="
REQUIRE_EXPERIENCE = "-UEPLyraRequireExperience"
TIMEOUT_PREFIX = "-UEPLyraTimeoutSeconds="
EXPECTED_CONTROLLERS_PREFIX = "-UEPLyraExpectedPlayerControllers="
REQUIRED_FEATURES_PREFIX = "-UEPLyraRequiredFeatures="
REQUIRED_REGISTERED_FEATURES_PREFIX = "-UEPLyraRequiredRegisteredFeatures="
EXPECTED_EXPERIENCE_PREFIX = "-UEPLyraExpectedExperienceContains="
HOLD_READY_PREFIX = "-UEPLyraHoldReadySeconds="
READY_RELEASE_PREFIX = "-UEPLyraReadyReleaseFile="
GAMEPLAY_SLICE = "-UEPLyraGameplaySlice"
GAMEPLAY_SYNC_DIR_PREFIX = "-UEPLyraGameplaySyncDir="
GAMEPLAY_DAMAGE_PREFIX = "-UEPLyraGameplayDamage="
HUD_SLICE = "-UEPLyraHUDSlice"
HUD_TRAVEL_URL_PREFIX = "-UEPLyraHUDTravelURL="


def _command_line_value(prefix, default=None):
    for argument in sys.argv:
        if argument.startswith(prefix):
            return argument[len(prefix):].strip('"')
    return default


def _has_argument(name):
    return any(argument.lower() == name.lower() for argument in sys.argv)


def _command_line_float(prefix, default):
    value = _command_line_value(prefix)
    try:
        return float(value) if value is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


def _command_line_int(prefix, default):
    value = _command_line_value(prefix)
    try:
        return int(value) if value is not None else int(default)
    except (TypeError, ValueError):
        return int(default)


def _command_line_list(prefix):
    value = _command_line_value(prefix, "")
    return [item.strip() for item in re.split(r"[,+;]", value) if item.strip()]


def _is_valid(obj):
    try:
        return obj is not None and obj.is_valid()
    except Exception:
        return False


def _field(value, name, default=None):
    try:
        return getattr(value, name)
    except Exception:
        return default


class LyraRuntimeProbe:
    def __init__(self):
        self.elapsed = 0.0
        self.started_at = time.monotonic()
        self.world_ticks = 0
        self.result_path = _command_line_value(RESULT_PREFIX)
        self.mode = _command_line_value(MODE_PREFIX, "source")
        self.require_experience = _has_argument(REQUIRE_EXPERIENCE)
        self.timeout_seconds = max(10.0, _command_line_float(TIMEOUT_PREFIX, 180.0))
        self.expected_player_controllers = max(0, _command_line_int(EXPECTED_CONTROLLERS_PREFIX, 1))
        self.required_features = _command_line_list(REQUIRED_FEATURES_PREFIX)
        self.required_registered_features = _command_line_list(
            REQUIRED_REGISTERED_FEATURES_PREFIX
        )
        self.expected_experience = _command_line_value(EXPECTED_EXPERIENCE_PREFIX, "")
        self.hold_ready_seconds = max(0.0, _command_line_float(HOLD_READY_PREFIX, 0.0))
        self.ready_release_path = _command_line_value(READY_RELEASE_PREFIX)
        self.gameplay_slice_enabled = _has_argument(GAMEPLAY_SLICE)
        self.gameplay_sync_path = _command_line_value(GAMEPLAY_SYNC_DIR_PREFIX)
        self.gameplay_damage = _command_line_float(GAMEPLAY_DAMAGE_PREFIX, 10.0)
        self.hud_slice_enabled = _has_argument(HUD_SLICE)
        self.gameplay = {
            "enabled": self.gameplay_slice_enabled,
            "completed": not self.gameplay_slice_enabled,
            "state": "waiting_readiness" if self.gameplay_slice_enabled else "disabled",
            "damage_amount": self.gameplay_damage,
            "baseline_health": None,
            "expected_damaged_health": None,
            "observed_damaged_health": None,
            "restored_health": None,
            "client_authority_rejection": None,
            "damage_command": None,
            "duplicate_command": None,
            "heal_command": None,
            "events": [],
        }
        self.ready_since = None
        self.ready_announced = False
        self.ready_snapshot_report = None
        self.bridge_class = ue.find_class("UEPLyraWorldSubsystem")
        self.library = ue.find_class("UEPLyraBridgeLibrary").get_cdo()
        self.world = None
        self.bridge = None
        self.bridge_generation = 0
        self.bound_callback = None
        self.experience_events = 0
        self.last_snapshot_report = None
        self.last_pending = None
        self.last_pending_log_at = -30.0
        self.finished = False
        self.hud_travel_url = _command_line_value(HUD_TRAVEL_URL_PREFIX, "")
        self.hud_lifecycle = {
            "enabled": self.hud_slice_enabled,
            "completed": not self.hud_slice_enabled,
            "state": "waiting_readiness" if self.hud_slice_enabled else "disabled",
            "respawn": {
                "requested": False,
                "observed": False,
                "old_pawn": None,
                "new_pawn": None,
                "before": None,
                "after": None,
            },
            "game_feature": {
                "name": "LAS_ShooterGame_StandardHUD:AddWidgets",
                "asset": "/ShooterCore/Experiences/LAS_ShooterGame_StandardHUD",
                "mechanism": "experience_action_travel_cycle",
                "deactivation_requested": False,
                "deactivated": False,
                "reactivation_requested": False,
                "reactivated": False,
                "bridge_generation_before": None,
                "bridge_generation_after": None,
                "before": None,
                "after_cycle": None,
                "client_evidence": None,
            },
            "travel": {
                "url": self.hud_travel_url,
                "requested": False,
                "observed": False,
                "bridge_generation_before": None,
                "bridge_generation_after": None,
                "before": None,
                "after": None,
            },
        }

    def _wall_elapsed(self):
        return time.monotonic() - self.started_at

    def _timed_out(self):
        return max(self.elapsed, self._wall_elapsed()) > self.timeout_seconds

    def _game_world(self):
        for world in ue.all_worlds():
            try:
                if world.get_world_type() in GAME_WORLD_TYPES:
                    return world
            except Exception:
                continue
        return None

    def _attach(self, world):
        bridge = self.library.call_function("GetBridgeForWorld", world)
        if not _is_valid(bridge):
            return False
        if _is_valid(self.bridge) and self.bridge == bridge:
            return True
        self.shutdown_binding()
        self.world = world
        self.bridge = bridge
        self.bridge_generation += 1
        self.bound_callback = self._on_experience_ready
        bridge.bind_event("OnExperienceReady", self.bound_callback)
        ue.log("UEP_LYRA_BRIDGE_ATTACHED")
        return True

    def _on_experience_ready(self, experience):
        self.experience_events += 1
        ue.log("UEP_LYRA_EXPERIENCE_READY")

    def shutdown_binding(self):
        if _is_valid(self.bridge) and self.bound_callback is not None:
            try:
                self.bridge.unbind_event("OnExperienceReady", self.bound_callback)
            except Exception:
                ue.log_error(traceback.format_exc())
        self.bound_callback = None
        self.bridge = None

    def _feature_states(self, snapshot):
        states = []
        for item in _field(snapshot, "GameFeatures", []) or []:
            states.append(
                {
                    "name": _field(item, "Name", ""),
                    "state": _field(item, "State", ""),
                    "active": bool(_field(item, "bActive", False)),
                }
            )
        return states

    def _snapshot_report(self, snapshot):
        current_experience = _field(snapshot, "CurrentExperience")
        return {
            "game_thread": bool(_field(snapshot, "bIsGameThread", False)),
            "game_world": bool(_field(snapshot, "bIsGameWorld", False)),
            "world": _field(snapshot, "WorldName", ""),
            "net_mode": _field(snapshot, "NetMode", ""),
            "server_authority": bool(_field(snapshot, "bHasServerAuthority", False)),
            "player_controller_count": int(_field(snapshot, "PlayerControllerCount", 0)),
            "local_player_controller_count": int(_field(snapshot, "LocalPlayerControllerCount", 0)),
            "remote_player_controller_count": int(_field(snapshot, "RemotePlayerControllerCount", 0)),
            "player_state_count": int(_field(snapshot, "PlayerStateCount", 0)),
            "experience_manager": bool(_field(snapshot, "bHasExperienceManager", False)),
            "experience_loaded": bool(_field(snapshot, "bExperienceLoaded", False)),
            "experience": current_experience.get_path_name() if _is_valid(current_experience) else None,
            "player_pawn": bool(_field(snapshot, "bHasPlayerPawn", False)),
            "pawn_locally_controlled": bool(_field(snapshot, "bPawnLocallyControlled", False)),
            "player_state_ready": bool(_field(snapshot, "bPlayerStateReady", False)),
            "pawn_local_role": _field(snapshot, "PawnLocalRole", ""),
            "pawn_remote_role": _field(snapshot, "PawnRemoteRole", ""),
            "hero_input_ready": bool(_field(snapshot, "bHeroInputReady", False)),
            "ability_system_ready": bool(_field(snapshot, "bAbilitySystemReady", False)),
            "health_ready": bool(_field(snapshot, "bHealthReady", False)),
            "damage_immune": bool(_field(snapshot, "bDamageImmune", False)),
            "health": float(_field(snapshot, "Health", 0.0)),
            "max_health": float(_field(snapshot, "MaxHealth", 0.0)),
            "game_features": self._feature_states(snapshot),
        }

    @staticmethod
    def _nearly_equal(left, right, tolerance=0.05):
        return abs(float(left) - float(right)) <= tolerance

    @staticmethod
    def _command_result_report(result):
        return {
            "command_id": _field(result, "CommandId", ""),
            "status": _field(result, "Status", ""),
            "accepted": bool(_field(result, "bAccepted", False)),
            "applied": bool(_field(result, "bApplied", False)),
            "server_authority": bool(_field(result, "bServerAuthority", False)),
            "target_actor": _field(result, "TargetActor", ""),
            "requested_health_delta": float(
                _field(result, "RequestedHealthDelta", 0.0)
            ),
            "health_before": float(_field(result, "HealthBefore", 0.0)),
            "health_after": float(_field(result, "HealthAfter", 0.0)),
            "max_health": float(_field(result, "MaxHealth", 0.0)),
        }

    def _apply_health_delta(self, command_id, health_delta, target_remote_player):
        result = self.bridge.call_function(
            "ApplyAuthorityHealthDelta",
            command_id,
            float(health_delta),
            bool(target_remote_player),
        )
        return self._command_result_report(result)

    @staticmethod
    def _assert_command(command, expected_status, expected_applied):
        if command["status"] != expected_status:
            raise RuntimeError(
                "gameplay command {0} returned {1}, expected {2}".format(
                    command["command_id"], command["status"], expected_status
                )
            )
        if command["applied"] != expected_applied:
            raise RuntimeError(
                "gameplay command {0} applied={1}, expected {2}".format(
                    command["command_id"], command["applied"], expected_applied
                )
            )

    def _sync_file(self, name):
        if not self.gameplay_sync_path:
            raise RuntimeError("network gameplay slice requires -UEPLyraGameplaySyncDir")
        return Path(self.gameplay_sync_path) / name

    def _write_sync(self, name, payload):
        path = self._sync_file(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(".{0}.{1}.tmp".format(path.name, self.mode))
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(str(temporary), str(path))

    def _read_sync(self, name):
        path = self._sync_file(name)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _record_gameplay_event(self, name, health=None):
        event = {"name": name, "world_tick": self.world_ticks}
        if health is not None:
            event["health"] = float(health)
        self.gameplay["events"].append(event)

    def _hud_snapshot(self):
        return hud_state.snapshot()

    def _hud_event_seen(self, expected_health):
        for event in self._hud_snapshot()["health_events"]:
            if (
                event["event"] == "health_changed"
                and self._nearly_equal(event["health"], expected_health)
            ):
                return True
        return False

    @staticmethod
    def _object_path(value):
        if not _is_valid(value):
            return None
        return value.get_path_name()

    @staticmethod
    def _hud_counts(hud):
        return {
            "active_widget_count": hud["active_widget_count"],
            "construct_count": hud["construct_count"],
            "destruct_count": hud["destruct_count"],
            "controller_bind_count": hud["controller_bind_count"],
            "controller_unbind_count": hud["controller_unbind_count"],
            "health_bind_count": hud["health_bind_count"],
            "health_unbind_count": hud["health_unbind_count"],
            "visual_update_count": hud["visual_update_count"],
        }

    @staticmethod
    def _hud_bindings_balanced(hud):
        active = hud["active_widget_count"]
        return (
            hud["controller_bind_count"] - hud["controller_unbind_count"] == active
            and hud["health_bind_count"] - hud["health_unbind_count"] == active
        )

    @staticmethod
    def _feature_state(report, feature_name):
        for feature in report["game_features"]:
            if feature["name"].lower() == feature_name.lower():
                return feature
        return None

    def _controller_and_pawn(self):
        try:
            controller = self.world.get_player_controller()
            pawn = controller.get_controlled_pawn()
            return controller, pawn
        except Exception:
            return None, None

    def _prepare_travel_baseline(self):
        travel = self.hud_lifecycle["travel"]
        if travel["bridge_generation_before"] is not None:
            return
        travel["bridge_generation_before"] = self.bridge_generation
        travel["before"] = self._hud_counts(self._hud_snapshot())

    def _prepare_game_feature_baseline(self):
        feature_cycle = self.hud_lifecycle["game_feature"]
        if feature_cycle["bridge_generation_before"] is not None:
            return
        feature_cycle["bridge_generation_before"] = self.bridge_generation
        feature_cycle["before"] = self._hud_counts(self._hud_snapshot())

    def _complete_hud_lifecycle(self, state_name="completed"):
        if self.hud_lifecycle["completed"]:
            return
        self.hud_lifecycle["state"] = state_name
        self.hud_lifecycle["completed"] = True
        ue.log("UEP_LYRA_HUD_LIFECYCLE_PROBE_PASSED")

    def _advance_hud_lifecycle_probe(self, report):
        if not self.hud_slice_enabled:
            return True
        if self.mode == "server_exit":
            self._complete_hud_lifecycle("completed_server_zero_ui")
            return True

        lifecycle = self.hud_lifecycle
        respawn = lifecycle["respawn"]
        feature_cycle = lifecycle["game_feature"]
        travel = lifecycle["travel"]
        state_name = lifecycle["state"]

        if state_name == "waiting_readiness":
            controller, pawn = self._controller_and_pawn()
            if not _is_valid(controller) or not _is_valid(pawn):
                return False
            respawn["old_pawn"] = self._object_path(pawn)
            respawn["before"] = self._hud_counts(self._hud_snapshot())
            if self.mode == "client":
                lifecycle["state"] = "waiting_server_respawn_request"
                return False

            game_mode = self.world.get_auth_game_mode()
            if not report["server_authority"] or not _is_valid(game_mode):
                return False
            game_mode.call_function("RequestPlayerRestartNextFrame", controller, True)
            respawn["requested"] = True
            lifecycle["state"] = "waiting_respawn_observation"
            if self.mode == "server":
                self._write_sync(
                    "server-hud-respawn-requested.json",
                    {"old_pawn": respawn["old_pawn"]},
                )
            ue.log("UEP_LYRA_HUD_RESPAWN_REQUESTED " + self.mode)
            return False

        if state_name == "waiting_server_respawn_request":
            if self._read_sync("server-hud-respawn-requested.json") is None:
                return False
            respawn["requested"] = True
            lifecycle["state"] = "waiting_respawn_observation"
            return False

        if state_name == "waiting_respawn_observation":
            controller, pawn = self._controller_and_pawn()
            new_pawn = self._object_path(pawn)
            if (
                not _is_valid(controller)
                or not _is_valid(pawn)
                or new_pawn == respawn["old_pawn"]
                or not report["health_ready"]
                or report["health"] <= 0.0
            ):
                return False
            current = self._hud_snapshot()
            if self.mode not in ("server", "server_exit"):
                if (
                    current["active_widget_count"] != 1
                    or current["health_bind_count"]
                    <= respawn["before"]["health_bind_count"]
                    or not self._hud_bindings_balanced(current)
                ):
                    return False
            respawn["new_pawn"] = new_pawn
            respawn["after"] = self._hud_counts(current)
            respawn["observed"] = True
            ue.log("UEP_LYRA_HUD_RESPAWN_PASSED " + self.mode)
            if self.mode == "server":
                self._write_sync(
                    "server-hud-respawned.json",
                    {"new_pawn": new_pawn, "health": report["health"]},
                )
                lifecycle["state"] = "waiting_client_respawn"
            elif self.mode == "client":
                self._write_sync(
                    "client-hud-respawn-observed.json",
                    {"new_pawn": new_pawn, "health": report["health"]},
                )
                self._prepare_game_feature_baseline()
                lifecycle["state"] = "waiting_server_game_feature_travel_request"
            else:
                self._prepare_game_feature_baseline()
                lifecycle["state"] = "start_game_feature_travel"
            return False

        if state_name == "waiting_client_respawn":
            client_respawn = self._read_sync("client-hud-respawn-observed.json")
            if client_respawn is None:
                return False
            respawn["client_evidence"] = client_respawn
            self._prepare_game_feature_baseline()
            lifecycle["state"] = "start_game_feature_travel"
            return False

        if state_name == "start_game_feature_travel":
            if not self.hud_travel_url:
                raise RuntimeError("HUD lifecycle requires -UEPLyraHUDTravelURL")
            self._prepare_game_feature_baseline()
            if self.mode == "server":
                self._write_sync(
                    "server-hud-game-feature-travel-requested.json",
                    {"url": self.hud_travel_url},
                )
            if not self.world.server_travel(self.hud_travel_url):
                raise RuntimeError("UE rejected the HUD Game Feature action travel")
            feature_cycle["deactivation_requested"] = True
            feature_cycle["reactivation_requested"] = True
            lifecycle["state"] = "waiting_game_feature_travel_observation"
            ue.log("UEP_LYRA_HUD_GAME_FEATURE_ACTION_CYCLE_REQUESTED " + self.mode)
            return False

        if state_name == "waiting_server_game_feature_travel_request":
            request = self._read_sync("server-hud-game-feature-travel-requested.json")
            if request is None:
                return False
            if request.get("url") != self.hud_travel_url:
                raise RuntimeError("server/client Game Feature action travel URLs do not match")
            feature_cycle["deactivation_requested"] = True
            feature_cycle["reactivation_requested"] = True
            lifecycle["state"] = "waiting_game_feature_travel_observation"
            return False

        if state_name == "waiting_game_feature_travel_observation":
            if self.bridge_generation <= feature_cycle["bridge_generation_before"]:
                return False
            feature = self._feature_state(report, "ShooterCore")
            current = self._hud_snapshot()
            if (
                feature is None
                or not feature["active"]
                or not report["health_ready"]
                or not report["player_pawn"]
            ):
                return False
            if self.mode in ("server", "server_exit"):
                if (
                    current["active_widget_count"] != 0
                    or current["construct_count"] != 0
                    or current["controller_bind_count"] != 0
                    or current["health_bind_count"] != 0
                ):
                    raise RuntimeError(
                        "dedicated server created HUD state during the Game Feature action cycle"
                    )
            elif (
                current["active_widget_count"] < 1
                or current["construct_count"]
                <= feature_cycle["before"]["construct_count"]
                or current["destruct_count"]
                <= feature_cycle["before"]["destruct_count"]
                or current["visual_update_count"]
                <= feature_cycle["before"]["visual_update_count"]
                or not self._hud_bindings_balanced(current)
            ):
                return False
            feature_cycle["bridge_generation_after"] = self.bridge_generation
            feature_cycle["after_cycle"] = self._hud_counts(current)
            feature_cycle["deactivated"] = True
            feature_cycle["reactivated"] = True
            ue.log("UEP_LYRA_HUD_GAME_FEATURE_CYCLE_PASSED " + self.mode)
            if self.mode == "server":
                self._write_sync(
                    "server-hud-game-feature-cycle.json",
                    {
                        "deactivated": True,
                        "reactivated": True,
                        "bridge_generation": self.bridge_generation,
                    },
                )
                lifecycle["state"] = "waiting_client_feature_cycle"
            elif self.mode == "client":
                self._write_sync(
                    "client-hud-game-feature-cycle.json",
                    {
                        "deactivated": True,
                        "reactivated": True,
                        "bridge_generation": self.bridge_generation,
                        "after_cycle": feature_cycle["after_cycle"],
                    },
                )
                self._prepare_travel_baseline()
                lifecycle["state"] = "waiting_server_travel_request"
            else:
                self._prepare_travel_baseline()
                lifecycle["state"] = "start_travel"
            return False

        if state_name == "waiting_client_feature_cycle":
            client_cycle = self._read_sync("client-hud-game-feature-cycle.json")
            if client_cycle is None:
                return False
            if not client_cycle.get("deactivated") or not client_cycle.get("reactivated"):
                raise RuntimeError("client did not complete the HUD Game Feature cycle")
            feature_cycle["deactivated"] = True
            feature_cycle["reactivated"] = True
            feature_cycle["client_evidence"] = client_cycle
            self._prepare_travel_baseline()
            lifecycle["state"] = "start_travel"
            return False

        if state_name == "start_travel":
            if not self.hud_travel_url:
                raise RuntimeError("HUD lifecycle requires -UEPLyraHUDTravelURL")
            self._prepare_travel_baseline()
            if self.mode == "server":
                self._write_sync(
                    "server-hud-travel-requested.json",
                    {"url": self.hud_travel_url},
                )
            if not self.world.server_travel(self.hud_travel_url):
                raise RuntimeError("UE rejected the HUD lifecycle server travel")
            travel["requested"] = True
            lifecycle["state"] = "waiting_travel_observation"
            ue.log("UEP_LYRA_HUD_TRAVEL_REQUESTED " + self.mode)
            return False

        if state_name == "waiting_server_travel_request":
            request = self._read_sync("server-hud-travel-requested.json")
            if request is None:
                return False
            if request.get("url") != self.hud_travel_url:
                raise RuntimeError("server/client HUD travel URLs do not match")
            travel["requested"] = True
            lifecycle["state"] = "waiting_travel_observation"
            return False

        if state_name == "waiting_travel_observation":
            if self.bridge_generation <= travel["bridge_generation_before"]:
                return False
            feature = self._feature_state(report, "ShooterCore")
            current = self._hud_snapshot()
            if (
                feature is None
                or not feature["active"]
                or not report["health_ready"]
                or not report["player_pawn"]
            ):
                return False
            if self.mode in ("server", "server_exit"):
                if (
                    current["active_widget_count"] != 0
                    or current["construct_count"] != 0
                    or current["controller_bind_count"] != 0
                    or current["health_bind_count"] != 0
                ):
                    raise RuntimeError("dedicated server created HUD state during travel")
            elif (
                current["active_widget_count"] < 1
                or current["construct_count"] <= travel["before"]["construct_count"]
                or current["destruct_count"] <= travel["before"]["destruct_count"]
                or not self._hud_bindings_balanced(current)
            ):
                return False
            travel["bridge_generation_after"] = self.bridge_generation
            travel["after"] = self._hud_counts(current)
            travel["observed"] = True
            ue.log("UEP_LYRA_HUD_TRAVEL_PASSED " + self.mode)
            if self.mode == "server":
                self._write_sync(
                    "server-hud-travel-observed.json",
                    {"bridge_generation": self.bridge_generation},
                )
                lifecycle["state"] = "waiting_client_travel"
            elif self.mode == "client":
                self._write_sync(
                    "client-hud-travel-observed.json",
                    {"bridge_generation": self.bridge_generation},
                )
                self._complete_hud_lifecycle()
            else:
                self._complete_hud_lifecycle()
            return lifecycle["completed"]

        if state_name == "waiting_client_travel":
            client_travel = self._read_sync("client-hud-travel-observed.json")
            if client_travel is None:
                return False
            travel["client_evidence"] = client_travel
            self._complete_hud_lifecycle("completed_server_zero_ui")
            return True

        return lifecycle["completed"]

    def _assert_hud_contract(self, report):
        if not self.hud_slice_enabled:
            return
        hud = self._hud_snapshot()
        if hud["errors"]:
            raise RuntimeError("Python HUD presenter recorded errors")
        if not hud["registered"] or not hud["source_asset_available"]:
            raise RuntimeError("Python HUD Mixin Set was not registered")
        if not self.hud_lifecycle["completed"]:
            raise RuntimeError("Python HUD lifecycle probe did not complete")
        if (
            not self.hud_lifecycle["respawn"]["requested"]
            or not self.hud_lifecycle["respawn"]["observed"]
            or not self.hud_lifecycle["game_feature"]["deactivated"]
            or not self.hud_lifecycle["game_feature"]["reactivated"]
            or self.hud_lifecycle["game_feature"]["bridge_generation_after"]
            <= self.hud_lifecycle["game_feature"]["bridge_generation_before"]
            or not self.hud_lifecycle["travel"]["requested"]
            or not self.hud_lifecycle["travel"]["observed"]
        ):
            raise RuntimeError("Python HUD extended lifecycle evidence is incomplete")

        if self.mode in ("server", "server_exit"):
            if (
                hud["active_widget_count"] != 0
                or hud["construct_count"] != 0
                or hud["controller_bind_count"] != 0
                or hud["health_bind_count"] != 0
                or hud["health_events"]
            ):
                raise RuntimeError("dedicated server created Python HUD state")
            return

        if (
            hud["active_widget_count"] != 1
            or hud["live_widget_reference_count"] != 1
            or hud["construct_count"] < 3
            or hud["destruct_count"] < 2
            or hud["controller_bind_count"] - hud["controller_unbind_count"]
            != hud["active_widget_count"]
            or hud["health_bind_count"] - hud["health_unbind_count"]
            != hud["active_widget_count"]
        ):
            raise RuntimeError("Python HUD lifecycle/delegate balance is inconsistent")
        if not any(
            self._nearly_equal(event["health"], report["health"])
            for event in hud["health_events"]
        ):
            raise RuntimeError("Python HUD did not render the final health value")
        if self.gameplay_slice_enabled:
            if not self._hud_event_seen(self.gameplay["expected_damaged_health"]):
                raise RuntimeError("Python HUD did not observe the damaged health event")
            if not self._hud_event_seen(self.gameplay["baseline_health"]):
                raise RuntimeError("Python HUD did not observe the restored health event")

    def _complete_gameplay_slice(self, restored_health):
        self.gameplay["restored_health"] = float(restored_health)
        self.gameplay["state"] = "completed"
        self.gameplay["completed"] = True
        self._record_gameplay_event("completed", restored_health)
        ue.log("UEP_LYRA_GAMEPLAY_SLICE_COMPLETE {0}".format(self.mode))

    def _advance_local_gameplay_slice(self, report):
        state = self.gameplay["state"]
        if state == "waiting_readiness":
            baseline = report["health"]
            damage_delta = -self.gameplay_damage
            damage = self._apply_health_delta("uep05.local.damage", damage_delta, False)
            self._assert_command(damage, "Applied", True)
            duplicate = self._apply_health_delta("uep05.local.damage", damage_delta, False)
            self._assert_command(duplicate, "RejectedDuplicateCommand", False)
            expected = baseline + damage_delta
            if not self._nearly_equal(damage["health_before"], baseline):
                raise RuntimeError("local damage baseline did not match the observed snapshot")
            if not self._nearly_equal(damage["health_after"], expected):
                raise RuntimeError("local damage did not produce the requested health delta")
            self.gameplay["baseline_health"] = baseline
            self.gameplay["expected_damaged_health"] = expected
            self.gameplay["damage_command"] = damage
            self.gameplay["duplicate_command"] = duplicate
            self.gameplay["state"] = "waiting_damage_observation"
            self._record_gameplay_event("damage_applied", damage["health_after"])
            return False

        if state == "waiting_damage_observation":
            expected = self.gameplay["expected_damaged_health"]
            if not self._nearly_equal(report["health"], expected):
                return False
            if self.hud_slice_enabled and not self._hud_event_seen(expected):
                return False
            self.gameplay["observed_damaged_health"] = report["health"]
            self._record_gameplay_event("damage_observed", report["health"])
            heal = self._apply_health_delta("uep05.local.heal", self.gameplay_damage, False)
            self._assert_command(heal, "Applied", True)
            if not self._nearly_equal(heal["health_after"], self.gameplay["baseline_health"]):
                raise RuntimeError("local heal did not restore the baseline health")
            self.gameplay["heal_command"] = heal
            self.gameplay["state"] = "waiting_restore_observation"
            self._record_gameplay_event("heal_applied", heal["health_after"])
            return False

        if state == "waiting_restore_observation":
            if not self._nearly_equal(report["health"], self.gameplay["baseline_health"]):
                return False
            if self.hud_slice_enabled and not self._hud_event_seen(
                self.gameplay["baseline_health"]
            ):
                return False
            self._complete_gameplay_slice(report["health"])
            return True

        return state == "completed"

    def _advance_client_gameplay_slice(self, report):
        state = self.gameplay["state"]
        if state == "waiting_readiness":
            baseline = report["health"]
            rejection = self._apply_health_delta(
                "uep05.client.must_reject", -self.gameplay_damage, False
            )
            self._assert_command(rejection, "RejectedNotAuthority", False)
            immediate = self._snapshot_report(self.bridge.call_function("CaptureSnapshot"))
            if not self._nearly_equal(immediate["health"], baseline):
                raise RuntimeError("client authority rejection changed local health")
            self.gameplay["baseline_health"] = baseline
            self.gameplay["client_authority_rejection"] = rejection
            self.gameplay["state"] = "waiting_server_damage"
            self._record_gameplay_event("client_authority_rejected", baseline)
            self._write_sync(
                "client-denied.json",
                {
                    "mode": self.mode,
                    "baseline_health": baseline,
                    "command": rejection,
                },
            )
            return False

        if state == "waiting_server_damage":
            damaged = self._read_sync("server-damaged.json")
            if damaged is None:
                return False
            damage_command = damaged.get("damage_command") or {}
            duplicate_command = damaged.get("duplicate_command") or {}
            if damage_command.get("status") != "Applied" or not damage_command.get("applied"):
                raise RuntimeError("server damage evidence was not an applied command")
            if duplicate_command.get("status") != "RejectedDuplicateCommand":
                raise RuntimeError("server duplicate command was not rejected")
            expected = float(damaged["expected_damaged_health"])
            self.gameplay["expected_damaged_health"] = expected
            self.gameplay["damage_command"] = damage_command
            self.gameplay["duplicate_command"] = duplicate_command
            if not self._nearly_equal(report["health"], expected):
                return False
            if self.hud_slice_enabled and not self._hud_event_seen(expected):
                return False
            self.gameplay["observed_damaged_health"] = report["health"]
            self.gameplay["state"] = "waiting_server_restore"
            self._record_gameplay_event("replicated_damage_observed", report["health"])
            self._write_sync(
                "client-damage-observed.json",
                {"mode": self.mode, "observed_health": report["health"]},
            )
            return False

        if state == "waiting_server_restore":
            restored = self._read_sync("server-restored.json")
            if restored is None:
                return False
            heal_command = restored.get("heal_command") or {}
            if heal_command.get("status") != "Applied" or not heal_command.get("applied"):
                raise RuntimeError("server heal evidence was not an applied command")
            expected = float(restored["restored_health"])
            self.gameplay["heal_command"] = heal_command
            if not self._nearly_equal(report["health"], expected):
                return False
            if self.hud_slice_enabled and not self._hud_event_seen(expected):
                return False
            self._record_gameplay_event("replicated_restore_observed", report["health"])
            self._write_sync(
                "client-restore-observed.json",
                {"mode": self.mode, "observed_health": report["health"]},
            )
            self._complete_gameplay_slice(report["health"])
            return True

        return state == "completed"

    def _advance_server_gameplay_slice(self, report):
        state = self.gameplay["state"]
        if state == "waiting_readiness":
            self.gameplay["baseline_health"] = report["health"]
            self.gameplay["state"] = "waiting_client_authority_rejection"
            return False

        if state == "waiting_client_authority_rejection":
            denied = self._read_sync("client-denied.json")
            if denied is None:
                return False
            rejection = denied.get("command") or {}
            if rejection.get("status") != "RejectedNotAuthority" or rejection.get("applied"):
                raise RuntimeError("client did not prove local authority rejection")
            client_baseline = float(denied["baseline_health"])
            if not self._nearly_equal(report["health"], client_baseline):
                raise RuntimeError("server and client health baselines did not converge")

            damage_delta = -self.gameplay_damage
            damage = self._apply_health_delta("uep05.server.damage", damage_delta, True)
            self._assert_command(damage, "Applied", True)
            duplicate = self._apply_health_delta("uep05.server.damage", damage_delta, True)
            self._assert_command(duplicate, "RejectedDuplicateCommand", False)
            expected = damage["health_before"] + damage_delta
            if not self._nearly_equal(damage["health_after"], expected):
                raise RuntimeError("server damage did not produce the requested health delta")

            self.gameplay["baseline_health"] = damage["health_before"]
            self.gameplay["expected_damaged_health"] = expected
            self.gameplay["damage_command"] = damage
            self.gameplay["duplicate_command"] = duplicate
            self.gameplay["client_authority_rejection"] = rejection
            self.gameplay["state"] = "waiting_client_damage_observation"
            self._record_gameplay_event("server_damage_applied", damage["health_after"])
            self._write_sync(
                "server-damaged.json",
                {
                    "mode": self.mode,
                    "baseline_health": damage["health_before"],
                    "expected_damaged_health": expected,
                    "damage_command": damage,
                    "duplicate_command": duplicate,
                },
            )
            return False

        if state == "waiting_client_damage_observation":
            observed = self._read_sync("client-damage-observed.json")
            if observed is None:
                return False
            if not self._nearly_equal(
                observed["observed_health"], self.gameplay["expected_damaged_health"]
            ):
                raise RuntimeError("client damage observation did not match server health")
            if not self._nearly_equal(report["health"], self.gameplay["expected_damaged_health"]):
                raise RuntimeError("server health changed before the restore command")

            heal = self._apply_health_delta("uep05.server.heal", self.gameplay_damage, True)
            self._assert_command(heal, "Applied", True)
            if not self._nearly_equal(heal["health_after"], self.gameplay["baseline_health"]):
                raise RuntimeError("server heal did not restore the baseline health")
            self.gameplay["observed_damaged_health"] = float(observed["observed_health"])
            self.gameplay["heal_command"] = heal
            self.gameplay["state"] = "waiting_client_restore_observation"
            self._record_gameplay_event("server_heal_applied", heal["health_after"])
            self._write_sync(
                "server-restored.json",
                {
                    "mode": self.mode,
                    "restored_health": heal["health_after"],
                    "heal_command": heal,
                },
            )
            return False

        if state == "waiting_client_restore_observation":
            observed = self._read_sync("client-restore-observed.json")
            if observed is None:
                return False
            if not self._nearly_equal(
                observed["observed_health"], self.gameplay["baseline_health"]
            ):
                raise RuntimeError("client restore observation did not match baseline health")
            self._complete_gameplay_slice(report["health"])
            return True

        return state == "completed"

    def _advance_gameplay_slice(self, report):
        if not self.gameplay_slice_enabled:
            return True
        if (
            not math.isfinite(self.gameplay_damage)
            or self.gameplay_damage <= 0.0
            or self.gameplay_damage > 25.0
        ):
            raise RuntimeError("gameplay damage must be finite and in the range (0, 25]")
        if self.mode in ("standalone", "packaged"):
            return self._advance_local_gameplay_slice(report)
        if self.mode == "client":
            return self._advance_client_gameplay_slice(report)
        if self.mode == "server":
            return self._advance_server_gameplay_slice(report)
        raise RuntimeError("gameplay slice is not supported for mode {0}".format(self.mode))

    def _pending_requirements(self, report):
        pending = []
        if not report["game_thread"]:
            pending.append("game thread")
        if not report["game_world"]:
            pending.append("game world")
        if self.require_experience and not report["experience_loaded"]:
            pending.append("Experience load")
        if self.expected_experience:
            experience = report["experience"] or ""
            if self.expected_experience.lower() not in experience.lower():
                pending.append("Experience containing {0}".format(self.expected_experience))
        if self.gameplay_slice_enabled:
            if not report["health_ready"]:
                pending.append("Lyra Health Component")
            elif report["health"] <= 0.0 or report["max_health"] <= 0.0:
                pending.append("positive Lyra health")
            if report["damage_immune"]:
                pending.append("Lyra gameplay damage enabled")

        if self.hud_slice_enabled:
            hud = self._hud_snapshot()
            if hud["errors"]:
                pending.append("error-free Python HUD presenter")
            if not hud["registered"]:
                pending.append("registered Python HUD Mixin Set")
            if not hud["source_asset_available"]:
                pending.append("staged W_Healthbar Mixin asset")
            if self.mode in ("server", "server_exit"):
                if (
                    hud["active_widget_count"] != 0
                    or hud["construct_count"] != 0
                    or hud["controller_bind_count"] != 0
                    or hud["health_bind_count"] != 0
                ):
                    pending.append("zero dedicated-server HUD instances")
            else:
                if hud["active_widget_count"] < 1:
                    pending.append("active Python W_Healthbar instance")
                if hud["controller_bind_count"] < 1:
                    pending.append("Python HUD controller binding")
                if hud["health_bind_count"] < 1:
                    pending.append("Python HUD health binding")
                if hud["visual_update_count"] < 1:
                    pending.append("Python HUD initial health render")

        feature_states = {
            item["name"].lower(): item for item in report["game_features"] if item["name"]
        }
        for feature in self.required_features:
            state = feature_states.get(feature.lower())
            if state is None or not state["active"]:
                pending.append("active Game Feature {0}".format(feature))
        registered_states = {"registered", "loaded", "active"}
        for feature in self.required_registered_features:
            state = feature_states.get(feature.lower())
            if state is None or state["state"].lower() not in registered_states:
                pending.append("registered Game Feature {0}".format(feature))

        if self.mode == "source":
            if report["net_mode"] != "Standalone":
                pending.append("Standalone net mode")
            return pending

        if self.mode == "server_exit":
            if report["net_mode"] not in ("DedicatedServer", "ListenServer"):
                pending.append("server net mode")
            if not report["server_authority"]:
                pending.append("server authority")
            return pending

        if self.mode in ("standalone", "packaged", "client"):
            expected_net_mode = "Client" if self.mode == "client" else "Standalone"
            if report["net_mode"] != expected_net_mode:
                pending.append("{0} net mode".format(expected_net_mode))
            if report["local_player_controller_count"] < self.expected_player_controllers:
                pending.append("{0} local player controller(s)".format(self.expected_player_controllers))
            if not report["player_pawn"]:
                pending.append("local player pawn")
            if not report["pawn_locally_controlled"]:
                pending.append("locally controlled pawn")
            if not report["player_state_ready"]:
                pending.append("replicated PlayerState")
            if not report["hero_input_ready"]:
                pending.append("Lyra Enhanced Input bindings")
            if not report["ability_system_ready"]:
                pending.append("Lyra Ability System")
            if self.mode == "client" and report["pawn_local_role"] != "AutonomousProxy":
                pending.append("AutonomousProxy pawn role")
            if self.mode in ("standalone", "packaged") and report["pawn_local_role"] != "Authority":
                pending.append("Authority pawn role")
        elif self.mode == "server":
            if report["net_mode"] not in ("DedicatedServer", "ListenServer"):
                pending.append("server net mode")
            if not report["server_authority"]:
                pending.append("server authority")
            if report["remote_player_controller_count"] < self.expected_player_controllers:
                pending.append("{0} remote player controller(s)".format(self.expected_player_controllers))
            if not report["player_pawn"]:
                pending.append("server-side player pawn")
            if not report["player_state_ready"]:
                pending.append("server-side PlayerState")
            if not report["ability_system_ready"]:
                pending.append("server-side Ability System")
            if report["player_pawn"] and report["pawn_local_role"] != "Authority":
                pending.append("server Authority pawn role")
        else:
            pending.append("known validation mode")
        return pending

    def _assert_ready(self, report):
        if sys.version_info[:2] != (3, 11):
            raise RuntimeError("expected CPython 3.11, got {0}".format(sys.version))
        pending = self._pending_requirements(report)
        if pending:
            raise RuntimeError("Lyra readiness timed out waiting for: {0}".format(", ".join(pending)))

    def _write_result(self, status, snapshot_report=None, error=None):
        if not self.result_path or self.finished:
            return
        self.finished = True
        report = {
            "schema_version": 5,
            "status": status,
            "mode": self.mode,
            "python_version": ".".join(str(value) for value in sys.version_info[:3]),
            "elapsed_seconds": round(self.elapsed, 3),
            "wall_elapsed_seconds": round(self._wall_elapsed(), 3),
            "world_ticks": self.world_ticks,
            "experience_events": self.experience_events,
            "required_features": self.required_features,
            "required_registered_features": self.required_registered_features,
            "expected_experience_contains": self.expected_experience,
            "expected_player_controllers": self.expected_player_controllers,
            "hold_ready_seconds": self.hold_ready_seconds,
            "ready_release_gate": bool(self.ready_release_path),
            "gameplay_slice": self.gameplay,
            "hud": self._hud_snapshot(),
            "hud_lifecycle": self.hud_lifecycle,
            "shutdown": None,
            "snapshot": snapshot_report,
            "pending_requirements": (
                self._pending_requirements(snapshot_report) if snapshot_report is not None else []
            ),
            "error": error,
        }
        path = Path(self.result_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if status == "passed" and self.hud_slice_enabled:
            from uep_lyra_hud.shutdown_validation import defer_until_shutdown

            defer_until_shutdown(report, path)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if report["status"] == "awaiting_shutdown":
            ue.log("UEP_LYRA_AWAITING_SHUTDOWN")
            return
        if status == "passed" and self.gameplay_slice_enabled:
            ue.log("UEP_LYRA_GAMEPLAY_SLICE_PASSED")
        if status == "passed" and self.hud_slice_enabled:
            ue.log("UEP_LYRA_PYTHON_HUD_PASSED")
        (ue.log if status == "passed" else ue.log_error)(
            "UEP_LYRA_SMOKE_PASSED" if status == "passed" else "UEP_LYRA_SMOKE_FAILED"
        )

    def _request_quit(self):
        try:
            ue.request_exit()
            return
        except Exception:
            ue.log_error(traceback.format_exc())

        candidates = [self.world] if _is_valid(self.world) else []
        candidates.extend(ue.all_worlds())
        for world in candidates:
            try:
                world.quit_game()
                return
            except Exception:
                try:
                    world.world_exec("QUIT")
                    return
                except Exception:
                    continue

    def tick(self, delta_seconds):
        try:
            self.elapsed += delta_seconds
            world = self._game_world()
            if not _is_valid(world) or not self._attach(world):
                if self.result_path and self._timed_out():
                    raise RuntimeError("Lyra game world/bridge was not ready before timeout")
                return True

            self.world_ticks += 1
            snapshot = self.bridge.call_function("CaptureSnapshot")
            snapshot_report = self._snapshot_report(snapshot)
            self.last_snapshot_report = snapshot_report
            minimum_ticks = 12 if self.mode == "source" else 30
            if self.world_ticks < minimum_ticks:
                return True

            # Network peers share a release gate. Once this process has proven
            # every requirement, retain that exact snapshot so a faster peer
            # cannot invalidate the already-observed result by disconnecting
            # before this process sees the release file on its next tick.
            if self.ready_snapshot_report is not None:
                if not Path(self.ready_release_path).is_file():
                    return True
                self._assert_ready(self.ready_snapshot_report)
                self._assert_hud_contract(self.ready_snapshot_report)
                self._write_result("passed", snapshot_report=self.ready_snapshot_report)
                self.shutdown_binding()
                self._request_quit()
                return False

            # Respawn, Game Feature transitions and travel intentionally make
            # ordinary readiness requirements temporarily false. Once the
            # gameplay sequence has completed and lifecycle work has started,
            # let its state machine restore those requirements before applying
            # the final readiness gate again.
            if (
                self.gameplay["completed"]
                and self.hud_slice_enabled
                and not self.hud_lifecycle["completed"]
                and self.hud_lifecycle["state"] != "waiting_readiness"
            ):
                if not self._advance_hud_lifecycle_probe(snapshot_report):
                    if self._timed_out():
                        raise RuntimeError(
                            "Lyra HUD lifecycle probe timed out in state: {0}".format(
                                self.hud_lifecycle["state"]
                            )
                        )
                    return True

            pending = self._pending_requirements(snapshot_report)
            if pending:
                self.ready_since = None
                self.ready_announced = False
                wall_elapsed = self._wall_elapsed()
                if pending != self.last_pending or wall_elapsed - self.last_pending_log_at >= 30.0:
                    ue.log(
                        "UEP_LYRA_PENDING {0}: {1}".format(self.mode, ", ".join(pending))
                    )
                    self.last_pending = list(pending)
                    self.last_pending_log_at = wall_elapsed
                if self._timed_out():
                    self._assert_ready(snapshot_report)
                return True

            if self.ready_since is None:
                self.ready_since = self.elapsed
            if self.elapsed - self.ready_since < self.hold_ready_seconds:
                return True

            if not self._advance_gameplay_slice(snapshot_report):
                if self._timed_out():
                    raise RuntimeError(
                        "Lyra gameplay slice timed out in state: {0}".format(
                            self.gameplay["state"]
                        )
                    )
                return True

            if not self._advance_hud_lifecycle_probe(snapshot_report):
                if self._timed_out():
                    raise RuntimeError(
                        "Lyra HUD lifecycle probe timed out in state: {0}".format(
                            self.hud_lifecycle["state"]
                        )
                    )
                return True

            if self.ready_release_path:
                self._assert_ready(snapshot_report)
                self._assert_hud_contract(snapshot_report)
                self.ready_snapshot_report = snapshot_report
                if not self.ready_announced:
                    ue.log("UEP_LYRA_REQUIREMENTS_READY {0}".format(self.mode))
                    self.ready_announced = True
                if not Path(self.ready_release_path).is_file():
                    return True

            self._assert_ready(snapshot_report)
            self._assert_hud_contract(snapshot_report)
            self._write_result("passed", snapshot_report=snapshot_report)
            self.shutdown_binding()
            self._request_quit()
            return False
        except Exception:
            details = traceback.format_exc()
            ue.log_error(details)
            self._write_result(
                "failed", snapshot_report=self.last_snapshot_report, error=details
            )
            self.shutdown_binding()
            self._request_quit()
            return False


try:
    _previous = globals().get("runtime")
    if _previous is not None:
        _previous.shutdown_binding()
except Exception:
    ue.log_error(traceback.format_exc())

if not _has_argument("-UEPLyraMultiClient"):
    runtime = LyraRuntimeProbe()
    ticker = ue.add_ticker(runtime.tick)
